#!/bin/bash
# ============================================================
#  ECOM SWARM - Termux Setup Script
#  Run this once: bash setup.sh
# ============================================================

echo ""
echo "██████████████████████████████████████████"
echo "   ECOM SWARM - AI Agent Setup for Termux  "
echo "██████████████████████████████████████████"
echo ""

# --- Termux packages ---
echo "[1/5] Installing Termux system packages..."
pkg update -y && pkg upgrade -y
pkg install -y python python-pip git clang libffi openssl rust nodejs

# --- Python deps ---
echo "[2/5] Installing Python packages..."
pip install --upgrade pip
pip install google-generativeai requests beautifulsoup4 rich python-dotenv \
    Pillow aiohttp lxml colorama pyfiglet

# --- Install Agent-Browser (Vercel Labs) ---
echo "[3/5] Installing Agent-Browser CLI..."
npm install -g agent-browser
agent-browser install

# --- Install OpenAI Swarm from GitHub ---
echo "[4/5] Installing OpenAI Swarm..."
pip install git+https://github.com/openai/swarm.git

# --- Create .env if not exists ---
echo "[5/5] Setting up config..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys!"
    echo "   nano .env"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Quick start:"
echo "  python main.py                    # Interactive menu"
echo "  python main.py --agent seo        # Run SEO agent alone"
echo "  python main.py --swarm full       # Run full swarm"
echo "  python main.py --swarm product    # Product research swarm"
echo "  python main.py --swarm marketing  # Marketing swarm"
echo ""
