#!/usr/bin/env python3
"""
Resilient Browser Collector for tiny-distill
Handles rate limits, session rotation, and multi-provider fallback.

The key insight: rate limits are usually cookie/session-based.
New browser context = new cookies = fresh limits = continue collecting!

Features:
- Auto-detect rate limits (error messages, CAPTCHAs, cooldowns)
- Auto-rotate browser sessions (new context = new identity)
- Multi-provider fallback (arena.ai → chatgpt → claude → ollama)
- Proxy rotation support (for IP-based limits)
- Progress persistence (resume where you left off)
- Cooldown detection (wait and retry if time-based limits)
"""

import json
import os
import sys
import uuid
import time
import asyncio
import random
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ─── Rate Limit Detection ───────────────────────────────────────────────────

RATE_LIMIT_SIGNALS = [
    # Common rate limit messages
    "rate limit",
    "too many requests",
    "try again later",
    "quota exceeded",
    "limit reached",
    "please wait",
    "slow down",
    "429",
    "throttl",
    "cooldown",
    "you've reached",
    "usage limit",
    "message limit",
    "hourly limit",
    "daily limit",
    "temporarily unavailable",
    "service unavailable",
    "try again in",
    # CAPTCHA signals
    "captcha",
    "verify you are human",
    "are you a robot",
    "challenge",
    "unusual traffic",
]

def is_rate_limited(response_text: str) -> bool:
    """Check if a response indicates a rate limit."""
    if not response_text:
        return True
    text_lower = response_text.lower()
    return any(signal in text_lower for signal in RATE_LIMIT_SIGNALS)


# ─── Provider Registry ──────────────────────────────────────────────────────

@dataclass
class ProviderConfig:
    name: str
    url: str
    input_selector: str
    send_method: str = "enter"  # "enter" or "button"
    send_button_selector: str = ""
    response_selector: str = ""
    response_wait: int = 20
    max_requests_per_session: int = 10  # Conservative default
    cooldown_seconds: int = 60  # Wait after rate limit
    priority: int = 1  # Lower = try first

PROVIDERS = {
    "arena": ProviderConfig(
        name="Arena.ai",
        url="https://arena.ai",
        input_selector='textarea, div[contenteditable="true"], input[type="text"]',
        response_selector='.prose, .message-content, [class*="response"], [class*="answer"]',
        response_wait=25,
        max_requests_per_session=5,  # Arena is aggressive with limits
        cooldown_seconds=120,
        priority=1,
    ),
    "chatgpt": ProviderConfig(
        name="ChatGPT",
        url="https://chatgpt.com",
        input_selector='textarea[data-id="root"], #prompt-textarea, div[contenteditable="true"]',
        send_button_selector='button[data-testid="send-button"]',
        response_selector='div[data-message-author-role="assistant"]',
        response_wait=20,
        max_requests_per_session=20,
        cooldown_seconds=30,
        priority=2,
    ),
    "claude": ProviderConfig(
        name="Claude",
        url="https://claude.ai",
        input_selector='div[contenteditable="true"], textarea',
        response_selector='div[data-testid="message"]',
        response_wait=25,
        max_requests_per_session=15,
        cooldown_seconds=60,
        priority=2,
    ),
    "gemini": ProviderConfig(
        name="Gemini",
        url="https://gemini.google.com",
        input_selector='textarea, div[contenteditable="true"]',
        response_selector='message-content, model-response',
        response_wait=20,
        max_requests_per_session=15,
        cooldown_seconds=30,
        priority=2,
    ),
    "ollama": ProviderConfig(
        name="Ollama (Local)",
        url="",  # Not browser-based, handled separately
        input_selector="",
        max_requests_per_session=999999,  # No limits!
        priority=0,  # Always try first if available
    ),
}


# ─── Session Manager ─────────────────────────────────────────────────────────

@dataclass
class SessionState:
    """Track per-provider session state."""
    provider: str
    requests_made: int = 0
    rate_limited: bool = False
    last_request_time: float = 0
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    @property
    def is_exhausted(self) -> bool:
        config = PROVIDERS[self.provider]
        return self.requests_made >= config.max_requests_per_session or self.rate_limited
    
    def reset(self):
        """Reset session (new browser context = new identity)."""
        self.requests_made = 0
        self.rate_limited = False
        self.session_id = str(uuid.uuid4())[:8]


