#!/usr/bin/env python3
"""
OpenRouter Collector for tiny-distill
Uses OpenRouter API to collect responses from 100+ models.

OpenRouter gives you access to:
  - Claude (Opus, Sonnet, Haiku)
  - GPT (o1, o3, 4o, 4o-mini)
  - Gemini (2.5 Pro, Flash)
  - Grok, Llama, Mistral, and 100+ more!

Setup:
  1. Get an API key from https://openrouter.ai/keys
  2. Set OPENROUTER_API_KEY env var or pass via --api-key
  3. Choose your model(s)

Usage:
  # Collect from a single model
  python collect/openrouter_collector.py --model claude-sonnet-4-6 --num-prompts 100
  
  # Multi-teacher: collect from multiple models
  python collect/openrouter_collector.py --multi-model \
    --models claude-sonnet-4-6,gpt-4o,gemini-2.0-flash \
    --num-prompts 100

  # Or use environment variable
  export OPENROUTER_API_KEY="your-key-here"
  python collect/openrouter_collector.py --model claude-sonnet-4-6 --num-prompts 50
"""

import json
import os
import sys
import uuid
import time
import random
import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# ─── Logging Setup ──────────────────────────────────────────────────────────

LOG_FILE = Path("data/openrouter_collection.log")

def setup_logging():
    """Set up logging to both console and file."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # File handler — detailed logs
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-7s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    # Console handler — clean output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('  %(message)s'))
    
    logger = logging.getLogger('openrouter')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

log = logging.getLogger('openrouter')


def ask_for_api_key(prompt: str) -> Optional[str]:
    """Ask user for API key input."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return None

# ─── Popular Models on OpenRouter ────────────────────────────────────────────

# Tier 1: Top performers
TIER_1 = {
    "anthropic/claude-opus-4-6": "Best overall - #1 ranked",
    "anthropic/claude-sonnet-4-6": "Best value - fast + smart",
    "openai/gpt-5.4": "OpenAI's latest flagship",
    "google/gemini-2.5-pro": "Google's best model",
    "x-ai/grok-4": "xAI's top reasoning model",
}

# Tier 2: Strong performers  
TIER_2 = {
    "anthropic/claude-haiku-3": "Fast & cheap",
    "openai/gpt-4o": "Solid all-rounder",
    "openai/gpt-4o-mini": "Fast & cheap",
    "google/gemini-2.0-flash": "Very fast",
    "meta-llama/llama-3.3-70b-instruct": "Open source beast",
    "mistralai/mistral-large": "Strong reasoning",
}

# Tier 3: Good for specific use cases
TIER_3 = {
    "deepseek/deepseek-chat": "Great value",
    "qwen/qwen-2.5-72b-instruct": "Strong open source",
    "anthropic/claude-3-5-sonnet": "Reliable classic",
    "openai/o1": "Reasoning model",
    "openai/o3-mini": "Fast reasoning",
}

RECOMMENDED = {**TIER_1, **TIER_2, **TIER_3}

# ─── API Endpoints ──────────────────────────────────────────────────────────

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_REFERRER = "https://github.com/r2d2helper1-creator/tiny-distill"

# ─── Rate Limit Detection ───────────────────────────────────────────────────

RATE_LIMIT_CODES = [429, 503, 504]


def is_rate_limit_error(response: requests.Response) -> bool:
    """Check if response indicates rate limiting."""
    if response.status_code in RATE_LIMIT_CODES:
        return True
    try:
        data = response.json()
        error = data.get("error", {}).get("message", "").lower()
        return any(x in error for x in ["rate limit", "too many requests", "quota"])
    except:
        return False


# ─── OpenRouter Collector ───────────────────────────────────────────────────

