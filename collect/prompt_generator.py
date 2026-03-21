#!/usr/bin/env python3
"""
Smart Prompt Generator for tiny-distill
Generates diverse, high-quality prompts across many domains.
"""

import random
import json
from pathlib import Path

DOMAINS = {
    "coding": {
        "weight": 0.25,
        "templates": [
            "Write a {lang} function to {task}.",
            "Debug this {lang} code and explain the fix: {code_snippet}",
            "Explain the time complexity of {algorithm} and when to use it.",
            "Compare {concept1} vs {concept2} in {lang}. When would you use each?",
            "Refactor this code to be more {quality}: {code_snippet}",
            "Write a {lang} class that implements {pattern}.",
            "How would you handle {error_scenario} in {lang}?",
            "Write unit tests for this function: {code_snippet}",
            "Explain what this {lang} code does, line by line: {code_snippet}",
            "Design a {lang} API for {use_case}.",
        ],
        "fills": {
            "lang": ["Python", "JavaScript", "TypeScript", "Rust", "Go", "Java", "C++"],
            "task": ["sorting a list", "reversing a linked list", "finding duplicates", 
                     "parsing JSON", "reading a file", "connecting to a database",
                     "implementing a cache", "rate limiting", "pagination", "retry logic"],
            "algorithm": ["quicksort", "binary search", "BFS", "DFS", "dynamic programming",
                          "merge sort", "Dijkstra's algorithm", "A* search"],
            "concept1": ["lists", "tuples", "generators", "async/await", "classes"],
            "concept2": ["arrays", "sets", "iterators", "callbacks", "interfaces"],
            "quality": ["readable", "efficient", "testable", "modular", "type-safe"],
            "pattern": ["observer pattern", "factory pattern", "strategy pattern", 
                        "singleton", "dependency injection"],
            "error_scenario": ["network failures", "invalid input", "race conditions",
                               "memory limits", "timeout errors"],
            "use_case": ["user authentication", "file upload", "real-time chat",
                         "shopping cart", "task scheduler"],
        }
    },
    "science": {
        "weight": 0.15,
        "templates": [
            "Explain {topic} like I'm {level}.",
            "What's the difference between {thing1} and {thing2}?",
            "How does {process} work at the {scale} level?",
            "Why is {phenomenon} important for {application}?",
            "What would happen if {hypothetical}?",
            "Explain the history of {discovery} and its impact.",
        ],
        "fills": {
            "topic": ["quantum entanglement", "CRISPR", "black holes", "photosynthesis",
                      "neural plasticity", "plate tectonics", "DNA replication",
                      "the immune system", "climate feedback loops", "dark matter"],
            "level": ["5 years old", "a high school student", "a college freshman",
                      "my grandmother", "an alien visitor"],
            "thing1": ["mitosis", "RNA", "fission", "chemical bonds", "genotypes"],
            "thing2": ["meiosis", "DNA", "fusion", "physical bonds", "phenotypes"],
            "process": ["protein folding", "nuclear fusion", "evolution", "memory formation"],
            "scale": ["quantum", "molecular", "cellular", "atomic", "macroscopic"],
            "phenomenon": ["gravity", "electromagnetic radiation", "natural selection"],
            "application": ["medicine", "energy", "space exploration", "agriculture"],
            "hypothetical": ["gravity stopped working for 5 seconds", "the sun disappeared",
                            "humans could photosynthesize", "we could see UV light"],
            "discovery": ["penicillin", "the structure of DNA", "radio waves", "X-rays"],
        }
    },
    "creative": {
        "weight": 0.15,
        "templates": [
            "Write a {genre} story about {premise} in {style}.",
            "Write a {poem_type} about {topic}.",
            "Create a dialogue between {character1} and {character2} about {topic}.",
            "Describe {scene} using all five senses.",
            "Write an opening paragraph for a {genre} novel set in {setting}.",
            "What would {character} say about {modern_topic}?",
        ],
        "fills": {
            "genre": ["sci-fi", "fantasy", "mystery", "horror", "romance", "thriller"],
            "premise": ["a robot learning emotions", "time travel goes wrong",
                       "the last tree on Earth", "a library that contains all possible books",
                       "a world where dreams are currency"],
            "style": ["Hemingway's style", "Shakespearean English", "modern casual",
                     "stream of consciousness", "noir detective style"],
            "poem_type": ["haiku", "sonnet", "free verse", "limerick", "villanelle"],
            "topic": ["artificial intelligence", "the ocean", "childhood memories",
                     "the passage of time", "urban loneliness"],
            "character1": ["Socrates", "a time traveler", "an AI assistant"],
            "character2": ["a teenager", "a medieval knight", "a cat"],
            "scene": ["a rainy city at night", "a bustling marketplace", 
                     "the surface of Mars", "a cozy library"],
            "setting": ["Victorian London", "a space station", "a small fishing village",
                       "a cyberpunk megacity"],
            "character": ["Shakespeare", "Einstein", "a pirate"],
            "modern_topic": ["social media", "climate change", "streaming services"],
        }
    },
    "reasoning": {
        "weight": 0.2,
        "templates": [
            "Think step by step: {problem}",
            "What are the strongest arguments for and against {position}?",
            "You're advising {role}. What factors would you consider for {decision}?",
            "A company is facing {situation}. What should they do?",
            "Compare the tradeoffs of {option1} vs {option2} for {context}.",
            "What assumptions are hidden in this statement: {statement}",
            "If {premise}, what can we conclude about {question}?",
        ],
        "fills": {
            "problem": ["the Monty Hall problem", "the prisoner's dilemma",
                       "how to fairly divide a cake among 3 people",
                       "why planes can fly upside down",
                       "how GPS works with relativity corrections"],
            "position": ["universal basic income", "nuclear energy", "space colonization",
                        "AI regulation", "open source software"],
            "role": ["a mayor", "a CEO", "a school principal", "a hospital director"],
            "decision": ["budget allocation", "hiring strategy", "policy change",
                        "technology adoption", "crisis response"],
            "situation": ["declining sales", "a PR crisis", "rapid growth",
                         "new competition", "regulatory changes"],
            "option1": ["building in-house", "centralization", "speed"],
            "option2": ["using third-party tools", "decentralization", "quality"],
            "context": ["a startup", "a large enterprise", "a non-profit"],
            "statement": ["correlation implies causation", "newer is always better",
                         "more data always helps", "AI will replace all jobs"],
            "premise": ["all swans are white", "demand exceeds supply",
                       "information wants to be free"],
            "question": ["whether a black swan exists", "price changes",
                        "privacy implications"],
        }
    },
    "general": {
        "weight": 0.25,
        "templates": [
            "Explain {topic} to someone who's never heard of it.",
            "What are the pros and cons of {thing}?",
            "How would you {task} in {context}?",
            "What's the best way to {goal}?",
            "Create a {list_type} of {topic}.",
            "I'm trying to {goal}. What am I doing wrong?",
            "Explain why {observation} happens.",
        ],
        "fills": {
            "topic": ["blockchain", "compound interest", "the water cycle",
                     "how search engines work", "supply and demand",
                     "how vaccines work", "the stock market"],
            "thing": ["remote work", "electric cars", "social media", "fast food",
                     "learning a new language", "early retirement"],
            "task": ["learn a new skill quickly", "organize a team effectively",
                    "negotiate a salary", "plan a trip on a budget"],
            "context": ["a small town", "a big city", "a developing country",
                       "a highly regulated industry"],
            "goal": ["learn to code", "save money", "be more productive",
                    "improve communication", "start a business"],
            "list_type": ["top 10 list", "pros and cons list", "step-by-step guide",
                         "comparison table", "checklist"],
            "observation": ["ice floats on water", "we yawn when tired",
                          "prices keep rising", "birds migrate"],
        }
    }
}

