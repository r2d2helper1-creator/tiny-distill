#!/usr/bin/env python3
"""
Data Cleaner & Knowledge Purifier for tiny-distill
Cleans, deduplicates, and purifies multi-teacher data.
"""

import json
import hashlib
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

def load_jsonl(file_path):
    """Load a JSONL file into a list of dicts."""
    entries = []
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries

def clean_text(text):
    """Basic text cleaning."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    # Remove common AI prefixes
    for prefix in ["Sure! Here's", "Of course! Here", "Certainly!", "Here's my"]:
        if text.startswith(prefix):
            pass  # Keep for now, just noting
    return text.strip()

def deduplicate(entries, similarity_threshold=0.85):
    """Remove duplicate and near-duplicate entries."""
    seen_hashes = set()
    seen_prompts = []
    unique = []
    
    for entry in entries:
        # Exact duplicate check (by content hash)
        content_hash = hashlib.md5(
            (entry["prompt"] + entry["response"]).encode()
        ).hexdigest()
        
        if content_hash in seen_hashes:
            continue
        
        # Near-duplicate check (by prompt similarity)
        is_near_dup = False
        for seen_prompt in seen_prompts:
            if SequenceMatcher(None, entry["prompt"], seen_prompt).ratio() > similarity_threshold:
                is_near_dup = True
                break
        
        if not is_near_dup:
            seen_hashes.add(content_hash)
            seen_prompts.append(entry["prompt"])
            unique.append(entry)
    
    return unique

def purify_multi_teacher(entries):
    """
    Knowledge purification: for prompts asked to multiple teachers,
    pick the best response or create an ensemble.
    
    Strategy: keep the longest, most detailed response per unique prompt.
    (Simple but effective baseline — can be upgraded with quality scoring later)
    """
    # Group by normalized prompt
    prompt_groups = defaultdict(list)
    for entry in entries:
        # Normalize prompt for grouping
        normalized = entry["prompt"].lower().strip()
        prompt_groups[normalized].append(entry)
    
    purified = []
    multi_teacher_count = 0
    
    for prompt, group in prompt_groups.items():
        if len(group) == 1:
            # Single teacher — keep as-is
            purified.append(group[0])
        else:
            # Multiple teachers — pick best
            multi_teacher_count += 1
            
            # Score each response
            scored = []
            for entry in group:
                score = 0
                resp = entry["response"]
                
                # Longer responses tend to be more detailed
                score += min(len(resp) / 1000, 5)  # Cap at 5 points for length
                
                # Responses with code blocks
                score += resp.count("```") * 0.5
                
                # Responses with structured formatting
                score += resp.count("\n- ") * 0.1
                score += resp.count("\n1.") * 0.1
                
                # Responses with examples
                score += resp.lower().count("example") * 0.2
                score += resp.lower().count("for instance") * 0.2
                
                # Penalize very short responses
                if len(resp) < 50:
                    score -= 2
                
                scored.append((score, entry))
            
            # Take the best
            scored.sort(key=lambda x: x[0], reverse=True)
            best = scored[0][1]
            best["multi_teacher"] = True
            best["teacher_count"] = len(group)
            purified.append(best)
    
    print(f"  📊 {multi_teacher_count} prompts had multiple teachers (purified)")
    return purified

def clean_dataset(input_files, output_file, do_purify=True):
    """Full cleaning pipeline."""
    print(f"\n🧹 Cleaning dataset...")
    
    # Load all files
    all_entries = []
    for f in input_files:
        entries = load_jsonl(f)
        print(f"  📂 Loaded {len(entries)} entries from {f}")
        all_entries.extend(entries)
    
    print(f"  📊 Total raw entries: {len(all_entries)}")
    
    # Clean text
    for entry in all_entries:
        entry["prompt"] = clean_text(entry["prompt"])
        entry["response"] = clean_text(entry["response"])
    
    # Filter out too-short entries
    before = len(all_entries)
    all_entries = [e for e in all_entries if len(e["response"]) > 30]
    print(f"  🗑️  Removed {before - len(all_entries)} too-short entries")
    
    # Deduplicate
    before = len(all_entries)
    all_entries = deduplicate(all_entries)
    print(f"  🗑️  Removed {before - len(all_entries)} duplicates")
    
    # Multi-teacher purification
    if do_purify:
        all_entries = purify_multi_teacher(all_entries)
    
    # Save
    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w') as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Cleaned dataset: {len(all_entries)} entries → {output}")
    
    # Stats
    domains = defaultdict(int)
    teachers = defaultdict(int)
    for e in all_entries:
        domains[e.get("domain", "unknown")] += 1
        teachers[e.get("teacher", "unknown")] += 1
    
    print(f"\n📊 Domain distribution:")
    for d, count in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"    {d}: {count}")
    
    print(f"\n📊 Teacher distribution:")
    for t, count in sorted(teachers.items(), key=lambda x: -x[1]):
        print(f"    {t}: {count}")
    
    return all_entries

if __name__ == "__main__":
    import argparse
    import glob
    
    parser = argparse.ArgumentParser(description="Clean and purify collected data")
    parser.add_argument("--input", nargs="+", help="Input JSONL files (or glob patterns)")
    parser.add_argument("--input-dir", default="data/", help="Directory to glob for .jsonl files")
    parser.add_argument("--output", default="data/cleaned_dataset.jsonl")
    parser.add_argument("--no-purify", action="store_true", help="Skip multi-teacher purification")
    args = parser.parse_args()
    
    if args.input:
        files = []
        for pattern in args.input:
            files.extend(glob.glob(pattern))
    else:
        files = list(Path(args.input_dir).glob("*.jsonl"))
        # Exclude already-cleaned files and progress files (used for resume)
        files = [f for f in files if "cleaned" not in f.name.lower() and "progress" not in f.name.lower()]
    
    if not files:
        print("❌ No input files found")
        sys.exit(1)
    
    clean_dataset(files, args.output, do_purify=not args.no_purify)
