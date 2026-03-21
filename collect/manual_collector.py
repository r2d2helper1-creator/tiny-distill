#!/usr/bin/env python3
"""
Manual Chat Collector for tiny-distill
Collect training data by copy-pasting from ChatGPT, Claude, Gemini, etc.
No API key needed — just a web browser!
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Color helpers for terminal output
class C:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print(f"""
{C.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🧪  TINY-DISTILL  —  Manual Chat Collector                 ║
║                                                              ║
║   Collect training data by chatting with AI models           ║
║   No API key needed. Just copy & paste.                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{C.END}
""")

def load_prompts(domain=None):
    """Load prompt templates, optionally filtered by domain."""
    prompts_file = Path(__file__).parent.parent / "data" / "example_prompts.json"
    
    if not prompts_file.exists():
        print(f"{C.YELLOW}⚠️  No prompts file found. Using built-in defaults.{C.END}")
        return get_default_prompts()
    
    with open(prompts_file) as f:
        data = json.load(f)
    
    if domain:
        data = [p for p in data if p.get("domain") == domain]
    
    return data

def get_default_prompts():
    """Built-in prompts if no file exists."""
    return [
        {"prompt": "Explain quantum computing to a 10-year-old.", "domain": "science"},
        {"prompt": "Write a Python function to find the longest palindrome in a string.", "domain": "coding"},
        {"prompt": "What are the key differences between TCP and UDP?", "domain": "tech"},
        {"prompt": "Write a haiku about artificial intelligence.", "domain": "creative"},
        {"prompt": "Explain the concept of compound interest with a real example.", "domain": "finance"},
        {"prompt": "What would you do if you had to plan a surprise birthday party?", "domain": "reasoning"},
        {"prompt": "Translate 'The early bird catches the worm' into 5 languages.", "domain": "language"},
        {"prompt": "Debug this code: for i in range(10): print(i += 1)", "domain": "coding"},
        {"prompt": "What are the pros and cons of remote work?", "domain": "general"},
        {"prompt": "Explain how a neural network learns, step by step.", "domain": "science"},
        {"prompt": "Write a short story about a robot learning to cook.", "domain": "creative"},
        {"prompt": "How would you solve the trolley problem?", "domain": "reasoning"},
        {"prompt": "What's the difference between machine learning and deep learning?", "domain": "tech"},
        {"prompt": "Write a SQL query to find duplicate emails in a users table.", "domain": "coding"},
        {"prompt": "Explain the water cycle in simple terms.", "domain": "science"},
    ]

def collect_single(prompt_info, session_id, teacher="unknown"):
    """Collect a single prompt-response pair interactively."""
    prompt = prompt_info["prompt"]
    domain = prompt_info.get("domain", "general")
    
    print(f"\n{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.END}")
    print(f"{C.CYAN}📋 PROMPT (copy this into your AI chat):{C.END}")
    print(f"{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.END}")
    print(f"\n{prompt}\n")
    print(f"{C.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.END}")
    
    print(f"\n{C.YELLOW}👆 Copy the prompt above and paste it into ChatGPT, Claude, etc.{C.END}")
    print(f"{C.YELLOW}   Then copy the AI's response and paste it here.{C.END}")
    print(f"\n{C.GREEN}[Enter] Paste response{C.END}  |  {C.RED}[s] Skip{C.END}  |  {C.RED}[q] Quit{C.END}")
    
    choice = input(f"\n{C.BOLD}> {C.END}").strip().lower()
    
    if choice == 'q':
        return None  # Signal to quit
    if choice == 's':
        return False  # Signal to skip
    
    # Collect multi-line response
    print(f"\n{C.CYAN}📝 Paste the AI response below (press Enter twice when done):{C.END}")
    lines = []
    empty_count = 0
    while True:
        line = input()
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
            lines.append(line)
        else:
            empty_count = 0
            lines.append(line)
    
    response = "\n".join(lines).strip()
    
    if not response:
        print(f"{C.YELLOW}⚠️  Empty response, skipping.{C.END}")
        return False
    
    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "teacher": teacher,
        "domain": domain,
        "prompt": prompt,
        "response": response,
        "method": "manual_chat"
    }

def save_dataset(entries, output_path):
    """Save collected entries as JSONL."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Append mode — don't overwrite existing data
    with open(output_path, 'a') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n{C.GREEN}✅ Saved {len(entries)} entries to {output_path}{C.END}")

def main():
    clear_screen()
    print_banner()
    
    session_id = str(uuid.uuid4())[:8]
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Ask which teacher
    print(f"{C.BOLD}Which AI are you collecting from?{C.END}")
    print(f"  1. ChatGPT")
    print(f"  2. Claude")
    print(f"  3. Gemini")
    print(f"  4. Other")
    
    teacher_map = {"1": "chatgpt", "2": "claude", "3": "gemini"}
    teacher_choice = input(f"\n{C.BOLD}> {C.END}").strip()
    teacher = teacher_map.get(teacher_choice, "unknown")
    
    # Ask which domain
    print(f"\n{C.BOLD}Which domain?{C.END}")
    print(f"  1. All domains (mixed)")
    print(f"  2. Coding")
    print(f"  3. Science")
    print(f"  4. Creative writing")
    print(f"  5. Reasoning")
    print(f"  6. General knowledge")
    
    domain_map = {"1": None, "2": "coding", "3": "science", "4": "creative", "5": "reasoning", "6": "general"}
    domain_choice = input(f"\n{C.BOLD}> {C.END}").strip()
    domain = domain_map.get(domain_choice)
    
    # Load prompts
    prompts = load_prompts(domain)
    print(f"\n{C.GREEN}📋 Loaded {len(prompts)} prompts{C.END}")
    
    # Output file
    output_file = data_dir / f"manual_{teacher}_{session_id}.jsonl"
    
    # Collect
    collected = []
    print(f"\n{C.BOLD}🚀 Let's collect some data! Press Enter to start...{C.END}")
    input()
    
    for i, prompt_info in enumerate(prompts):
        print(f"\n{C.CYAN}[{i+1}/{len(prompts)}]{C.END}")
        
        result = collect_single(prompt_info, session_id, teacher)
        
        if result is None:  # Quit
            break
        elif result is not False:  # Got data
            collected.append(result)
            print(f"{C.GREEN}✅ Collected! ({len(collected)} total){C.END}")
    
    # Save
    if collected:
        save_dataset(collected, output_file)
        print(f"""
{C.GREEN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🎉  Collection Complete!                                   ║
║                                                              ║
║   Collected: {len(collected):>4} prompt-response pairs                ║
║   Teacher:   {teacher:<20}                          ║
║   Saved to:  {str(output_file.name):<20}                          ║
║                                                              ║
║   Next steps:                                                ║
║   1. Collect from more teachers (ChatGPT, Claude, Gemini)    ║
║   2. Run: python collect/cleaner.py                          ║
║   3. Train: open notebooks/train_colab.ipynb                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{C.END}
""")
    else:
        print(f"\n{C.YELLOW}No data collected. Run again when you're ready!{C.END}")

if __name__ == "__main__":
    main()
