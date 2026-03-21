#!/usr/bin/env python3
"""
BitNet Distillation Training Script for tiny-distill
Fine-tunes a BitNet model on collected multi-teacher data.

Requirements:
  - GPU with 8GB+ VRAM (or use Colab/Kaggle notebooks for free GPU)
  - pip install torch transformers datasets accelerate peft

Usage:
  python train/train_bitnet.py --data data/cleaned_dataset.jsonl --output models/my-model
"""

import json
import os
import sys
import argparse
from pathlib import Path

def check_requirements():
    """Check if required packages are installed."""
    missing = []
    for pkg in ["torch", "transformers", "datasets", "accelerate"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print(f"   Install: pip install {' '.join(missing)}")
        sys.exit(1)

def load_training_data(data_path):
    """Load and format training data."""
    examples = []
    with open(data_path) as f:
        for line in f:
            entry = json.loads(line.strip())
            # Format as conversation for SFT
            examples.append({
                "messages": [
                    {"role": "user", "content": entry["prompt"]},
                    {"role": "assistant", "content": entry["response"]}
                ]
            })
    return examples

def train(
    data_path,
    base_model="microsoft/bitnet-b1.58-2B-4T-bf16",
    output_dir="models/my-bitnet-model",
    epochs=3,
    batch_size=4,
    learning_rate=2e-5,
    max_seq_length=2048,
    use_lora=True,
    lora_r=16,
    lora_alpha=32,
    gradient_accumulation_steps=4,
    warmup_ratio=0.1,
    logging_steps=10,
    save_steps=500,
):
    """
    Train a BitNet model via supervised fine-tuning.
    
    Uses LoRA by default to reduce VRAM requirements.
    Full fine-tuning needs ~16GB VRAM; LoRA needs ~6-8GB.
    """
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForSeq2Seq,
    )
    from datasets import Dataset
    
    print(f"\n🧪 tiny-distill training")
    print(f"   Base model: {base_model}")
    print(f"   Data: {data_path}")
    print(f"   Output: {output_dir}")
    print(f"   LoRA: {use_lora}")
    print(f"   Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    
    # Check GPU
    if not torch.cuda.is_available():
        print("\n⚠️  No GPU detected! Training will be VERY slow on CPU.")
        print("   Recommended: Use Google Colab or Kaggle for free GPU.")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    # Load data
    print(f"\n📂 Loading data...")
    raw_data = load_training_data(data_path)
    print(f"   Loaded {len(raw_data)} examples")
    
    # Load model and tokenizer
    print(f"\n🧠 Loading model {base_model}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    
    # Apply LoRA if requested
    if use_lora:
        try:
            from peft import LoraConfig, get_peft_model, TaskType
            
            print(f"\n🔧 Applying LoRA (r={lora_r}, alpha={lora_alpha})...")
            lora_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=lora_r,
                lora_alpha=lora_alpha,
                lora_dropout=0.05,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj", 
                               "gate_proj", "up_proj", "down_proj"],
            )
            model = get_peft_model(model, lora_config)
            model.print_trainable_parameters()
        except ImportError:
            print("⚠️  peft not installed, skipping LoRA (full fine-tuning)")
            use_lora = False
    
    # Tokenize
    print(f"\n🔤 Tokenizing...")
    
    def tokenize_function(examples):
        texts = []
        for messages in examples["messages"]:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            texts.append(text)
        
        tokenized = tokenizer(
            texts,
            truncation=True,
            max_length=max_seq_length,
            padding=False,
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized
    
    dataset = Dataset.from_list(raw_data)
    tokenized_dataset = dataset.map(
        tokenize_function, 
        batched=True,
        remove_columns=dataset.column_names,
        desc="Tokenizing"
    )
    
    print(f"   Tokenized {len(tokenized_dataset)} examples")
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_ratio=warmup_ratio,
        logging_steps=logging_steps,
        save_steps=save_steps,
        save_total_limit=3,
        bf16=torch.cuda.is_available(),
        fp16=False,
        optim="adamw_torch",
        lr_scheduler_type="cosine",
        report_to="none",
        remove_unused_columns=False,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True),
    )
    
    # Train!
    print(f"\n🚀 Starting training...")
    trainer.train()
    
    # Save
    print(f"\n💾 Saving model to {output_dir}...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"""
✅ Training complete!

Model saved to: {output_dir}

Next steps:
  1. Test your model:
     python train/evaluate.py --model {output_dir}
  
  2. Convert for bitnet.cpp inference (CPU):
     # See: https://github.com/microsoft/BitNet
  
  3. Upload to Hugging Face:
     huggingface-cli upload {output_dir}
""")

def main():
    parser = argparse.ArgumentParser(description="Train BitNet model via distillation")
    parser.add_argument("--data", required=True, help="Training data JSONL file")
    parser.add_argument("--base-model", default="microsoft/bitnet-b1.58-2B-4T-bf16",
                       help="Base BitNet model to fine-tune")
    parser.add_argument("--output", default="models/my-bitnet-model")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--no-lora", action="store_true", help="Full fine-tuning (needs more VRAM)")
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--gradient-accumulation", type=int, default=4)
    args = parser.parse_args()
    
    check_requirements()
    
    train(
        data_path=args.data,
        base_model=args.base_model,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_seq_length=args.max_seq_length,
        use_lora=not args.no_lora,
        lora_r=args.lora_r,
        gradient_accumulation_steps=args.gradient_accumulation,
    )

if __name__ == "__main__":
    main()
