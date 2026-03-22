#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# 🧪 tiny-distill — One Command to Rule Them All
# 
# This script walks you through creating your own AI model.
# No experience needed. No pre-installed dependencies assumed.
#
# Usage:
#   git clone https://github.com/r2d2helper1-creator/tiny-distill.git
#   cd tiny-distill
#   bash setup.sh
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS="debian"
        elif [ -f /etc/redhat-release ]; then
            OS="redhat"
        else
            OS="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="mac"
    else
        OS="unknown"
    fi
}

# Install system package (cross-platform)
install_system_pkg() {
    local pkg_debian="$1"
    local pkg_redhat="$2"
    local pkg_mac="$3"
    
    case $OS in
        debian)
            apt-get install -y $pkg_debian 2>/dev/null
            ;;
        redhat)
            yum install -y $pkg_redhat 2>/dev/null
            ;;
        mac)
            if command -v brew &> /dev/null; then
                brew install $pkg_mac 2>/dev/null
            fi
            ;;
    esac
}

# ─── Main ────────────────────────────────────────────────────────────────────

banner
detect_os

echo -e "  ${DIM}Detected OS: $OS${NC}"
echo ""
echo -e "  ${DIM}This script will:${NC}"
echo -e "  ${DIM}  1. Install all system dependencies${NC}"
echo -e "  ${DIM}  2. Set up Python environment${NC}"
echo -e "  ${DIM}  3. Collect 1000 training examples${NC}"
echo -e "  ${DIM}  4. Clean the data${NC}"
echo -e "  ${DIM}  5. Give you a Colab notebook to train${NC}"
echo ""
echo -e "  ${DIM}Total time: 30 min to 3 hours (depends on method)${NC}"
echo -e "  ${DIM}Cost: \$0 (everything is free)${NC}"
echo ""

confirm

# ══════════════════════════════════════════════════════════════════════════════
# Step 1: Install system dependencies
# ══════════════════════════════════════════════════════════════════════════════

step "1" "Installing system dependencies"

info "Updating package lists..."
case $OS in
    debian)
        apt-get update -qq 2>/dev/null || true
        ;;
    redhat)
        yum makecache 2>/dev/null || true
        ;;
esac

# Check and install Python
if ! command -v python3 &> /dev/null; then
    info "Installing Python 3..."
    install_system_pkg "python3 python3-venv python3-pip" "python3 python3-pip" "python3"
fi

PYTHON="python3"
ok "Python: $($PYTHON --version 2>&1)"

# Check and install curl (needed for Ollama)
if ! command -v curl &> /dev/null; then
    info "Installing curl..."
    install_system_pkg "curl" "curl" "curl"
fi
ok "curl: $(curl --version 2>&1 | head -1)"

# Check and install git (needed for cloning)
if ! command -v git &> /dev/null; then
    info "Installing git..."
    install_system_pkg "git" "git" "git"
fi
ok "git: $(git --version 2>&1)"

# ─── Chromium system dependencies (for Playwright browser automation) ───────

info "Installing browser dependencies..."

case $OS in
    debian)
        # All Chromium/Playwright system deps for Debian/Ubuntu
        apt-get install -y -qq \
            libnss3 \
            libatk1.0-0 \
            libatk-bridge2.0-0 \
            libcups2 \
            libdrm2 \
            libxkbcommon0 \
            libxcomposite1 \
            libxdamage1 \
            libxrandr2 \
            libgbm1 \
            libpango-1.0-0 \
            libcairo2 \
            libasound2 \
            libxshmfence1 \
            libx11-xcb1 \
            fonts-liberation \
            libappindicator3-1 \
            libnspr4 \
            libxss1 \
            libgconf-2-4 \
            xdg-utils \
            wget \
            2>/dev/null || true
        ;;
    redhat)
        yum install -y \
            nss atk at-spi2-atk cups-libs libdrm libxkbcommon \
            libxcomposite libxdamage libxrandr mesa-libgbm pango \
            cairo alsa-lib libX11-xcb liberation-fonts \
            libappindicator-gtk3 nspr libXScrnSaver xdg-utils wget \
            2>/dev/null || true
        ;;
    mac)
        # macOS doesn't need these — Chromium comes bundled
        true
        ;;