def generate_prompt():
    """Generate a single random prompt."""
    # Pick domain based on weights
    domain_names = list(DOMAINS.keys())
    weights = [DOMAINS[d]["weight"] for d in domain_names]
    domain = random.choices(domain_names, weights=weights, k=1)[0]
    
    config = DOMAINS[domain]
    template = random.choice(config["templates"])
    
    # Fill in template variables
    prompt = template
    for key, values in config["fills"].items():
        placeholder = "{" + key + "}"
        if placeholder in prompt:
            prompt = prompt.replace(placeholder, random.choice(values), 1)
    
    return {"prompt": prompt, "domain": domain}

def generate_prompts(n=100):
    """Generate n diverse prompts."""
    return [generate_prompt() for _ in range(n)]

def save_prompts(prompts, output_path="data/example_prompts.json"):
    """Save prompts to JSON file."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output, 'w') as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Generated {len(prompts)} prompts → {output}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=200, help="Number of prompts")
    parser.add_argument("-o", default="data/example_prompts.json")
    args = parser.parse_args()
    
    prompts = generate_prompts(args.n)
    save_prompts(prompts, args.o)
    
    # Show sample
    print("\n📋 Sample prompts:")
    for p in random.sample(prompts, min(5, len(prompts))):
        print(f"  [{p['domain']}] {p['prompt']}")
