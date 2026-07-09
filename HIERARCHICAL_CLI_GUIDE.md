# 🐝 UltraSwarm Hierarchical CLI — User Guide

## Quick Start

### Option 1: Using the Run Script (Easiest)
```bash
cd /home/jaasiel/Documents/Agents/UltraSwarm-main
./run
```

### Option 2: Using venv Python
```bash
cd /home/jaasiel/Documents/Agents/UltraSwarm-main
.venv/bin/python main.py
```

### Option 3: With Activated venv
```bash
cd /home/jaasiel/Documents/Agents/UltraSwarm-main
source .venv/bin/activate
python main.py
```

---

## Menu Structure

```
MAIN MENU (6 options)
│
├─ [1] MULTI-AGENT SWARMS
│  ├─ Full Launch Swarm (ALL agents)
│  ├─ Product Research (SEO + Product + Store)
│  ├─ Marketing Campaign (Ads + Social + Banners)
│  ├─ SEO Deep Dive (SEO only)
│  └─ [0] Back
│
├─ [2] SUPREME ORCHESTRATOR (APEX)
│  └─ Direct execution (free-form goals)
│
├─ [3] AGENT MANAGEMENT & DISCOVERY
│  ├─ E-Commerce Agents (6 agents)
│  ├─ External Agents (14+ agents)
│  ├─ Worker Agents (all workers)
│  ├─ All Agents (30+ total)
│  ├─ Create New Agent
│  └─ [0] Back
│
├─ [4] SKILL MANAGEMENT
│  ├─ List all skills
│  ├─ Add new skill
│  ├─ Validate skill JSON
│  ├─ Describe skill
│  └─ [0] Back
│
├─ [5] KNOWLEDGE BASE (RAG)
│  ├─ Query knowledge base
│  ├─ Add document
│  ├─ List documents
│  ├─ RAG status
│  ├─ Index statistics
│  ├─ Clear cache
│  ├─ Reindex all
│  └─ [0] Back
│
├─ [6] LEGACY MODE
│  └─ Run agent by name (backward compatible)
│
└─ [0] EXIT

```

---

## Usage Examples

### Example 1: Browse and Run an Agent

```
$ ./run

[Shows Main Menu]
Select [0-6]: 3          ← Choose "Agent Management"

[Shows Agent Management Menu]
Select [0-5]: 1          ← Choose "E-Commerce Agents"

[Shows E-Commerce Agents]
  [1] social - ecommerce
  [2] product - ecommerce
  [3] seo - ecommerce
  [4] store_manager - ecommerce
  [5] banner - ecommerce
  [6] ads - ecommerce

Select agent [0-20]: 3   ← Choose "seo" agent

[Runs SEO agent interactively]
```

### Example 2: Query Knowledge Base

```
$ ./run

Select [0-6]: 5          ← Choose "Knowledge Base"

Select [0-7]: 1          ← Choose "Query knowledge base"

Question: How do I optimize for mobile?

[Returns answer from knowledge base]
```

### Example 3: Run Multi-Agent Swarm

```
$ ./run

Select [0-6]: 1          ← Choose "Swarms"

Select [0-4]: 2          ← Choose "Product Research"

Product/niche to research: fitness trackers

[Swarm executes: SEO + Product + Store agents]
```

### Example 4: Use Supreme Orchestrator

```
$ ./run

Select [0-6]: 2          ← Choose "APEX Orchestrator"

[User] Launch fitness tracker on Amazon

[APEX delegates to appropriate agents and synthesizes results]
```

---

## Features Available

### 🤖 Agent Discovery (30+ Agents)

**E-Commerce (6):**
- seo, product, ads, social, banner, store_manager

**External (14+):**
- web_research, email_drafting, stock_research, customer_support
- social_media, unit_test_generator, competitive_analysis, multi_debate
- ... and more