esac

ok "System dependencies installed"

# ══════════════════════════════════════════════════════════════════════════════
# Step 2: Set up Python environment
# ══════════════════════════════════════════════════════════════════════════════

step "2" "Setting up Python environment"

# Create virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    ok "Virtual environment already exists"
else
    info "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
    ok "Virtual environment created"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"
ok "Virtual environment activated"

# Upgrade pip
info "Upgrading pip..."
$PIP install --upgrade pip --quiet 2>/dev/null

# Install core dependencies
info "Installing Python packages..."
$PIP install --quiet requests

ok "Python environment ready"

# ══════════════════════════════════════════════════════════════════════════════
# Step 3: Choose collection method
# ══════════════════════════════════════════════════════════════════════════════

step "3" "Choose how to collect training data"

echo -e "  You need to collect 1000 prompt-response pairs from AI models."
echo -e "  Choose your method:"
echo ""
echo -e "  ${BOLD}1)${NC} 📡 OpenRouter API (RECOMMENDED — fast, reliable, 100+ models!)"
echo -e "     ${DIM}Claude, GPT, Gemini, Llama — all via one API key.${NC}"
echo -e "     ${DIM}Just HTTP calls. No browser. No login issues.${NC}"
echo ""
echo -e "  ${BOLD}2)${NC} 🏟️  Arena.ai (398+ free models, needs browser)"
echo -e "     ${DIM}Claude Opus, GPT-5, Gemini 3, Grok 4 — all free!${NC}"
echo -e "     ${DIM}Just needs a browser. Handles rate limits automatically.${NC}"
echo ""
echo -e "  ${BOLD}3)${NC} 🦙 Ollama (runs on your computer)"
echo -e "     ${DIM}Free. No limits. No API keys. Downloads a small model.${NC}"
echo ""
echo -e "  ${BOLD}4)${NC} 📋 Manual Copy-Paste"
echo -e "     ${DIM}Shows you prompts, you paste into ChatGPT, paste back.${NC}"
echo -e "     ${DIM}No install needed. Takes ~2 hours.${NC}"
echo ""

ask "Which method? [1-4]:" METHOD
METHOD=${METHOD:-1}

# ══════════════════════════════════════════════════════════════════════════════
# Step 4: Set up and run collection
# ══════════════════════════════════════════════════════════════════════════════

