#!/usr/bin/env python3
"""
Arena.ai Collector for tiny-distill
Optimized for collecting from arena.ai's 398+ free models.

arena.ai gives you FREE access to:
  - Claude Opus 4.6, Sonnet 4.6 (Anthropic)
  - GPT-5.4, GPT-5.2 (OpenAI)
  - Gemini 3.1 Pro, Gemini 3 Pro (Google)
  - Grok 4.1, Grok 4.20 (xAI)
  - And 390+ more models!

This collector automates the browser to collect responses.
Handles rate limits with automatic session rotation.

Usage:
  python collect/arena_collector.py --model claude-opus-4-6 --num-prompts 100
  python collect/arena_collector.py --model gpt-5.2-chat-latest --num-prompts 500
  python collect/arena_collector.py --multi-model --models claude-opus-4-6,gpt-5.2,gemini-3-pro --num-prompts 1000
"""

import json
import os
import sys
import uuid
import time
import random
import re
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field


# ─── Arena.ai Models (top picks for distillation) ───────────────────────────

# Models organized by quality tier
TIER_1 = {
    "claude-opus-4-6": "Anthropic's best — #1 ranked",
    "gpt-5.4-high": "OpenAI's latest — top tier",
    "gemini-3.1-pro": "Google's best — #3 ranked",
    "grok-4.20-beta": "xAI's reasoning model",
}

TIER_2 = {
    "claude-sonnet-4-6": "Fast + smart, great for coding",
    "gpt-5.2-chat-latest": "Solid all-rounder",
    "gemini-3-pro": "Google's strong model",
    "grok-4.1": "xAI's fast model",
}

TIER_3 = {
    "claude-sonnet-4-5": "Previous gen, still great",
    "gpt-5.1-high": "Older GPT-5",
    "gemini-3-flash": "Google's fast model",
    "grok-4-fast": "xAI's speed demon",
}

# All recommended models
RECOMMENDED = {**TIER_1, **TIER_2, **TIER_3}

# ─── Rate Limit Signals ─────────────────────────────────────────────────────

RATE_LIMIT_SIGNALS = [
    "rate limit", "too many requests", "try again later",
    "quota exceeded", "limit reached", "please wait",
    "slow down", "429", "throttl", "cooldown",
    "you've reached", "usage limit", "message limit",
    "hourly limit", "daily limit", "temporarily unavailable",
    "captcha", "verify you are human", "are you a robot",
    "sign in", "log in", "create account",
]

def is_rate_limited(text: str) -> bool:
    if not text:
        return True
    return any(s in text.lower() for s in RATE_LIMIT_SIGNALS)


# ─── Arena.ai Collector ─────────────────────────────────────────────────────

