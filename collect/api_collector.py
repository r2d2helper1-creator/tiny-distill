#!/usr/bin/env python3
"""
API-based Data Collector for tiny-distill
Automated collection from OpenAI, Anthropic, etc.
Requires API key — but way faster than manual.
"""

import json
import os
import sys
import uuid
import time
from datetime import datetime
from pathlib import Path

def collect_openai(prompts, api_key, model="gpt-4o-mini", max_tokens=1024):
    """Collect responses from OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        print("❌ pip install openai")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    results = []
    
    for i, p in enumerate(prompts):
        prompt_text = p["prompt"] if isinstance(p, dict) else p
        domain = p.get("domain", "general") if isinstance(p, dict) else "general"
        
        print(f"  [{i+1}/{len(prompts)}] Querying {model}...", end=" ", flush=True)
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            results.append({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "teacher": f"openai/{model}",
                "domain": domain,
                "prompt": prompt_text,
                "response": response.choices[0].message.content,
                "tokens_prompt": response.usage.prompt_tokens,
                "tokens_completion": response.usage.completion_tokens,
                "method": "api"
            })
            print("✅")
            
            # Rate limit respect
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ {e}")
            time.sleep(2)
    
    return results

def collect_anthropic(prompts, api_key, model="claude-sonnet-4-20250514", max_tokens=1024):
    """Collect responses from Anthropic API."""
    try:
        from anthropic import Anthropic
    except ImportError:
        print("❌ pip install anthropic")
        sys.exit(1)
    
    client = Anthropic(api_key=api_key)
    results = []
    
    for i, p in enumerate(prompts):
        prompt_text = p["prompt"] if isinstance(p, dict) else p
        domain = p.get("domain", "general") if isinstance(p, dict) else "general"
        
        print(f"  [{i+1}/{len(prompts)}] Querying {model}...", end=" ", flush=True)
        
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt_text}]
            )
            
            results.append({
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "teacher": f"anthropic/{model}",
                "domain": domain,
                "prompt": prompt_text,
                "response": response.content[0].text,
                "tokens_prompt": response.usage.input_tokens,
                "tokens_completion": response.usage.output_tokens,
                "method": "api"
            })
            print("✅")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ {e}")
            time.sleep(2)
    
    return results

def save_dataset(entries, output_path):
    """Save collected entries as JSONL."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'a') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Saved {len(entries)} entries to {output_path}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect training data via API")
    parser.add_argument("--provider", choices=["openai", "anthropic"], required=True)
    parser.add_argument("--model", help="Model name (default: provider default)")
    parser.add_argument("--num-prompts", type=int, default=100, help="Number of prompts")
    parser.add_argument("--prompts-file", help="Custom prompts JSON file")
    parser.add_argument("--output", help="Output JSONL file")
    parser.add_argument("--max-tokens", type=int, default=1024)
    args = parser.parse_args()
    
    # Get API key
    if args.provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        model = args.model or "gpt-4o-mini"
        collect_fn = collect_openai
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = args.model or "claude-sonnet-4-20250514"
        collect_fn = collect_anthropic
    
    if not api_key:
        print(f"❌ Set {args.provider.upper()}_API_KEY environment variable")
        sys.exit(1)
    
    # Load prompts
    if args.prompts_file:
        with open(args.prompts_file) as f:
            prompts = json.load(f)
    else:
        # Import prompt generator
        sys.path.insert(0, str(Path(__file__).parent))
        from prompt_generator import generate_prompts
        prompts = generate_prompts(args.num_prompts)
    
    # Collect
    print(f"\n🧪 Collecting {len(prompts)} responses from {args.provider}/{model}\n")
    results = collect_fn(prompts, api_key, model, args.max_tokens)
    
    # Save
    output = args.output or f"data/api_{args.provider}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    save_dataset(results, output)
    
    print(f"\n🎉 Done! {len(results)} prompt-response pairs collected.")

if __name__ == "__main__":
    main()