class OpenRouterCollector:
    """
    Collects training data via OpenRouter API.
    """
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-sonnet-4-6",
                 max_retries: int = 3, cooldown: int = 60):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.cooldown = cooldown
        self.results = []
        
        # Progress tracking
        self.progress_file = Path("data/openrouter_progress.jsonl")
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
    
    def _save_entry(self, entry: dict):
        """Save immediately (crash-safe)."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        log.debug(f"Saved entry: id={entry['id'][:8]} prompt={entry['prompt'][:40]}...")
    
    def _call_api(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Make a single API call to OpenRouter."""
        
        log.debug(f"API call start | model={self.model} | prompt_len={len(prompt)}")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": OPENROUTER_REFERRER,
            "X-Title": "tiny-distill",
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        
        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=120
            )
        except requests.exceptions.Timeout:
            log.error("API call timed out after 120s")
            return "ERROR: Request timed out after 120s"
        except requests.exceptions.ConnectionError as e:
            log.error(f"API connection error: {e}")
            return f"ERROR: Connection failed - {e}"
        except Exception as e:
            log.error(f"API call exception: {e}")
            return f"ERROR: {e}"
        
        log.debug(f"API response | status={response.status_code} | latency={response.elapsed.total_seconds():.1f}s")
        
        if response.status_code != 200:
            if is_rate_limit_error(response):
                log.warning(f"Rate limited! Status={response.status_code} | Headers: {dict(response.headers)}")
                return "RATE_LIMIT"
            try:
                error = response.json().get("error", {}).get("message", response.text)
                log.error(f"API error | status={response.status_code} | error={error}")
                return f"ERROR: {error}"
            except:
                log.error(f"API error | status={response.status_code} | body={response.text[:200]}")
                return f"ERROR: HTTP {response.status_code}"
        
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Log token usage if available
            usage = data.get("usage", {})
            log.info(f"API success | {len(content)} chars | "
                    f"prompt_tokens={usage.get('prompt_tokens', '?')} | "
                    f"completion_tokens={usage.get('completion_tokens', '?')} | "
                    f"total_tokens={usage.get('total_tokens', '?')}")
            
            return content
        except Exception as e:
            log.error(f"Failed to parse API response: {e} | response={str(data)[:200] if 'data' in dir() else 'N/A'}")
            return f"ERROR: {e}"
    
    def collect(self, prompts: list, system_prompt: Optional[str] = None) -> list:
        """
        Collect responses from OpenRouter for all prompts.
        """
        # Filter already completed
        remaining = [
            p for p in prompts
            if p.get("prompt", str(p)) not in self.completed
        ]
        
        log.info(f"=== COLLECTION START ===")
        log.info(f"Model: {self.model}")
        log.info(f"Total prompts: {len(prompts)}")
        log.info(f"Already done: {len(prompts) - len(remaining)}")
        log.info(f"Remaining: {len(remaining)}")
        
        print(f"\n📡 OpenRouter Collection")
        print(f"   Model: {self.model}")
        print(f"   Total: {len(prompts)}")
        print(f"   Already done: {len(prompts) - len(remaining)}")
        print(f"   Remaining: {len(remaining)}")
        
        success_count = 0
        fail_count = 0
        consecutive_rate_limits = 0  # Track consecutive rate limit failures
        start_time = time.time()
        
        for i, p in enumerate(remaining):
            prompt_text = p.get("prompt", str(p)) if isinstance(p, dict) else p
            domain = p.get("domain", "general") if isinstance(p, dict) else "general"
            
            log.info(f"[{i+1}/{len(remaining)}] Starting prompt | domain={domain} | prompt={prompt_text[:80]}...")
            print(f"\n  [{i+1}/{len(remaining)}] {prompt_text[:60]}...")
            
            # Retry loop
            for attempt in range(self.max_retries + 1):
                response = self._call_api(prompt_text, system_prompt)
                
                if response == "RATE_LIMIT":
                    wait_time = self.cooldown * (attempt + 1)
                    log.warning(f"Rate limited on attempt {attempt+1}/{self.max_retries+1} | waiting {wait_time}s")
                    print(f"    🚫 Rate limited! Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                if response.startswith("ERROR:"):
                    if attempt < self.max_retries:
                        wait = 2 ** attempt  # Exponential backoff
                        log.warning(f"Error on attempt {attempt+1}/{self.max_retries+1}: {response[:100]} | retrying in {wait}s")
                        print(f"    ❌ {response[:50]}... Retrying in {wait}s")
                        time.sleep(wait)
                        continue
                    else:
                        log.error(f"FAILED prompt after {self.max_retries+1} attempts | prompt={prompt_text[:80]} | last_error={response[:100]}")
                        print(f"    ❌ Failed after {self.max_retries} retries")
                        fail_count += 1
                        consecutive_rate_limits = 0  # Reset on non-rate-limit error
                        break
                
                # Success!
                entry = {
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                    "teacher": f"openrouter/{self.model}",
                    "domain": domain,
                    "prompt": prompt_text,
                    "response": response,
                    "method": "openrouter_api",
                }
                
                self.results.append(entry)
                self.completed.add(prompt_text)
                self._save_entry(entry)
                success_count += 1
                consecutive_rate_limits = 0  # Reset consecutive rate limit counter on success
                
                elapsed = time.time() - start_time
                rate = success_count / elapsed * 60  # per minute
                remaining_est = (len(remaining) - i - 1) / (success_count / elapsed) / 60  # minutes
                
                log.info(f"SUCCESS | chars={len(response)} | total_success={success_count} | "
                        f"failures={fail_count} | rate={rate:.1f}/min | est_remaining={remaining_est:.0f}min")
                print(f"    ✅ ({len(response)} chars)")
                print(f"    📊 Running: {success_count} ✅ / {fail_count} ❌ | {rate:.1f}/min | ~{remaining_est:.0f}min remaining")
                break
            
            else:
                # This executes if we exited the retry loop normally (all retries exhausted)
                # Check if we exited due to rate limit
                if consecutive_rate_limits >= 10:
                    log.error(f"Hit {consecutive_rate_limits} consecutive rate limit failures!")
                    print(f"\n🚨 ALERT: {consecutive_rate_limits} consecutive rate limit failures detected!")
                    print(f"This suggests your API key may be exhausted or blocked.")
                    
                    # Ask for new API key
                    print(f"\n💡 Please:")
                    print(f"   1. Check your OpenRouter usage at https://openrouter.ai/authorize")
                    print(f"   2. Generate a new API key if needed")
                    print(f"   3. Enter it below to continue")
                    
                    new_key = ask_for_api_key("Enter new OpenRouter API key (or press Enter to quit): ")
                    if not new_key:
                        log.info("User chose to quit after rate limit alert")
                        print(f"\n👋 Stopping collection. Progress saved.")
                        break  # Exit the collection loop
                    
                    # Update API key and reset counter
                    log.info("API key updated by user")
                    self.api_key = new_key
                    consecutive_rate_limits = 0
                    print(f"🔑 API key updated! Resuming collection...")
                    # Retry the current prompt with new key
                    continue
                else:
                    # Not enough consecutive rate limits to trigger alert, just count this failure
                    consecutive_rate_limits += 1
                    log.warning(f"Rate limit failure #{consecutive_rate_limits} for prompt")
                    print(f"    ⚠️  Rate limit failure #{consecutive_rate_limits} - continuing...")
                    fail_count += 1
            
            # Small delay between requests to be nice to the API
            time.sleep(random.uniform(1, 3))
        
        elapsed_total = time.time() - start_time
        log.info(f"=== COLLECTION DONE === | success={success_count} | failed={fail_count} | "
                f"consecutive_rate_limit_alerts={consecutive_rate_limits if consecutive_rate_limits >= 10 else 0} | "
                f"elapsed={elapsed_total/60:.1f}min | entries_in_file={len(self.completed)}")
        
        print(f"\n✅ Collection complete: {success_count} success / {fail_count} failed in {elapsed_total/60:.1f}min")
        print(f"📄 Detailed log: {LOG_FILE}")
        return self.results
    
    def collect_multi_model(self, prompts: list, models: list,
                           system_prompt: Optional[str] = None) -> list:
        """Collect from multiple models for multi-teacher distillation."""
        all_results = []
        
        for model in models:
            print(f"\n{'='*60}")
            print(f"📡 Collecting from: {model}")
            print(f"{'='*60}")
            
            original_model = self.model
            self.model = model
            
            results = self.collect(prompts, system_prompt)
            all_results.extend(results)
            
            print(f"  ✅ Got {len(results)} responses from {model}")
            
            self.model = original_model
        
        return all_results


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    # Set up logging FIRST
    setup_logging()
    log.info("="*60)
    log.info("tiny-distill OpenRouter Collector starting")
    log.info("="*60)
    
    parser = argparse.ArgumentParser(
        description="Collect training data via OpenRouter API"
    )
    parser.add_argument("--api-key", "-k", default=None,
                       help="OpenRouter API key (or set OPENROUTER_API_KEY env)")
    parser.add_argument("--model", "-m", default="anthropic/claude-sonnet-4-6",
                       help="Model to use (default: anthropic/claude-sonnet-4-6)")
    parser.add_argument("--models", default=None,
                       help="Comma-separated models for multi-teacher mode")
    parser.add_argument("--multi-model", action="store_true",
                       help="Collect from multiple models")
    parser.add_argument("--num-prompts", "-n", type=int, default=100,
                       help="Number of prompts to generate")
    parser.add_argument("--prompts-file", "-p", default=None,
                       help="Custom prompts JSON file")
    parser.add_argument("--output", "-o", default=None,
                       help="Output file")
    parser.add_argument("--system-prompt", "-s", default=None,
                       help="Optional system prompt")
    parser.add_argument("--cooldown", type=int, default=60,
                       help="Cooldown seconds after rate limit")
    args = parser.parse_args()
    
    log.info(f"Args: model={args.model} | num_prompts={args.num_prompts} | multi_model={args.multi_model} | "
            f"prompts_file={args.prompts_file} | output={args.output}")
    
    # Get API key
    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        log.error("No API key provided!")
        print("❌ No API key provided!")
        print("   Set OPENROUTER_API_KEY env var or pass --api-key")
        print("   Get your key at: https://openrouter.ai/keys")
        sys.exit(1)
    
    log.info("API key loaded (masked)")
    
    # Load prompts
    if args.prompts_file:
        log.info(f"Loading prompts from {args.prompts_file}")
        with open(args.prompts_file) as f:
            prompts = json.load(f)
        log.info(f"Loaded {len(prompts)} prompts from file")
        print(f"📋 Loaded {len(prompts)} prompts from {args.prompts_file}")
    else:
        log.info(f"Generating {args.num_prompts} prompts")
        sys.path.insert(0, str(Path(__file__).parent))
        from prompt_generator import generate_prompts
        prompts = generate_prompts(args.num_prompts)
        log.info(f"Generated {len(prompts)} prompts")
        print(f"📋 Generated {len(prompts)} prompts")
    
    # Create collector
    collector = OpenRouterCollector(
        api_key=api_key,
        model=args.model,
        cooldown=args.cooldown,
    )
    
    # Collect
    if args.multi_model or args.models:
        models = args.models.split(",") if args.models else [
            "anthropic/claude-sonnet-4-6",
            "openai/gpt-4o",
            "google/gemini-2.0-flash",
        ]
        log.info(f"Multi-model mode: {models}")
        results = collector.collect_multi_model(prompts, models, args.system_prompt)
    else:
        results = collector.collect(prompts, args.system_prompt)
    
    # Save final dataset
    if results:
        output = args.output or f"data/openrouter_{args.model.replace('/', '-')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            for entry in results:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        log.info(f"Saved {len(results)} entries to {output}")
        log.info(f"Full log available at {LOG_FILE}")
        print(f"\n✅ Dataset: {len(results)} entries → {output}")
        print(f"📄 Full log: {LOG_FILE}")
    else:
        log.warning("No data collected!")
        print("\n❌ No data collected")
    
    log.info("="*60)
    log.info("Collector finished")
    log.info("="*60)


if __name__ == "__main__":
    main()
