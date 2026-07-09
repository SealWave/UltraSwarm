# 🐝 ECOM SWARM — AI Agent System

**A scalable multi-agent swarm for e-commerce automation**
Built for Windows & Termux | Powered by Gemini 2.5 Flash (Free)
Browsing Powered by: **browser-use** with **DuckDuckGo** search

---

## 🚀 Quick Setup Guide

### 1. Requirements
- Python 3.10+
- Node.js
- Docker (optional, for containerized deployment)

### 2. Install Dependencies
Run the following command to install everything you need:
```bash
pip install -r requirements.txt
```

### 3. Configuration (.env)
Create a `.env` file from `.env.example` and add your keys. 
**Important Settings:**
- `GOOGLE_API_KEY`: Required for the Gemini models.
- `BROWSER_HEADLESS=false`: **Crucial if you want to see the browser agent working in real-time.** If this is missing or set to true, the browser will run invisibly in the background.

Example `.env`:
```env
GOOGLE_API_KEY=your_api_key_here
BROWSER_HEADLESS=false
BROWSER_USE_AUTO_START=true
```

*(Optional)* For the best Windows browser-use experience, run the included script to attach the agent to a dedicated Chrome profile:
```powershell
.\run_browser.ps1
```

---

## 🐳 Docker Support

UltraSwarm includes full Docker support for Windows, Linux, and Arch Linux.

### Quick Docker Start

```bash
# Linux/macOS
./run_docker.sh

# Windows (PowerShell)
.\run_docker.ps1
```

### Docker Compose

```bash
docker-compose up
```

### Platform-Specific Guides
- [Docker Guide for Windows](DOCKER_README.md#windows)
- [Docker Guide for Linux](DOCKER_README.md#linux)
- [Docker Guide for Arch Linux](DOCKER_README.md#arch-linux)

### Docker Files
- `Dockerfile` - Production image
- `Dockerfile.dev` - Development image with hot reload
- `docker-compose.yml` - Compose configuration
- `run_docker.sh` - Linux/macOS script
- `run_docker.ps1` - Windows PowerShell script
- `docker-bake.hcl` - Multi-platform build configuration

See the full [Docker README](DOCKER_README.md) for more details.

---

## 📱 Usage

Run the main dashboard to access all agents and swarms interactively:
```bash
python main.py
```

### 🤖 The Agents
- **SERAPH (SEO)**: Live web research, keyword strategy, competitor analysis.
- **SCOUT (Product)**: Product researcher, sources products and creates full store listings. *Now supports custom product counts and specific genre targeting.*
- **PULSE (Ads)**: Ad copywriter for Google Ads, Meta, TikTok campaigns.
- **VIBE (Social)**: Social strategist for Instagram/TikTok scripts and 30-day calendars.
- **CANVAS (Banners)**: Visual director for banner briefs and ad creatives.
- **FORGE (Store Manager)**: Operations manager to push products and create launch plans.
- **BROWSE**: Simple plain-text-to-browser operator.

---

## 🐝 The Swarms (Pipelines)
Combine agents to complete massive tasks:
- **Full Launch**: All 6 agents for a complete product launch package.
- **Product Research**: SERAPH + SCOUT + FORGE.
- **Marketing**: SERAPH + PULSE + VIBE + CANVAS.
- **SEO Deep Dive**: SERAPH only.

---

## 📁 Project Structure

```
ecom_swarm/
├── main.py                    ← Master entry point
├── .env                       ← Your config & API keys
├── requirements.txt           ← Dependencies
├── Dockerfile                 ← Production Docker image
├── Dockerfile.dev             ← Development Docker image
├── docker-compose.yml         ← Compose configuration
├── run_docker.sh              ← Linux/macOS Docker script
├── run_docker.ps1             ← Windows Docker script
├── DOCKER_README.md           ← Docker documentation
├── problems_and_improvements.md ← Roadmap & known issues
├── core/                      ← Gemini client
├── agents/                    ← Standalone agent scripts
├── swarms/                    ← Orchestration engine & pipelines
├── tools/                     ← Tools (browser automation, store API)
└── outputs/                   ← All agent outputs saved here
```

Enjoy building your AI-automated empire!

---

## 🔧 Development

### Running Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run
python main.py
```

### Running in Development Mode

```bash
# Build development image
docker build -f Dockerfile.dev -t ultraswarm:dev .

# Run with hot reload
docker run -it --rm \
  -e GOOGLE_API_KEY=your_key \
  -v $(pwd):/app \
  ultraswarm:dev
```

