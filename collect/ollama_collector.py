#!/usr/bin/env python3
"""
Ollama Collector for tiny-distill
Collect training data from Ollama (local or cloud) — FREE teachers!
"""

import json
import os
import sys
import uuid
import time
import argparse
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ pip install requests")
    sys.exit(1)


# ─── Ollama Cloud (free tier) ───────────────────────────────────────────────
# Ollama Cloud gives you free access to many models until tokens run out.
# Sign up at https://ollama.com → get your cloud API endpoint.

OLLAMA_CLOUD_BASE = "https://ollama.com/api"


def collect_ollama_cloud(prompts, api_key=None, model="llama3.1:70b", max_tokens=1024):
    """
    Collect responses from Ollama Cloud (free tier).
    
    Models available on Ollama Cloud (check https://ollama.com/library):
      - llama3.1:70b       (Meta's flagship)
      - llama3.1:8b        (fast, lightweight)
      - gemma2:27b         (Google's open model)
      - qwen2.5:72b        (strong multilingual)
      - mistral-nemo:12b   (good all-rounder)
      - phi3:14b           (Microsoft's efficient model)
      - codellama:34b      (code specialist)
      - deepseek-coder-v2  (strong coding)
      - many more...
    
    Args:
        prompts: List of prompt dicts or strings
        api_key: Ollama Cloud API key (get from ollama.com/settings)
        model: Model name in ollama format
        max_tokens: Max response tokens
    """
    results = []
    
    # Ollama Cloud API key
    if not api_key:
        api_key = os.environ.get("OLLAMA_API_KEY")
    
    if not api_key:
        print("""
⚠️  No Ollama Cloud API key found!

To get one:
  1. Go to https://ollama.com
  2. Sign up / Sign in
  3. Go to Settings → API Keys
  4. Create a key
  5. Set: export OLLAMA_API_KEY="your-key"

Or use Ollama LOCAL instead (free, no key needed):
  python collect/ollama_collector.py --mode local --model llama3.1
""")
        return []
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    for i, p in enumerate(prompts):
        prompt_text = p["prompt"] if isinstance(p, dict) else p
        domain = p.get("domain", "general") if isinstance(p, dict) else "general"
        
        print(f"  [{i+1}/{len(prompts)}] {model} (cloud)...", end=" ", flush=True)
        
        try:
            response = requests.post(
                f"{OLLAMA_CLOUD_BASE}/chat",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                results.append({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                    "teacher": f"ollama-cloud/{model}",
                    "domain": domain,
                    "prompt": prompt_text,
                    "response": content,
                    "tokens_prompt": data.get("prompt_eval_count", 0),
                    "tokens_completion": data.get("eval_count", 0),
                    "method": "ollama_cloud"
                })
                print("✅")
            else:
                print(f"❌ HTTP {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"❌ {e}")
        
        # Respect rate limits
        time.sleep(1)
    
    return results


# ─── Ollama Local (100% free, runs on your machine) ─────────────────────────

def collect_ollama_local(prompts, model="llama3.1:8b", max_tokens=1024, 
                         base_url="http://localhost:11434"):
    """
    Collect responses from local Ollama instance.
    
    Prerequisites:
      1. Install Ollama: https://ollama.com/download
      2. Pull a model: ollama pull llama3.1:8b
      3. It runs automatically — no API key needed!
    
    Great models for local distillation (8GB+ RAM):
      - llama3.1:8b        — best balance of quality/speed
      - gemma2:9b          — Google's efficient model
      - qwen2.5:7b         — strong multilingual
      - phi3:3.8b          — runs on 4GB RAM!
      - mistral:7b         — solid all-rounder
      - codellama:7b       — good for code data
    """
    results = []
    
    # Check if Ollama is running
    try:
        health = requests.get(f"{base_url}/api/tags", timeout=5)
        if health.status_code != 200:
            print(f"❌ Ollama not running at {base_url}")
            print(f"   Start it with: ollama serve")
            return []
        
        models = [m["name"] for m in health.json().get("models", [])]
        if model not in models:
            print(f"⚠️  Model '{model}' not found locally.")
            print(f"   Available: {', '.join(models) if models else 'none'}")
            print(f"   Pull it: ollama pull {model}")
            return []
            
    except requests.ConnectionError:
        print(f"❌ Cannot connect to Ollama at {base_url}")
        print(f"   Install: https://ollama.com/download")
        print(f"   Start:   ollama serve")
        return []
    
    for i, p in enumerate(prompts):
        prompt_text = p["prompt"] if isinstance(p, dict) else p
        domain = p.get("domain", "general") if isinstance(p, dict) else "general"
        
        print(f"  [{i+1}/{len(prompts)}] {model} (local)...", end=" ", flush=True)
        
        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                },
                timeout=300  # Local can be slow on CPU
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                results.append({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                    "teacher": f"ollama-local/{model}",
                    "domain": domain,
                    "prompt": prompt_text,
                    "response": content,
                    "tokens_prompt": data.get("prompt_eval_count", 0),
                    "tokens_completion": data.get("eval_count", 0),
                    "duration_ms": data.get("total_duration", 0) // 1_000_000,
                    "method": "ollama_local"
                })
                print("✅")
            else:
                print(f"❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {e}")
    
    return results


# ─── Multi-Model Collection ─────────────────────────────────────────────────

def collect_multi_model(prompts, mode="cloud", models=None, api_key=None):
    """
    Collect from MULTIPLE Ollama models for multi-teacher distillation.
    
    Example usage:
      python collect/ollama_collector.py --mode cloud --multi-model \\
          --models llama3.1:70b,gemma2:27b,qwen2.5:72b
    """
    if models is None:
        if mode == "cloud":
            models = ["llama3.1:70b", "gemma2:27b", "qwen2.5:72b"]
        else:
            models = ["llama3.1:8b", "gemma2:9b", "qwen2.5:7b"]
    
    all_results = []
    
    for model in models:
        print(f"\n🤖 Collecting from {model}...")
        
        if mode == "cloud":
            results = collect_ollama_cloud(prompts, api_key=api_key, model=model)
        else:
            results = collect_ollama_local(prompts, model=model)
        
        all_results.extend(results)
        print(f"  ✅ Got {len(results)} responses from {model}")
    
    return all_results


# ─── CLI ─────────────────────────────────────────────────────────────────────

def save_dataset(entries, output_path):
    """Save collected entries as JSONL."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'a') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Saved {len(entries)} entries to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Collect training data from Ollama (local or cloud)"
    )
    parser.add_argument("--mode", choices=["cloud", "local"], default="cloud",
                       help="Ollama mode: cloud (free, needs API key) or local (100% free)")
    parser.add_argument("--model", default=None,
                       help="Model name (default: llama3.1:70b cloud / llama3.1:8b local)")
    parser.add_argument("--multi-model", action="store_true",
                       help="Collect from multiple models for multi-teacher distillation")
    parser.add_argument("--models", default=None,
                       help="Comma-separated list of models for multi-model mode")
    parser.add_argument("--num-prompts", type=int, default=100,
                       help="Number of prompts to generate")
    parser.add_argument("--prompts-file", default=None,
                       help="Custom prompts JSON file")
    parser.add_argument("--output", default=None,
                       help="Output JSONL file")
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--base-url", default="http://localhost:11434",
                       help="Ollama local server URL")
    args = parser.parse_args()
    
    # Set defaults based on mode
    if args.model is None:
        args.model = "llama3.1:70b" if args.mode == "cloud" else "llama3.1:8b"
    
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
    if args.multi_model:
        models = args.models.split(",") if args.models else None
        results = collect_multi_model(prompts, mode=args.mode, models=models)
    elif args.mode == "cloud":
        results = collect_ollama_cloud(prompts, model=args.model, max_tokens=args.max_tokens)
    else:
        results = collect_ollama_local(prompts, model=args.model, max_tokens=args.max_tokens,
                                       base_url=args.base_url)
    
    # Save
    if results:
        output = args.output or f"data/ollama_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        save_dataset(results, output)
        print(f"\n🎉 Done! {len(results)} prompt-response pairs collected.")
    else:
        print("\n❌ No data collected.")


if __name__ == "__main__":
    main()
