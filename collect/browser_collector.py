#!/usr/bin/env python3
"""
Browser Automation Collector for tiny-distill
Uses browser-use to automatically collect from ChatGPT, Claude, Gemini web interfaces.

No API keys needed for the chat interfaces — just a browser!
(You need ONE API key to power the browser agent itself)

Install:
  pip install browser-use
  playwright install chromium

Usage:
  # Collect from ChatGPT (needs OpenAI key for agent, NOT for ChatGPT access)
  python collect/browser_collector.py --provider chatgpt --num-prompts 50

  # Collect from Claude
  python collect/browser_collector.py --provider claude --num-prompts 50

  # Use a free LLM for the agent (no paid API needed!)
  python collect/browser_collector.py --provider chatgpt --agent-llm ollama
"""

import json
import os
import sys
import uuid
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

# ─── Provider Configurations ────────────────────────────────────────────────

PROVIDERS = {
    "chatgpt": {
        "name": "ChatGPT",
        "url": "https://chatgpt.com",
        "input_selector": 'textarea[data-id="root"], #prompt-textarea, div[contenteditable="true"]',
        "send_button": 'button[data-testid="send-button"], button[aria-label="Send prompt"]',
        "response_wait": 15,  # seconds to wait for response
        "response_selector": 'div[data-message-author-role="assistant"]',
        "login_required": True,
        "login_url": "https://chatgpt.com/auth/login",
        "instructions": """
ChatGPT Browser Automation:
  1. Make sure you're logged into ChatGPT in your default browser
  2. The agent will open ChatGPT and automate the collection
  3. You may need to handle CAPTCHA if it appears
  
  NOTE: You need to be logged in! The agent navigates as YOU.
"""
    },
    "claude": {
        "name": "Claude",
        "url": "https://claude.ai",
        "input_selector": 'div[contenteditable="true"], textarea, p[data-placeholder]',
        "send_button": 'button[aria-label="Send Message"], button[type="submit"]',
        "response_wait": 20,
        "response_selector": 'div[data-testid="message"], div.font-claude-message',
        "login_required": True,
        "login_url": "https://claude.ai/login",
        "instructions": """
Claude Browser Automation:
  1. Make sure you're logged into claude.ai
  2. The agent will automate collection
"""
    },
    "gemini": {
        "name": "Gemini",
        "url": "https://gemini.google.com",
        "input_selector": 'textarea, div[contenteditable="true"], rich-textarea',
        "send_button": 'button[aria-label="Send"], button.send-button',
        "response_wait": 15,
        "response_selector": 'message-content, model-response',
        "login_required": True,
        "login_url": "https://gemini.google.com",
        "instructions": """
Gemini Browser Automation:
  1. Make sure you're logged into gemini.google.com
  2. The agent will automate collection
"""
    }
}

# ─── Agent LLM Options ──────────────────────────────────────────────────────

def get_agent_llm(llm_choice: str):
    """
    Get the LLM that powers the browser agent.
    
    Options:
      - "openai"    → uses OpenAI API (needs OPENAI_API_KEY)
      - "anthropic" → uses Anthropic API (needs ANTHROPIC_API_KEY)  
      - "ollama"    → uses local Ollama (FREE! needs ollama running, uses phi3:3.8b)
      - "google"    → uses Google Gemini API (needs GOOGLE_API_KEY)
    """
    if llm_choice == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini")
    
    elif llm_choice == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-20250514")
    
    elif llm_choice == "ollama":
        from langchain_ollama import ChatOllama
        # phi3:3.8b — tiny but smart enough for browser automation
        # Falls back to qwen2.5:3b or llama3.2:3b if not available
        return ChatOllama(model="phi3:3.8b", base_url="http://localhost:11434")
    
    elif llm_choice == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    
    else:
        print(f"❌ Unknown LLM: {llm_choice}")
        print(f"   Options: openai, anthropic, ollama, google")
        sys.exit(1)


# ─── Browser Collection Task ────────────────────────────────────────────────

COLLECT_TASK_TEMPLATE = """
You are a data collection agent. Your job is to collect AI responses for training data.

TASK:
1. Navigate to {url}
2. Wait for the page to fully load
3. Find the input field and type this prompt:
   "{prompt}"
4. Press Enter or click the send button
5. Wait for the AI to finish generating its response (wait for the stop/streaming button to disappear or for a new message to appear)
6. Copy the FULL response text from the AI's message
7. Return ONLY the response text, nothing else

IMPORTANT:
- Do NOT add any commentary or explanation
- Return the EXACT response from the AI
- If there's an error or you can't complete it, return "ERROR: [reason]"
- Wait long enough for the response to fully generate
"""


async def collect_single_prompt(agent, provider_config, prompt, provider_name):
    """Use browser-use agent to collect a single response."""
    
    task = COLLECT_TASK_TEMPLATE.format(
        url=provider_config["url"],
        prompt=prompt.replace('"', '\\"'),
    )
    
    try:
        result = await agent.run(task)
        return result
    except Exception as e:
        return f"ERROR: {e}"