**Workers (8+):**
- research, strategy, analysis, orchestrator, allocator, outreach
- follow_up, fiverr_manager, gig_creation, account_management
- classifier, memory, thinking, scraping_lead_gen

### 🎯 Skill Management

- **List skills** — See all available capabilities
- **Add skill** — Add new skill from JSON file
- **Validate** — Check skill JSON structure
- **Describe** — View detailed skill information

### 🧠 Knowledge Base (RAG)

- **Query** — Ask questions about indexed documents
- **Add document** — Index new documentation
- **List documents** — See what's indexed
- **Statistics** — View indexing stats
- **Reindex** — Refresh embeddings
- **Cache management** — Clear and optimize cache

### 🔄 Multi-Agent Swarms

1. **Full Launch** — All 6 agents for complete product launch
2. **Product Research** — SEO + Product + Store agents
3. **Marketing Campaign** — Ads + Social + Banner agents
4. **SEO Deep Dive** — Full SEO audit and strategy

### ⚡ Supreme Orchestrator (APEX)

- Free-form goal specification
- Automatic agent delegation
- Multi-level task decomposition
- Result synthesis

---

## Navigation Tips

✅ **Back Navigation**
- Enter `0` at any menu to return to previous menu
- Keep going back to reach Main Menu

✅ **Invalid Input**
- If you enter invalid choice, menu stays open
- Try again

✅ **Agent Execution**
- Most agents run interactively
- Type `quit`, `exit`, or `q` to exit agent
- Agents prompt for task and optional context

✅ **Backward Compatibility**
- Option 6 in main menu allows direct agent run by name
- Old command flags still work: `--agent`, `--swarm`, `--orchestrator`

---

## System Requirements

- Python 3.10+
- Virtual environment activated (.venv)
- Required packages installed (see requirements.txt)

---

## Troubleshooting

### "Module not found" Error
**Solution:** Use the venv python:
```bash
.venv/bin/python main.py
# OR
source .venv/bin/activate
python main.py
```

### Agent Won't Run
**Check:**
1. GOOGLE_API_KEY is set in .env
2. Browser is available (for browser-based agents)
3. Internet connection (for web research)

### Knowledge Base Not Working
**Note:** RAG requires `langchain-community` package. If errors occur:
```bash
.venv/bin/pip install langchain-community
```

---

## Quick Reference

| Task | Menu | Option |
|------|------|--------|
| Run agent | 3 → filter → select | Run agent |
| List agents | 3 → 4 → select | Browse all |
| Launch swarm | 1 → select | Execute |
| Query KB | 5 → 1 | Ask question |
| Add skill | 4 → 2 | Upload JSON |
| Use APEX | 2 | Direct run |

---

## Design Philosophy

This hierarchical CLI was designed with:

✅ **Progressive Disclosure** — Show only relevant options
✅ **Clear Organization** — Related features grouped together
✅ **Intuitive Navigation** — Consistent "Back" buttons
✅ **User Efficiency** — Fewer options per menu = faster decisions
✅ **Backward Compatibility** — Legacy mode preserved
✅ **No Code Duplication** — Reuses existing commands

---

## Examples by Use Case

### I want to discover agents
```
./run → 3 → 4 → Browse all 30+ agents
```

### I want to run a specific agent
```
./run → 3 → 1/2/3 → Select agent → Run
```

### I want to research a topic
```
./run → 1 → 2 (Product Research) → Enter topic
```

### I want to get AI help with something
```
./run → 2 (APEX) → Describe goal
```

### I want to query my knowledge base
```
./run → 5 → 1 → Ask question
```

### I want to manage skills
```
./run → 4 → Select operation
```

---

## Getting Help

Each menu has built-in descriptions. Navigate through menus to explore features.

For detailed documentation, see:
- `QUICK_START_NEW_CLI.md` — Typer CLI usage
- `CLI_README.md` — 100+ command examples
- `IMPLEMENTATION_SUMMARY.md` — Technical details

---

**🐝 Happy swarming!**