class ResilientCollector:
    """
    Collects responses with automatic rate-limit handling and session rotation.
    """
    
    def __init__(
        self,
        providers: list[str],
        agent_llm: str = "ollama",
        proxies: list[str] = None,
        max_retries: int = 3,
        progress_file: str = "data/progress.jsonl",
    ):
        self.providers = sorted(providers, key=lambda p: PROVIDERS[p].priority)
        self.agent_llm = agent_llm
        self.proxies = proxies or []
        self.max_retries = max_retries
        self.progress_file = Path(progress_file)
        self.sessions: dict[str, SessionState] = {
            p: SessionState(provider=p) for p in providers
        }
        self.results: list[dict] = []
        self.current_proxy_idx = 0
        
        # Load progress (resume support)
        self.completed_prompts: set[str] = set()
        self._load_progress()
    
    def _load_progress(self):
        """Load previously completed prompts to resume collection."""
        if self.progress_file.exists():
            with open(self.progress_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        self.completed_prompts.add(entry.get("prompt", ""))
                        self.results.append(entry)
                    except:
                        pass
            if self.completed_prompts:
                print(f"📂 Resuming: {len(self.completed_prompts)} prompts already collected")
    
    def _save_progress(self, entry: dict):
        """Save a single result immediately (crash-safe)."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy from rotation."""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_proxy_idx % len(self.proxies)]
        self.current_proxy_idx += 1
        return proxy
    
    async def _create_browser_context(self, proxy: str = None):
        """Create a fresh browser context (new cookies, new identity)."""
        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
            
            launch_options = {
                'headless': True,
                'args': browser_args,
            }
            
            if proxy:
                launch_options['proxy'] = {'server': proxy}
            
            self._browser = await self._playwright.chromium.launch(**launch_options)
            
            # New context = new cookies = new session
            context = await self._browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent=f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(120,131)}.0.0.0 Safari/537.36',
            )
            
            page = await context.new_page()
            return page, context
            
        except Exception as e:
            print(f"  ❌ Browser creation failed: {e}")
            return None, None
    
    async def _close_browser(self):
        """Close browser and clean up."""
        try:
            if hasattr(self, '_browser') and self._browser:
                await self._browser.close()
            if hasattr(self, '_playwright') and self._playwright:
                await self._playwright.stop()
        except:
            pass
    
    async def _collect_single_browser(
        self, page, config: ProviderConfig, prompt: str
    ) -> str:
        """Collect a single response via browser."""
        try:
            # Navigate
            await page.goto(config.url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Find and fill input
            input_el = await page.wait_for_selector(config.input_selector, timeout=10000)
            await input_el.click()
            await asyncio.sleep(0.5)
            await input_el.fill(prompt)
            await asyncio.sleep(1)
            
            # Send
            if config.send_button_selector:
                btn = await page.query_selector(config.send_button_selector)
                if btn:
                    await btn.click()
                else:
                    await page.keyboard.press('Enter')
            else:
                await page.keyboard.press('Enter')
            
            # Wait for response
            await asyncio.sleep(config.response_wait)
            
            # Try to get response
            if config.response_selector:
                elements = await page.query_selector_all(config.response_selector)
                if elements:
                    # Get the last response
                    text = await elements[-1].inner_text()
                    return text.strip()
            
            # Fallback: get all visible text
            body_text = await page.inner_text('body')
            return body_text[-2000:].strip()  # Last 2000 chars
            
        except Exception as e:
            return f"ERROR: {e}"
    
    async def _collect_single_ollama(self, prompt: str) -> str:
        """Collect via Ollama (local, no limits)."""
        try:
            import requests
            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "phi3:3.8b",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_predict": 1024}
                },
                timeout=120
            )
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
            return f"ERROR: HTTP {response.status_code}"
        except Exception as e:
            return f"ERROR: {e}"
    
    async def collect_with_rotation(self, prompts: list[dict]):
        """
        Main collection loop with automatic session rotation.
        
        Flow:
        1. Try current provider
        2. If rate limited → rotate session (new browser context)
        3. If provider exhausted → switch to next provider
        4. If all providers exhausted → wait and retry
        5. Save progress after each successful collection
        """
        # Filter already-completed prompts
        remaining = [
            p for p in prompts 
            if p.get("prompt", str(p)) not in self.completed_prompts
        ]
        
        print(f"\n🔄 Resilient Collection")
        print(f"   Total prompts: {len(prompts)}")
        print(f"   Already done: {len(prompts) - len(remaining)}")
        print(f"   Remaining: {len(remaining)}")
        print(f"   Providers: {', '.join(self.providers)}")
        
        prompt_idx = 0
        provider_idx = 0
        
        while prompt_idx < len(remaining):
            prompt_info = remaining[prompt_idx]
            prompt_text = prompt_info.get("prompt", str(prompt_info))
            domain = prompt_info.get("domain", "general")
            
            # Find an available provider
            provider = self.providers[provider_idx % len(self.providers)]
            session = self.sessions[provider]
            config = PROVIDERS[provider]
            
            # Check if session is exhausted
            if session.is_exhausted:
                print(f"\n🔄 Session exhausted for {config.name} — rotating...")
                session.reset()
                
                # If rate limited, cooldown first
                if session.rate_limited:
                    print(f"   ⏳ Cooling down {config.cooldown_seconds}s...")
                    await asyncio.sleep(config.cooldown_seconds)
                
                # Try next provider
                provider_idx += 1
                if provider_idx >= len(self.providers) * 2:
                    # All providers tried twice — wait longer
                    print(f"\n⏳ All providers hit limits. Waiting 5 minutes...")
                    await asyncio.sleep(300)
                    provider_idx = 0
                    for s in self.sessions.values():
                        s.reset()
                continue
            
            print(f"\n  [{prompt_idx+1}/{len(remaining)}] {config.name} | {prompt_text[:60]}...")
            
            # Collect
            response = None
            
            if provider == "ollama":
                response = await self._collect_single_ollama(prompt_text)
            else:
                # Browser-based collection with fresh context
                proxy = self._get_next_proxy()
                page, context = await self._create_browser_context(proxy)
                
                if page:
                    try:
                        response = await self._collect_single_browser(page, config, prompt_text)
                    finally:
                        if context:
                            await context.close()
                        await self._close_browser()
                else:
                    response = "ERROR: browser failed"
            
            # Check response
            if is_rate_limited(response):
                print(f"    🚫 Rate limited! Rotating session...")
                session.rate_limited = True
                provider_idx += 1
                continue
            
            if response.startswith("ERROR:"):
                print(f"    ❌ {response}")
                session.requests_made += 1
                prompt_idx += 1  # Skip this prompt, try next
                continue
            
            # Success!
            entry = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "teacher": f"{provider}",
                "domain": domain,
                "prompt": prompt_text,
                "response": response,
                "session_id": session.session_id,
                "method": "resilient_browser"
            }
            
            self.results.append(entry)
            self.completed_prompts.add(prompt_text)
            session.requests_made += 1
            
            # Save immediately (crash-safe)
            self._save_progress(entry)
            
            print(f"    ✅ Collected ({len(response)} chars)")
            
            prompt_idx += 1
            
            # Small delay between requests
            await asyncio.sleep(random.uniform(2, 5))
        
        return self.results


