#!/bin/bash
# 🧪 tiny-distill — One-Command Data Collection
# Run this on YOUR machine (laptop/desktop with a browser)
#
# Usage:
#   chmod +x run-collection.sh
#   ./run-collection.sh
#
# What it does:
#   1. Installs dependencies
#   2. Generates 1000 smart prompts
#   3. Collects responses from Ollama (free, local) or browser (ChatGPT/Claude)
#   4. Cleans the data
#   5. Gives you a training-ready dataset

set -e

echo "🧪 tiny-distill Data Collection"
echo "================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install it first."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install requests --quiet 2>/dev/null || python3 -m pip install requests --quiet

# Check for Ollama (preferred — free, no limits)
if command -v ollama &> /dev/null; then
    echo "✅ Ollama found!"
    echo ""
    echo "Which model to use?"
    echo "  1. phi3:3.8b     (2.3GB, recommended)"
    echo "  2. qwen2.5:3b    (1.9GB)"
    echo "  3. llama3.2:3b   (2.0GB)"
    echo "  4. gemma2:2b     (1.6GB, smallest)"
    echo ""
    read -p "Choice [1]: " model_choice
    model_choice=${model_choice:-1}
    
    case $model_choice in
        1) MODEL="phi3:3.8b" ;;
        2) MODEL="qwen2.5:3b" ;;
        3) MODEL="llama3.2:3b" ;;
        4) MODEL="gemma2:2b" ;;
        *) MODEL="phi3:3.8b" ;;
    esac
    
    echo ""
    echo "📥 Pulling $MODEL (if not already downloaded)..."
    ollama pull $MODEL
    
    echo ""
    echo "🚀 Starting collection from Ollama ($MODEL)..."
    echo "   This will collect 1000 prompt-response pairs."
    echo "   Estimated time: 1-3 hours (depending on your hardware)"
    echo ""
    
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    python3 "$SCRIPT_DIR/collect/ollama_collector.py" \
        --mode local \
        --model $MODEL \
        --num-prompts 1000 \
        --output data/ollama_dataset.jsonl

else
    echo "⚠️  Ollama not found."
    echo ""
    echo "Option A: Install Ollama (recommended, 100% free)"
    echo "   → https://ollama.com/download"
    echo "   → Then run this script again"
    echo ""
    echo "Option B: Use browser automation (collect from ChatGPT/Claude web)"
    echo "   → Requires: pip3 install browser-use playwright"
    echo "   → Then: python3 collect/browser_collector.py --provider chatgpt --num-prompts 1000"
    echo ""
    echo "Option C: Use manual copy-paste mode (no install needed)"
    echo "   → python3 collect/manual_collector.py"
    echo ""
    read -p "Which option? [C]: " option
    option=${option:-C}
    
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    
    case $option in
        [Aa])
            echo "Go to https://ollama.com/download and install, then run this script again."
            exit 0
            ;;
        [Bb])
            echo "Installing browser-use..."
            pip3 install browser-use playwright
            playwright install chromium
            echo "Starting browser collection..."
            python3 "$SCRIPT_DIR/collect/browser_collector.py" --provider chatgpt --num-prompts 1000
            ;;
        *)
            echo "Starting manual collection..."
            python3 "$SCRIPT_DIR/collect/manual_collector.py"
            ;;
    esac
fi

echo ""
echo "🧹 Cleaning data..."
python3 collect/cleaner.py --input-dir data/ --output data/cleaned_dataset.jsonl

echo ""
echo "✅ Done! Your dataset is ready at: data/cleaned_dataset.jsonl"
echo ""
echo "Next steps:"
echo "  1. Open notebooks/train_colab.ipynb in Google Colab"
echo "  2. Upload data/cleaned_dataset.jsonl"
echo "  3. Click 'Run All'"
echo "  4. Download your trained model!"
echo ""
echo "🧪 Happy distilling!"
