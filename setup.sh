#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# 🧪 tiny-distill — One Command to Rule Them All
# 
# This script walks you through creating your own AI model.
# No experience needed. Just run it and follow along.
#
# Usage:
#   curl -sSL https://tiny-distill.com/setup.sh | bash
#   OR
#   git clone https://github.com/r2d2helper1-creator/tiny-distill.git && cd tiny-distill && bash setup.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e

# ─── Colors ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ─── Helpers ─────────────────────────────────────────────────────────────────

banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║${NC}   ${BOLD}🧪  tiny-distill${NC}                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}   ${DIM}Distill your own AI model. No GPU. No API keys.${NC}            ${CYAN}║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Step $1: $2${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

info() { echo -e "  ${CYAN}ℹ${NC}  $1"; }
ok()   { echo -e "  ${GREEN}✅${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠️${NC}  $1"; }
fail() { echo -e "  ${RED}❌${NC} $1"; }

ask() {
    echo ""
    echo -e "  ${BOLD}$1${NC}"
    read -p "  > " "$2"
}

confirm() {
    read -p "  Press Enter to continue..." dummy
}

# ─── Main ────────────────────────────────────────────────────────────────────

banner

echo -e "  ${DIM}This script will help you:${NC}"
echo -e "  ${DIM}  1. Set up data collection${NC}"
echo -e "  ${DIM}  2. Collect 1000 prompt-response pairs${NC}"
echo -e "  ${DIM}  3. Clean the data${NC}"
echo -e "  ${DIM}  4. Give you a Colab notebook to train your model${NC}"
echo ""
echo -e "  ${DIM}Total time: 30 min to 3 hours (depends on method)${NC}"
echo -e "  ${DIM}Cost: \$0 (everything is free)${NC}"
echo ""

confirm

# ─── Step 1: Check Python ────────────────────────────────────────────────────

step "1" "Checking your setup"

PYTHON=""
if command -v python3 &> /dev/null; then
    PYTHON="python3"
    ok "Python 3 found: $(python3 --version)"
elif command -v python &> /dev/null; then
    PYTHON="python"
    ok "Python found: $(python --version)"
else
    fail "Python not found!"
    echo ""
    echo "  Install Python 3.8+ first:"
    echo "    Mac:    brew install python3"
    echo "    Ubuntu: sudo apt install python3 python3-pip"
    echo "    Windows: https://python.org/downloads"
    exit 1
fi

# Check pip
PIP=""
if command -v pip3 &> /dev/null; then
    PIP="pip3"
elif command -v pip &> /dev/null; then
    PIP="pip"
elif $PYTHON -m pip --version &> /dev/null; then
    PIP="$PYTHON -m pip"
else
    warn "pip not found — will try to install"
    $PYTHON -m ensurepip 2>/dev/null || true
    PIP="$PYTHON -m pip"
fi

ok "Package manager: $PIP"

# ─── Step 2: Install dependencies ───────────────────────────────────────────

step "2" "Installing dependencies"

info "Installing requests..."
$PIP install requests --quiet 2>/dev/null || $PYTHON -m pip install requests --quiet
ok "requests installed"

# ─── Step 3: Choose collection method ───────────────────────────────────────

step "3" "Choose how to collect training data"

echo -e "  You need to collect 1000 prompt-response pairs from AI models."
echo -e "  Choose your method:"
echo ""
echo -e "  ${BOLD}1)${NC} 🏟️  Arena.ai (BEST — 398+ free models!)"
echo -e "     ${DIM}Claude Opus, GPT-5, Gemini 3, Grok 4 — all free!${NC}"
echo -e "     ${DIM}Just needs a browser. Handles rate limits automatically.${NC}"
echo ""
echo -e "  ${BOLD}2)${NC} 🦙 Ollama (recommended if no browser)"
echo -e "     ${DIM}Free. Runs on your computer. No limits. No API keys.${NC}"
echo -e "     ${DIM}Requires: ~2GB disk space for model download${NC}"
echo ""
echo -e "  ${BOLD}2)${NC} 🌐 Browser Automation"
echo -e "     ${DIM}Goes to ChatGPT/Claude website, collects automatically.${NC}"
echo -e "     ${DIM}Requires: Chromium browser, logged into ChatGPT/Claude${NC}"
echo ""
echo -e "  ${BOLD}3)${NC} 📋 Manual Copy-Paste"
echo -e "     ${DIM}Shows you prompts, you paste into ChatGPT, paste back.${NC}"
echo -e "     ${DIM}No install needed. Takes ~2 hours.${NC}"
echo ""
echo -e "  ${BOLD}4)${NC} 🔑 API (fastest, costs money)"
echo -e "     ${DIM}Uses OpenAI/Anthropic API. ~$5 for 1000 prompts.${NC}"
echo ""

ask "Which method? [1-4]:" METHOD
METHOD=${METHOD:-1}

# ─── Step 4: Set up collection ───────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case $METHOD in
    1)
        # ─── Arena.ai ────────────────────────────────────────────────────
        step "4" "Collecting from Arena.ai (398+ free models!)"
        
        echo ""
        echo -e "  ${BOLD}Available models:${NC}"
        echo -e "  ${CYAN}Tier 1 (best quality):${NC}"
        echo "    1) claude-opus-4-6      (Anthropic #1)"
        echo "    2) gpt-5.4-high         (OpenAI latest)"
        echo "    3) gemini-3.1-pro       (Google #3)"
        echo "    4) grok-4.20-beta       (xAI reasoning)"
        echo -e "  ${CYAN}Tier 2 (fast + smart):${NC}"
        echo "    5) claude-sonnet-4-6    (great for coding)"
        echo "    6) gpt-5.2-chat-latest  (solid all-rounder)"
        echo "    7) gemini-3-pro         (Google strong)"
        echo "    8) grok-4.1             (xAI fast)"
        echo -e "  ${CYAN}Multi-model:${NC}"
        echo "    9) ALL tier 1 models (best quality + diversity)"
        echo ""
        
        ask "Which model? [1-9]:" MODEL_CHOICE
        MODEL_CHOICE=${MODEL_CHOICE:-1}
        
        case $MODEL_CHOICE in
            1) MODEL="claude-opus-4-6"; MULTI="" ;;
            2) MODEL="gpt-5.4-high-no-system-prompt"; MULTI="" ;;
            3) MODEL="gemini-3.1-pro"; MULTI="" ;;
            4) MODEL="grok-4.20-beta-0309-reasoning"; MULTI="" ;;
            5) MODEL="claude-sonnet-4-6"; MULTI="" ;;
            6) MODEL="gpt-5.2-chat-latest"; MULTI="" ;;
            7) MODEL="gemini-3-pro"; MULTI="" ;;
            8) MODEL="grok-4.1"; MULTI="" ;;
            9) MODEL="claude-opus-4-6"; MULTI="--multi-model --models claude-opus-4-6,gpt-5.2-chat-latest,gemini-3-pro,grok-4.1" ;;
            *) MODEL="claude-opus-4-6"; MULTI="" ;;
        esac
        
        ask "How many prompts? [1000]:" NUM_PROMPTS
        NUM_PROMPTS=${NUM_PROMPTS:-1000}
        
        echo ""
        if [ -n "$MULTI" ]; then
            echo -e "  ${BOLD}Collecting $NUM_PROMPTS prompts from MULTIPLE models${NC}"
        else
            echo -e "  ${BOLD}Collecting $NUM_PROMPTS prompts from $MODEL${NC}"
        fi
        echo -e "  ${DIM}Browser will open. Handles rate limits automatically.${NC}"
        echo -e "  ${DIM}You can Ctrl+C anytime — progress is saved.${NC}"
        echo ""
        confirm
        
        $PYTHON "$SCRIPT_DIR/collect/arena_collector.py" \
            --model $MODEL \
            --num-prompts $NUM_PROMPTS \
            --output "$SCRIPT_DIR/data/raw_dataset.jsonl" \
            $MULTI
        ;;
    
    2)
        # ─── Ollama ──────────────────────────────────────────────────────
        step "4a" "Setting up Ollama"
        
        if command -v ollama &> /dev/null; then
            ok "Ollama already installed!"
        else
            info "Installing Ollama..."
            echo ""
            echo -e "  ${DIM}This will download Ollama from https://ollama.com${NC}"
            echo -e "  ${DIM}If you prefer, install manually from https://ollama.com/download${NC}"
            echo ""
            
            if [[ "$OSTYPE" == "darwin"* ]]; then
                if command -v brew &> /dev/null; then
                    brew install ollama
                else
                    curl -fsSL https://ollama.com/install.sh | sh
                fi
            else
                curl -fsSL https://ollama.com/install.sh | sh
            fi
            ok "Ollama installed!"
        fi
        
        if ! ollama list &> /dev/null; then
            info "Starting Ollama server..."
            ollama serve &>/dev/null &
            sleep 3
        fi
        
        echo ""
        echo -e "  ${BOLD}Which model?${NC}"
        echo "  1) phi3:3.8b     (2.3GB, best balance)"
        echo "  2) qwen2.5:3b    (1.9GB, multilingual)"
        echo "  3) llama3.2:3b   (2.0GB, Meta's best small)"
        echo "  4) gemma2:2b     (1.6GB, smallest)"
        
        ask "Model [1]:" MODEL_CHOICE
        MODEL_CHOICE=${MODEL_CHOICE:-1}
        
        case $MODEL_CHOICE in
            1) MODEL="phi3:3.8b" ;;
            2) MODEL="qwen2.5:3b" ;;
            3) MODEL="llama3.2:3b" ;;
            4) MODEL="gemma2:2b" ;;
            *) MODEL="phi3:3.8b" ;;
        esac
        
        info "Pulling $MODEL (this may take a few minutes)..."
        ollama pull $MODEL
        ok "$MODEL ready!"
        
        ask "How many prompts? [1000]:" NUM_PROMPTS
        NUM_PROMPTS=${NUM_PROMPTS:-1000}
        
        step "4b" "Collecting data (this takes 1-3 hours)"
        echo ""
        echo -e "  ${BOLD}Collecting $NUM_PROMPTS responses from $MODEL${NC}"
        echo -e "  ${DIM}Estimated time: ~$((NUM_PROMPTS * 5 / 60)) minutes${NC}"
        echo -e "  ${DIM}You can Ctrl+C anytime — progress is saved automatically${NC}"
        echo ""
        confirm
        
        $PYTHON "$SCRIPT_DIR/collect/ollama_collector.py" \
            --mode local \
            --model $MODEL \
            --num-prompts $NUM_PROMPTS \
            --output "$SCRIPT_DIR/data/raw_dataset.jsonl"
        ;;
    
    3)
        # ─── Browser Automation ──────────────────────────────────────────
        step "4a" "Setting up browser automation"
        
        info "Installing browser-use and Playwright..."
        $PIP install browser-use --quiet 2>/dev/null || $PYTHON -m pip install browser-use --quiet
        
        if ! command -v playwright &> /dev/null; then
            $PYTHON -m playwright install chromium 2>/dev/null || {
                warn "Playwright install had issues. Trying anyway..."
            }
        fi
        ok "Browser tools ready!"
        
        echo ""
        echo -e "  ${BOLD}Which website?${NC}"
        echo "  1) ChatGPT (chat.openai.com)"
        echo "  2) Claude (claude.ai)"
        echo "  3) Gemini (gemini.google.com)"
        
        ask "Website [1]:" SITE_CHOICE
        SITE_CHOICE=${SITE_CHOICE:-1}
        
        case $SITE_CHOICE in
            1) PROVIDER="chatgpt" ;;
            2) PROVIDER="claude" ;;
            3) PROVIDER="gemini" ;;
            *) PROVIDER="chatgpt" ;;
        esac
        
        echo ""
        warn "Make sure you're logged into $PROVIDER in your browser!"
        confirm
        
        step "4b" "Collecting data via browser"
        
        $PYTHON "$SCRIPT_DIR/collect/browser_collector.py" \
            --provider $PROVIDER \
            --num-prompts 1000 \
            --no-headless
        ;;
    
    4)
        # ─── Manual ──────────────────────────────────────────────────────
        step "4" "Manual collection"
        echo ""
        echo -e "  The collector will show you prompts one by one."
        echo -e "  Copy each prompt into ChatGPT/Claude, paste the response back."
        echo -e "  Press 's' to skip, 'q' to quit and save."
        echo ""
        confirm
        
        $PYTHON "$SCRIPT_DIR/collect/manual_collector.py"
        ;;
    
    5)
        # ─── API ─────────────────────────────────────────────────────────
        step "4" "API collection"
        
        echo ""
        echo -e "  ${BOLD}Which API?${NC}"
        echo "  1) OpenAI (GPT-4o-mini, cheapest)"
        echo "  2) Anthropic (Claude)"
        
        ask "API [1]:" API_CHOICE
        API_CHOICE=${API_CHOICE:-1}
        
        case $API_CHOICE in
            1)
                PROVIDER="openai"
                ENV_KEY="OPENAI_API_KEY"
                ;;
            2)
                PROVIDER="anthropic"
                ENV_KEY="ANTHROPIC_API_KEY"
                ;;
            *)
                PROVIDER="openai"
                ENV_KEY="OPENAI_API_KEY"
                ;;
        esac
        
        if [ -z "${!ENV_KEY}" ]; then
            ask "Enter your $ENV_KEY:" API_KEY
            export $ENV_KEY="$API_KEY"
        fi
        
        info "Estimated cost: ~\$5 for 1000 prompts"
        confirm
        
        $PYTHON "$SCRIPT_DIR/collect/api_collector.py" \
            --provider $PROVIDER \
            --num-prompts 1000
        ;;
    
    *)
        fail "Invalid choice"
        exit 1
        ;;
