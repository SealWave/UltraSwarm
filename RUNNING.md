# Running UltraSwarm

This guide explains how to run the UltraSwarm multi-agent system.

## Quick Start

### Option 1: Interactive Menu
```bash
cd /home/jaasiel/Documents/Agents/UltraSwarm-main
.venv/bin/python main.py
```
This opens an interactive menu where you can:
- Run individual agents (SEO, Product, Ads, Social, etc.)
- Run multi-agent swarms (Full Launch, Product Research, Marketing)
- Use the Supreme Orchestrator to delegate to ANY agent

### Option 2: Direct Agent Run
```bash
# Run a specific agent
.venv/bin/python main.py --agent seo
.venv/bin/python main.py --agent product
.venv/bin/python main.py --agent ads
.venv/bin/python main.py --agent social

# Run a swarm
.venv/bin/python main.py --swarm full
.venv/bin/python main.py --swarm product
.venv/bin/python main.py --swarm marketing

# Use the Supreme Orchestrator (recommended for complex tasks)
.venv/bin/python main.py --orchestrator
```

## What's Available

### Individual Agents (E-commerce)
| Agent | Purpose |
|-------|---------|
| SEO | Keyword research, on-page optimization, SEO strategy |
| Product | Product listings, descriptions, market positioning |
| Ads | Paid ad copy and targeting strategy |
| Social | Instagram, TikTok, Pinterest content |
| Banner | Visual banner and creative direction |
| Store | End-to-end ecommerce store orchestration |
| Browser | Live browser control for web scraping |

### Multi-Agent Swarms
| Swarm | Agents Included |
|-------|----------------|
| Full Launch | All 6 e-commerce agents |
| Product Research | SEO + Product + Store |
| Marketing Campaign | Ads + Social + Banners |
| SEO Deep Dive | SEO only |

### Supreme Orchestrator
The **Supreme Orchestrator** (APEX) is the smartest way to use UltraSwarm. It:
- Knows about all 50+ agents in the registry
- Automatically decomposes complex goals
- Delegates tasks to the best-suited agents
- Synthesizes results into coherent answers
- Uses the validation layer for input/output checking

## Configuration

Make sure your `.env` file has:
```env
GOOGLE_API_KEY=your_api_key_here
BROWSER_HEADLESS=false  # Set to false to see browser in action
```

## Input/Output Validation Layer

UltraSwarm now includes a complete validation layer:
- **Schema Registry**: Validates inputs/outputs against schemas
- **Validation Middleware**: Ensures data format consistency
- **Dependency Resolver**: Manages agent dependencies
- **Versioned State**: Thread-safe shared state with conflict detection

This layer is automatically active when using the Supreme Orchestrator or BaseAgent-based agents.

## Troubleshooting

### "LLM Configuration Missing" Error
Run the setup wizard by selecting option 1 (Google Gemini) or 2 (Local LLM) in the interactive menu.

### Slow Agent Loading
The first run may take longer as it loads all agents into memory. Subsequent runs are faster.

### Browser Won't Start
Set `BROWSER_HEADLESS=false` in `.env` and ensure Chrome/Chromium is installed:
```bash
sudo apt-get install chromium
```

## Next Steps

1. Test with the Supreme Orchestrator: `--orchestrator`
2. Try a simple goal like: "Research best-selling products on Amazon"
3. Use specific agents for focused tasks
4. Combine agents in swarms for complex workflows