async def collect_batch_browser(
    prompts,
    provider="chatgpt",
    agent_llm="openai",
    headless=True,
    max_retries=2
):
    """
    Collect responses from a chat interface using browser automation.
    
    Args:
        prompts: List of prompt dicts or strings
        provider: "chatgpt", "claude", or "gemini"
        agent_llm: LLM to power the agent ("openai", "anthropic", "ollama", "google")
        headless: Run browser headlessly (no GUI)
        max_retries: Max retries per prompt on failure
    """
    try:
        from browser_use import Agent, Browser
    except ImportError:
        print("❌ browser-use not installed!")
        print("   pip install browser-use")
        print("   playwright install chromium")
        sys.exit(1)
    
    config = PROVIDERS[provider]
    llm = get_agent_llm(agent_llm)
    results = []
    
    print(f"\n🌐 Browser Collection from {config['name']}")
    print(f"   Agent LLM: {agent_llm}")
    print(f"   Headless: {headless}")
    print(f"   Prompts: {len(prompts)}")
    
    # Create browser instance
    browser = Browser(headless=headless)
    
    for i, p in enumerate(prompts):
        prompt_text = p["prompt"] if isinstance(p, dict) else p
        domain = p.get("domain", "general") if isinstance(p, dict) else "general"
        
        print(f"\n  [{i+1}/{len(prompts)}] Collecting...", flush=True)
        print(f"    Prompt: {prompt_text[:80]}...")
        
        for attempt in range(max_retries + 1):
            try:
                agent = Agent(
                    task=COLLECT_TASK_TEMPLATE.format(
                        url=config["url"],
                        prompt=prompt_text.replace('"', '\\"').replace('\n', ' '),
                    ),
                    llm=llm,
                    browser=browser,
                )
                
                result = await agent.run()
                response = str(result).strip()
                
                if response.startswith("ERROR:"):
                    print(f"    ❌ {response}")
                    if attempt < max_retries:
                        print(f"    🔄 Retry {attempt + 1}/{max_retries}...")
                        continue
                    break
                
                results.append({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                    "teacher": f"browser/{provider}",
                    "domain": domain,
                    "prompt": prompt_text,
                    "response": response,
                    "method": "browser_automation"
                })
                print(f"    ✅ Collected ({len(response)} chars)")
                break
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                if attempt < max_retries:
                    print(f"    🔄 Retry {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(3)
                else:
                    print(f"    ⚠️  Skipping after {max_retries} retries")
    
    await browser.close()
    return results


# ─── Multi-Provider Collection ──────────────────────────────────────────────

async def collect_multi_provider(prompts, providers, agent_llm, headless):
    """Collect from multiple providers for multi-teacher distillation."""
    all_results = []
    
    for provider in providers:
        print(f"\n{'='*60}")
        print(f"🌐 Starting collection from {PROVIDERS[provider]['name']}")
        print(f"{'='*60}")
        
        results = await collect_batch_browser(
            prompts, provider=provider, agent_llm=agent_llm, headless=headless
        )
        all_results.extend(results)
        print(f"  ✅ Got {len(results)} responses from {provider}")
    
    return all_results


# ─── Save & CLI ──────────────────────────────────────────────────────────────

def save_dataset(entries, output_path):
    """Save collected entries as JSONL."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'a') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Saved {len(entries)} entries to {output_path}")


async def main_async(args):
    # Load prompts
    if args.prompts_file:
        with open(args.prompts_file) as f:
            prompts = json.load(f)
        print(f"📋 Loaded {len(prompts)} prompts from {args.prompts_file}")
    else:
        sys.path.insert(0, str(Path(__file__).parent))
        from prompt_generator import generate_prompts
        prompts = generate_prompts(args.num_prompts)
        print(f"📋 Generated {len(prompts)} prompts")
    
    # Collect
    if args.multi_provider:
        providers = args.providers.split(",") if args.providers else ["chatgpt", "claude"]
        results = await collect_multi_provider(
            prompts, providers, args.agent_llm, not args.no_headless
        )
    else:
        results = await collect_batch_browser(
            prompts, provider=args.provider, agent_llm=args.agent_llm,
            headless=not args.no_headless
        )
    
    # Save
    if results:
        output = args.output or f"data/browser_{args.provider}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        save_dataset(results, output)
        print(f"\n🎉 Done! {len(results)} prompt-response pairs collected.")
    else:
        print("\n❌ No data collected.")


def main():
    parser = argparse.ArgumentParser(
        description="Collect training data via browser automation (no API keys for chat!)"
    )
    parser.add_argument("--provider", choices=["chatgpt", "claude", "gemini"],
                       default="chatgpt", help="Chat interface to collect from")
    parser.add_argument("--multi-provider", action="store_true",
                       help="Collect from multiple providers")
    parser.add_argument("--providers", default=None,
                       help="Comma-separated providers for multi-provider mode")
    parser.add_argument("--agent-llm", choices=["openai", "anthropic", "ollama", "google"],
                       default="openai", help="LLM to power the browser agent")
    parser.add_argument("--num-prompts", type=int, default=50,
                       help="Number of prompts to collect")
    parser.add_argument("--prompts-file", default=None,
                       help="Custom prompts JSON file")
    parser.add_argument("--output", default=None,
                       help="Output JSONL file")
    parser.add_argument("--no-headless", action="store_true",
                       help="Show browser window (useful for debugging/CAPTCHA)")
    parser.add_argument("--max-retries", type=int, default=2)
    args = parser.parse_args()
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