case $METHOD in

    # ─────────────────────────────────────────────────────────────────────
    # Option 1: OpenRouter API (RECOMMENDED)
    # ─────────────────────────────────────────────────────────────────────
    1)
        step "4a" "Setting up OpenRouter"
        
        info "Installing requests (if not already installed)..."
        $PIP install --quiet requests
        
        # Get API key
        if [ -n "$OPENROUTER_API_KEY" ]; then
            info "Using OPENROUTER_API_KEY from environment"
        else
            echo ""
            echo -e "  ${BOLD}Get your API key:${NC}"
            echo -e "  1. Go to ${CYAN}https://openrouter.ai/keys${NC}"
            echo -e "  2. Sign up (free)"
            echo -e "  3. Create a new API key"
            echo -e "  4. Paste it below"
            echo ""
            ask "Your OpenRouter API key:" OPENROUTER_API_KEY
            
            if [ -z "$OPENROUTER_API_KEY" ]; then
                fail "No API key provided!"
                exit 1
            fi
        fi
        
        # Verify the key works
        info "Verifying API key..."
        VERIFY=$($PYTHON -c "
import requests, sys
r = requests.get('https://openrouter.ai/api/v1/auth/key',
    headers={'Authorization': 'Bearer $OPENROUTER_API_KEY'}, timeout=10)
if r.status_code == 200:
    data = r.json()['data']
    print(f'Key valid! Usage: \${data.get(\"usage\", 0):.2f} / \${data.get(\"limit\", \"unlimited\")}')
    sys.exit(0)
else:
    print(f'Key error: {r.status_code}')
    sys.exit(1)
" 2>&1)
        
        if [ $? -eq 0 ]; then
            ok "$VERIFY"
        else
            fail "API key verification failed: $VERIFY"
            exit 1
        fi
        
        step "4b" "Choose your model"
        
        echo ""
        echo -e "  ${BOLD}Available models:${NC}"
        echo -e "  ${CYAN}Tier 1 (best quality):${NC}"
        echo "    1) anthropic/claude-sonnet-4-6  (best value, fast + smart)"
        echo "    2) anthropic/claude-opus-4-6    (best overall)"
        echo "    3) openai/gpt-4o                (OpenAI strong)"
        echo "    4) google/gemini-2.5-pro        (Google's best)"
        echo -e "  ${CYAN}Tier 2 (cheaper/faster):${NC}"
        echo "    5) anthropic/claude-haiku-3     (fast & cheap)"
        echo "    6) openai/gpt-4o-mini           (fast & cheap)"
        echo "    7) google/gemini-2.0-flash      (very fast)"
        echo "    8) meta-llama/llama-3.3-70b-instruct (open source)"
        echo -e "  ${CYAN}Multi-model:${NC}"
        echo "    9) ALL tier 1 models (diversity for multi-teacher!)"
        echo ""
        
        ask "Which model? [1-9]:" MODEL_CHOICE
        MODEL_CHOICE=${MODEL_CHOICE:-1}
        
        case $MODEL_CHOICE in
            1) MODEL="anthropic/claude-sonnet-4-6"; MULTI="" ;;
            2) MODEL="anthropic/claude-opus-4-6"; MULTI="" ;;
            3) MODEL="openai/gpt-4o"; MULTI="" ;;
            4) MODEL="google/gemini-2.5-pro"; MULTI="" ;;
            5) MODEL="anthropic/claude-haiku-3"; MULTI="" ;;
            6) MODEL="openai/gpt-4o-mini"; MULTI="" ;;
            7) MODEL="google/gemini-2.0-flash"; MULTI="" ;;
            8) MODEL="meta-llama/llama-3.3-70b-instruct"; MULTI="" ;;
            9) MODEL="anthropic/claude-sonnet-4-6"; MULTI="--multi-model --models anthropic/claude-sonnet-4-6,openai/gpt-4o,google/gemini-2.0-flash" ;;
            *) MODEL="anthropic/claude-sonnet-4-6"; MULTI="" ;;
        esac
        
        ask "How many prompts? [1000]:" NUM_PROMPTS
        NUM_PROMPTS=${NUM_PROMPTS:-1000}
        
        echo ""
        if [ -n "$MULTI" ]; then
            echo -e "  ${BOLD}Collecting $NUM_PROMPTS prompts from MULTIPLE models${NC}"
        else
            echo -e "  ${BOLD}Collecting $NUM_PROMPTS prompts from $MODEL${NC}"
        fi
        echo -e "  ${DIM}API calls. Fast. Reliable. Progress saved as you go.${NC}"
        echo ""
        confirm
        
        $PYTHON "$SCRIPT_DIR/collect/openrouter_collector.py" \
            --api-key "$OPENROUTER_API_KEY" \
            --model $MODEL \
            --num-prompts $NUM_PROMPTS \
            --output "$SCRIPT_DIR/data/raw_dataset.jsonl" \
            $MULTI
        ;;

    # ─────────────────────────────────────────────────────────────────────
    # Option 2: Arena.ai
    # ─────────────────────────────────────────────────────────────────────
    2)
        step "4a" "Installing Playwright + Chromium"
        
        info "Installing playwright (Python package)..."
        $PIP install --quiet playwright
        
        info "Downloading Chromium browser (this may take a minute)..."
        $PYTHON -m playwright install --with-deps chromium 2>/dev/null || {
            warn "playwright install --with-deps failed, trying without deps..."
            $PYTHON -m playwright install chromium 2>/dev/null || {
                warn "Automatic Chromium install failed."
                info "Trying to install Chromium system package instead..."
                install_system_pkg "chromium-browser" "chromium" ""
                $PYTHON -m playwright install chromium 2>/dev/null || true
            }
        }
        
        # Verify playwright works
        $PYTHON -c "from playwright.async_api import async_playwright; print('OK')" 2>/dev/null && \
            ok "Playwright + Chromium ready!" || {
            fail "Playwright setup failed"
            echo "  Try manually:"
            echo "    pip install playwright"
            echo "    playwright install --with-deps chromium"
            exit 1
        }
        
        step "4b" "Collecting from Arena.ai (398+ free models!)"
        
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

    # ─────────────────────────────────────────────────────────────────────
    # Option 3: Ollama
    # ─────────────────────────────────────────────────────────────────────
    3)
        step "4a" "Setting up Ollama"
        
        if command -v ollama &> /dev/null; then
            ok "Ollama already installed!"
        else
            info "Downloading and installing Ollama..."
            curl -fsSL https://ollama.com/install.sh | sh
            ok "Ollama installed!"
        fi
        
        # Start Ollama server if not running
        if ! ollama list &> /dev/null 2>&1; then
            info "Starting Ollama server..."
            ollama serve &>/dev/null &
            sleep 5
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
        
        info "Downloading $MODEL (this may take a few minutes)..."
        ollama pull $MODEL
        ok "$MODEL ready!"
        
        ask "How many prompts? [1000]:" NUM_PROMPTS
        NUM_PROMPTS=${NUM_PROMPTS:-1000}
        
        step "4b" "Collecting data (this takes 1-3 hours)"
        echo ""
        echo -e "  ${BOLD}Collecting $NUM_PROMPTS responses from $MODEL${NC}"
        echo -e "  ${DIM}You can Ctrl+C anytime — progress is saved.${NC}"
        echo ""
        confirm
        
        $PYTHON "$SCRIPT_DIR/collect/ollama_collector.py" \
            --mode local \
            --model $MODEL \
            --num-prompts $NUM_PROMPTS \
            --output "$SCRIPT_DIR/data/raw_dataset.jsonl"
        ;;

    # ─────────────────────────────────────────────────────────────────────
    # Option 4: Manual
    # ─────────────────────────────────────────────────────────────────────
    4)
        step "4" "Manual collection"
        echo ""
        echo -e "  The collector will show you prompts one by one."
        echo -e "  Copy each prompt into ChatGPT/Claude, paste the response back."
        echo -e "  Press 's' to skip, 'q' to quit and save."
        echo ""
        confirm
        
        $PYTHON "$SCRIPT_DIR/collect/manual_collector.py"
        ;;

    *)
        fail "Invalid choice"
        exit 1
        ;;
esac

# ══════════════════════════════════════════════════════════════════════════════
# Step 5: Clean data
# ══════════════════════════════════════════════════════════════════════════════

step "5" "Cleaning your data"

$PYTHON "$SCRIPT_DIR/collect/cleaner.py" \
    --input-dir "$SCRIPT_DIR/data/" \
    --output "$SCRIPT_DIR/data/cleaned_dataset.jsonl"

ENTRY_COUNT=$(wc -l < "$SCRIPT_DIR/data/cleaned_dataset.jsonl" 2>/dev/null || echo "0")
ok "Cleaned dataset: $ENTRY_COUNT examples"

# ══════════════════════════════════════════════════════════════════════════════
# Step 6: Done!
# ══════════════════════════════════════════════════════════════════════════════

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

echo -e "  ${DIM}Questions? → https://github.com/r2d2helper1-creator/tiny-distill/issues${NC}"
echo -e "  ${DIM}Happy distilling! 🧪${NC}"
echo ""