# ─── CLI ─────────────────────────────────────────────────────────────────────

async def main_async(args):
    # Load prompts
    if args.prompts_file:
        with open(args.prompts_file) as f:
            prompts = json.load(f)
    else:
        sys.path.insert(0, str(Path(__file__).parent))
        from prompt_generator import generate_prompts
        prompts = generate_prompts(args.num_prompts)
    
    # Load proxies if provided
    proxies = []
    if args.proxies_file:
        with open(args.proxies_file) as f:
            proxies = [line.strip() for line in f if line.strip()]
    
    # Collect
    collector = ResilientCollector(
        providers=args.providers.split(","),
        agent_llm=args.agent_llm,
        proxies=proxies,
        progress_file=args.output or "data/progress.jsonl",
    )
    
    results = await collector.collect_with_rotation(prompts)
    
    # Save final dataset
    output = args.output or f"data/resilient_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for entry in results:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Final dataset: {len(results)} entries → {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Resilient collector with rate-limit rotation"
    )
    parser.add_argument("--providers", default="arena,chatgpt,claude,ollama",
                       help="Comma-separated providers (fallback order)")
    parser.add_argument("--agent-llm", default="ollama")
    parser.add_argument("--num-prompts", type=int, default=100)
    parser.add_argument("--prompts-file", default=None)
    parser.add_argument("--proxies-file", default=None,
                       help="File with proxy URLs (one per line)")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
