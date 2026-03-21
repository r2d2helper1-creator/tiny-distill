# 🧪 tiny-distill

**Distill your own AI model. No GPU, no API keys, no problem.**

Create a small, fast, private AI model from big models like ChatGPT, Claude, or Gemini — just by chatting.

---

## 🤯 What is this?

`tiny-distill` is a toolkit that lets anyone create their own compressed AI model by collecting responses from existing AI chat interfaces (ChatGPT, Claude, Gemini, etc.) and distilling that knowledge into a tiny [BitNet](https://github.com/microsoft/BitNet) model.

**You don't need:**
- ❌ An API key
- ❌ A GPU
- ❌ Coding experience
- ❌ An open-source model
- ❌ Money (free tier everything)

**You just need:**
- ✅ A web browser
- ✅ Access to ChatGPT, Claude, or any AI chat
- ✅ ~30 minutes of chatting

---

## 🚀 Quick Start

### Option 1: Ollama (Free — no API key, multiple models!)

```bash
# Option A: Ollama Cloud (free tier, many models)
export OLLAMA_API_KEY="your-key"  # Get from https://ollama.com/settings
python collect/ollama_collector.py --mode cloud --multi-model

# Option B: Ollama Local (100% free, runs on your machine)
# First: install Ollama → https://ollama.com/download
# Then: ollama pull llama3.1:8b
python collect/ollama_collector.py --mode local --model llama3.1:8b
```

### Option 2: Manual Chat Mode (Zero Setup — copy-paste from ChatGPT)

```bash
# 1. Clone the repo
git clone https://github.com/r2d2helper1-creator/tiny-distill.git
cd tiny-distill

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start collecting data via chat
python collect/manual_collector.py

# 4. Follow the prompts — it'll tell you exactly what to paste into ChatGPT/Claude
# 5. Paste responses back — it saves everything automatically
```

### Option 2: API Mode (Automated, needs API key)

```bash
# Set your API key
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."

# Run automated collection
python collect/api_collector.py --provider openai --num-prompts 1000
```

### Option 3: Train Your Model

**Free GPU (recommended):**
1. Upload your collected data to Google Colab or Kaggle
2. Open the included notebook: `notebooks/train_distill.ipynb`
3. Click "Run All" — it trains your BitNet model on free GPU

**Local (needs GPU):**
```bash
python train/train_bitnet.py --data data/my_dataset.jsonl --output models/my-model
```

---

## 📁 Project Structure

```
tiny-distill/
├── collect/
│   ├── manual_collector.py    # Chat-based data collection (no API key)
│   ├── ollama_collector.py    # Ollama cloud + local collection (FREE!)
│   ├── api_collector.py       # Automated API collection
│   ├── prompt_generator.py    # Smart prompt generation
│   └── cleaner.py             # Data cleaning & deduplication
├── train/
│   ├── train_bitnet.py        # Main training script
│   ├── config.py              # Training configurations
│   └── evaluate.py            # Model evaluation
├── notebooks/
│   ├── train_colab.ipynb      # Google Colab notebook (free GPU)
│   └── train_kaggle.ipynb     # Kaggle notebook (free GPU)
├── data/
│   └── example_prompts.json   # Starter prompt sets
├── models/                    # Your trained models go here
├── requirements.txt
└── README.md
```

---

## 🧠 How It Works

### The Distillation Pipeline

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Big Models    │     │  Data Pipeline  │     │  Tiny Model     │
│  (ChatGPT,      │────▶│  Collect, Clean,│────▶│  (BitNet 1.58   │
│   Claude, etc.) │     │  Deduplicate    │     │   3B-7B param)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. **Generate prompts** — Smart, diverse prompts across domains (coding, reasoning, creative, factual)
2. **Collect responses** — From multiple teachers (API or manual copy-paste)
3. **Purify knowledge** — Pick the best response per prompt, or ensemble them
4. **Train student** — Fine-tune a BitNet model on the collected data
5. **Deploy** — Run your tiny model on CPU, phone, Raspberry Pi

### Why BitNet?

- **1.58-bit weights** ({-1, 0, +1}) = ~10-16× smaller than full precision
- **Runs on CPU** — No GPU needed for inference
- **Fast** — 3× faster than equivalent BF16 models
- **Energy efficient** — 55-82% less power consumption
- **Open source** — Microsoft's official BitNet framework

---

## 📊 What Can You Distill?

| Teacher | Method | Quality | Cost |
|---------|--------|---------|------|
| ChatGPT (web) | Manual copy-paste | ⭐⭐⭐⭐⭐ | Free |
| Claude (web) | Manual copy-paste | ⭐⭐⭐⭐⭐ | Free |
| Gemini (web) | Manual copy-paste | ⭐⭐⭐⭐ | Free |
| Ollama Cloud | Automated | ⭐⭐⭐⭐⭐ | Free (token limit) |
| Ollama Local | Automated | ⭐⭐⭐⭐ | 100% Free |
| OpenAI API | Automated | ⭐⭐⭐⭐⭐ | ~$0.01/1K prompts |
| Anthropic API | Automated | ⭐⭐⭐⭐⭐ | ~$0.01/1K prompts |
| Multiple teachers | Ensemble | ⭐⭐⭐⭐⭐+ | Varies |

**Pro tip:** Using multiple teachers and picking the best response often produces a student that's BETTER than any single teacher on specific tasks.

---

## 🛠️ Requirements

### For Data Collection (any computer)
- Python 3.8+
- No GPU needed
- ~100MB disk space

### For Training
**Free option (Google Colab):**
- Google account
- ~15 min setup

**Free option (Kaggle):**
- Kaggle account
- 30 hours/week GPU time

**Local (optional):**
- NVIDIA GPU with 8GB+ VRAM
- Or: Apple Silicon Mac (M1+)

### For Inference (running your model)
- Any computer with 2GB+ RAM
- Works on CPU — no GPU needed!

---

## 🗺️ Roadmap

- [x] Manual chat collector
- [x] API-based collector (OpenAI, Anthropic)
- [x] Ollama collector (cloud + local, free!)
- [x] Smart prompt generator
- [x] Data cleaner & deduplicator
- [x] Training script (BitNet fine-tuning)
- [x] Google Colab notebook
- [x] Kaggle notebook
- [ ] Multi-teacher knowledge purification
- [ ] Web UI for easier collection
- [ ] One-click deploy to Hugging Face
- [ ] Mobile-friendly collection (chat on phone!)
- [ ] MoE ternary support
- [ ] Real-time quality scoring

---

## 📝 License

MIT — do whatever you want with it.

---

## 🙏 Credits

- [Microsoft BitNet](https://github.com/microsoft/BitNet) — The 1.58-bit inference framework
- [HuggingFace Transformers](https://github.com/huggingface/transformers) — BitNet model support
- [llama.cpp](https://github.com/ggerganov/llama.cpp) — Foundation for bitnet.cpp

---

*"The best model is the one you can run."* 🧪