esac

# ─── Step 5: Clean data ─────────────────────────────────────────────────────

step "5" "Cleaning your data"

$PYTHON "$SCRIPT_DIR/collect/cleaner.py" \
    --input-dir "$SCRIPT_DIR/data/" \
    --output "$SCRIPT_DIR/data/cleaned_dataset.jsonl"

# Count entries
ENTRY_COUNT=$(wc -l < "$SCRIPT_DIR/data/cleaned_dataset.jsonl" 2>/dev/null || echo "0")
ok "Cleaned dataset: $ENTRY_COUNT examples"

# ─── Step 6: Done! ──────────────────────────────────────────────────────────

step "6" "You're ready to train! 🎉"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${NC}   ${BOLD}✅  Data Collection Complete!${NC}                             ${GREEN}║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${NC}   Dataset: $ENTRY_COUNT prompt-response pairs                      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}   File: data/cleaned_dataset.jsonl                          ${GREEN}║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${NC}   ${BOLD}Next steps:${NC}                                               ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                              ║${NC}"
echo -e "${GREEN}║${NC}   1. Go to https://colab.research.google.com                 ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}   2. Upload: notebooks/train_colab.ipynb                     ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}   3. Upload: data/cleaned_dataset.jsonl                      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}   4. Click 'Run All'                                        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}   5. Wait ~2 hours                                          ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}   6. Download your model! 🎉                                ${GREEN}║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Open Colab if on Mac
if [[ "$OSTYPE" == "darwin"* ]]; then
    ask "Open Google Colab in your browser? [Y/n]:" OPEN_COLAB
    OPEN_COLAB=${OPEN_COLAB:-Y}
    if [[ "$OPEN_COLAB" =~ ^[Yy]$ ]]; then
        open "https://colab.research.google.com"
    fi
fi

echo -e "  ${DIM}Questions? Issues? → https://github.com/r2d2helper1-creator/tiny-distill/issues${NC}"
echo -e "  ${DIM}Happy distilling! 🧪${NC}"
echo ""