class ArenaCollector:
    """
    Collects from arena.ai with automatic session rotation.
    """
    
    ARENA_URL = "https://arena.ai"
    
    def __init__(self, headless=True, max_per_session=10, cooldown=120):
        self.headless = headless
        self.max_per_session = max_per_session
        self.cooldown = cooldown
        self.results = []
        self.progress_file = Path("data/arena_progress.jsonl")
        self.completed = set()
        self._load_progress()
    
    def _load_progress(self):
        """Load previous progress for resume support."""
        if self.progress_file.exists():
            with open(self.progress_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        self.completed.add(entry.get("prompt", ""))
                        self.results.append(entry)
                    except:
                        pass
            if self.completed:
                print(f"📂 Resuming: {len(self.completed)} already collected")
    
    def _save_entry(self, entry):
        """Save immediately (crash-safe)."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    async def _create_session(self):
        """Create a fresh browser session."""
        from playwright.async_api import async_playwright
        
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        context = await self._browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent=(
                f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                f'AppleWebKit/537.36 (KHTML, like Gecko) '
                f'Chrome/{random.randint(120,131)}.0.0.0 Safari/537.36'
            ),
        )
        
        page = await context.new_page()
        return page, context
    
    async def _close_session(self):
        """Clean up browser."""
        try:
            if hasattr(self, '_browser') and self._browser:
                await self._browser.close()
            if hasattr(self, '_pw') and self._pw:
                await self._pw.stop()
        except:
            pass
    
    async def _collect_single(self, page, prompt: str, model: str) -> str:
        """Collect a single response from arena.ai."""
        
        try:
            # Navigate to arena.ai
            await page.goto(self.ARENA_URL, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Try to select model (if there's a model selector)
            # Arena.ai might use "Direct Chat" or "Battle" mode
            # Look for a way to select specific model
            
            # Try clicking on model selector if it exists
            try:
                # Look for model dropdown/selector
                model_selectors = [
                    'button:has-text("Model")',
                    'select[name="model"]',
                    '[data-testid="model-selector"]',
                    'button:has-text("Choose")',
                    '.model-select',
                ]
                for sel in model_selectors:
                    el = await page.query_selector(sel)
                    if el:
                        await el.click()
                        await asyncio.sleep(1)
                        # Type model name to filter
                        await page.keyboard.type(model[:20])
                        await asyncio.sleep(1)
                        # Click first result
                        results = await page.query_selector_all('[role="option"], .model-option, li')
                        if results:
                            await results[0].click()
                            await asyncio.sleep(1)
                        break
            except:
                pass  # Model selection is optional
            
            # Find and fill the input
            input_selectors = [
                'textarea',
                'div[contenteditable="true"]',
                'input[type="text"]',
                '#chat-input',
                '[data-testid="chat-input"]',
                'form textarea',
            ]
            
            input_el = None
            for sel in input_selectors:
                input_el = await page.query_selector(sel)
                if input_el:
                    break
            
            if not input_el:
                return "ERROR: Could not find input field"
            
            # Type the prompt
            await input_el.click()
            await asyncio.sleep(0.5)
            await input_el.fill(prompt)
            await asyncio.sleep(0.5)
            
            # Send (Enter or click send button)
            send_selectors = [
                'button[type="submit"]',
                'button:has-text("Send")',
                '[data-testid="send-button"]',
                'button:has-text("Submit")',
            ]
            
            sent = False
            for sel in send_selectors:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    sent = True
                    break
            
            if not sent:
                await page.keyboard.press('Enter')
            
            # Wait for response (streaming indicator + completion)
            await asyncio.sleep(3)  # Wait for it to start
            
            # Wait for response to finish (look for stop button to disappear, or new message)
            max_wait = 60
            waited = 0
            last_text = ""
            
            while waited < max_wait:
                await asyncio.sleep(2)
                waited += 2
                
                # Check for response content
                response_selectors = [
                    '.prose',
                    '.message-content',
                    '[class*="response"]',
                    '[class*="answer"]',
                    '[class*="assistant"]',
                    '.markdown-body',
                    'div[class*="message"]',
                ]
                
                for sel in response_selectors:
                    elements = await page.query_selector_all(sel)
                    if elements:
                        text = await elements[-1].inner_text()
                        if text and len(text) > 20:
                            # Check if still streaming (text growing)
                            if text == last_text:
                                # Stable for 2 seconds, probably done
                                await asyncio.sleep(2)
                                final = await elements[-1].inner_text()
                                if final == text:
                                    return text.strip()
                            last_text = text
                
                # Also check if there's a stop/streaming indicator
                stop_btn = await page.query_selector(
                    'button:has-text("Stop"), button:has-text("Cancel"), '
                    '[class*="stop"], [class*="generating"]'
                )
                if not stop_btn:
                    # No stop button = probably done
                    await asyncio.sleep(2)
            
            # Fallback: get all visible text from the page
            body = await page.inner_text('body')
            # Extract just the response (last part after the prompt)
            if prompt in body:
                parts = body.split(prompt)
                if len(parts) > 1:
                    return parts[-1].strip()[-3000:]
            
            return body[-2000:].strip()
            
        except Exception as e:
            return f"ERROR: {e}"
    
    async def collect(self, prompts: list[dict], model: str = "claude-opus-4-6"):
        """
        Main collection loop with session rotation.
        """
        # Filter already completed
        remaining = [
            p for p in prompts
            if p.get("prompt", str(p)) not in self.completed
        ]
        
        print(f"\n🏟️  Arena.ai Collection")
        print(f"   Model: {model}")
        print(f"   Total: {len(prompts)}")
        print(f"   Already done: {len(prompts) - len(remaining)}")
        print(f"   Remaining: {len(remaining)}")
        
        session_count = 0
        idx = 0
        
        while idx < len(remaining):
            # Rotate session every N requests
            if session_count >= self.max_per_session:
                print(f"\n🔄 Session rotation (cooldown {self.cooldown}s)...")
                await self._close_session()
                await asyncio.sleep(self.cooldown)
                session_count = 0
            
            # Create session if needed
            if session_count == 0:
                print(f"\n🌐 Creating new browser session...")
                page, context = await self._create_session()
            
            prompt_info = remaining[idx]
            prompt = prompt_info.get("prompt", str(prompt_info))
            domain = prompt_info.get("domain", "general")
            
            print(f"\n  [{idx+1}/{len(remaining)}] {model} | {prompt[:60]}...")
            
            response = await self._collect_single(page, prompt, model)
            
            # Check for rate limit
            if is_rate_limited(response):
                print(f"    🚫 Rate limited! Rotating...")
                await context.close()
                await self._close_session()
                session_count = self.max_per_session  # Force rotation
                continue
            
            if response.startswith("ERROR:"):
                print(f"    ❌ {response}")
                idx += 1
                session_count += 1
                continue
            
            # Success!
            entry = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "teacher": f"arena/{model}",
                "domain": domain,
                "prompt": prompt,
                "response": response,
                "method": "arena_browser",
            }
            
            self.results.append(entry)
            self.completed.add(prompt)
            self._save_entry(entry)
            session_count += 1
            
            print(f"    ✅ ({len(response)} chars)")
            
            idx += 1
            
            # Random delay between requests
            await asyncio.sleep(random.uniform(3, 8))
        
        # Cleanup
        await self._close_session()
        
        return self.results
    
    async def collect_multi_model(self, prompts, models):
        """Collect from multiple models for multi-teacher distillation."""
        all_results = []
        
        for model in models:
            print(f"\n{'='*60}")
            print(f"🏟️  Collecting from: {model}")
            print(f"{'='*60}")
            
            results = await self.collect(prompts, model=model)
            all_results.extend(results)
            
            print(f"  ✅ Got {len(results)} responses from {model}")
        
        return all_results


# ─── Async Main ──────────────────────────────────────────────────────────────

import asyncio

async def main_async(args):
    # Load prompts
    if args.prompts_file:
        with open(args.prompts_file) as f:
            prompts = json.load(f)
    else:
        sys.path.insert(0, str(Path(__file__).parent))
        from prompt_generator import generate_prompts
        prompts = generate_prompts(args.num_prompts)
    
    print(f"📋 {len(prompts)} prompts loaded")
    
    # Create collector
    collector = ArenaCollector(
        headless=not args.no_headless,
        max_per_session=args.max_per_session,
        cooldown=args.cooldown,
    )
    
    # Collect
    if args.multi_model:
        models = args.models.split(",") if args.models else list(TIER_1.keys())
        results = await collector.collect_multi_model(prompts, models)
    else:
        results = await collector.collect(prompts, model=args.model)
    
    # Save final dataset
    output = args.output or f"data/arena_{args.model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for entry in results:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Dataset: {len(results)} entries → {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Collect from arena.ai (398+ free models!)"
    )
    parser.add_argument("--model", default="claude-opus-4-6",
                       help="Model to collect from")
    parser.add_argument("--multi-model", action="store_true",
                       help="Collect from multiple models")
    parser.add_argument("--models", default=None,
                       help="Comma-separated model names")
    parser.add_argument("--num-prompts", type=int, default=100)
    parser.add_argument("--prompts-file", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--no-headless", action="store_true",
                       help="Show browser window")
    parser.add_argument("--max-per-session", type=int, default=10,
                       help="Max requests before session rotation")
    parser.add_argument("--cooldown", type=int, default=120,
                       help="Seconds to wait between sessions")
    args = parser.parse_args()
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
