# 🐝 UltraSwarm CLI — Commands Quick Reference

## 🚀 Start Here

```bash
# Interactive menu (best for exploring)
./uswarm

# Or use full Python path
.venv/bin/python uswarm.py
```

---

## 🤖 Agent Commands

### List All Agents
```bash
./uswarm agent list
```
Shows all 30+ available agents (e-commerce, external, workers, managers)

### Get Agent Info
```bash
./uswarm agent describe seo
./uswarm agent describe product
./uswarm agent describe ads
```

### Run an Agent
```bash
# Interactive mode
./uswarm agent run seo

# With specific task
./uswarm agent run seo --task "Analyze google.com"

# With context (JSON)
./uswarm agent run product --context '{"topic":"fitness trackers"}'
```

### Create New Agent
```bash
# Interactive (prompts for type)
./uswarm agent create my_analyzer

# Specify type
./uswarm agent create my_analyzer --type worker
./uswarm agent create my_helper --type helper
```

---

## 🎯 Skill Commands

### List All Skills
```bash
./uswarm skill list
```

### Get Skill Details
```bash
./uswarm skill describe seo_agent
```

### Add New Skill
```bash
./uswarm skill add ./my_skill.json
```

### Validate Skill JSON
```bash
./uswarm skill validate ./my_skill.json
```

### Remove Skill
```bash
./uswarm skill remove my_skill --confirm
```

---

## 🧠 Knowledge Base (RAG) Commands

### Query Knowledge Base
```bash
./uswarm rag query "How do I optimize for search?"
./uswarm rag query "What's the best strategy for Amazon?"
```

### Add Document
```bash
./uswarm rag add ./docs/api_guide.md
./uswarm rag add ./knowledge/seo_guide.txt
```

### Check Status
```bash
./uswarm rag status
```

### List Documents
```bash
./uswarm rag list
```

### Get Detailed Stats
```bash
./uswarm rag index-stats
```

### Clear Cache
```bash
./uswarm rag clear-cache
```

### Reindex All
```bash
./uswarm rag reindex --confirm
```

---

## 🔄 Swarm Commands

### Run Pre-Built Swarms
```bash
# Product research (SEO + Product + Store)
./uswarm swarm run product

# Marketing campaign (Ads + Social + Banner)
./uswarm swarm run marketing

# SEO deep dive (SEO only)
./uswarm swarm run seo

# Full launch (ALL agents)
./uswarm swarm run full
```

### Use Supreme Orchestrator (APEX)
```bash
# Interactive
./uswarm swarm apex

# With specific goal
./uswarm swarm apex --goal "Launch fitness tracker on Amazon"
./uswarm swarm apex --goal "Research eco-friendly water bottles in US market"
```

---

## 📚 Help & Documentation

### Get Help
```bash
./uswarm --help                      # Main help
./uswarm agent --help                # Agent help
./uswarm skill --help                # Skill help
./uswarm rag --help                  # RAG help
./uswarm swarm --help                # Swarm help
./uswarm agent run --help            # Specific command help
```

### Read Documentation
```bash
cat QUICK_START_NEW_CLI.md           # User guide
cat CLI_README.md                    # 100+ examples
cat IMPLEMENTATION_COMPLETION.md     # Technical details
```

---

## 🎮 Common Workflows

### Workflow 1: Explore Available Agents
```bash
./uswarm
# Choose option 1: List agents
```

### Workflow 2: Run Quick Agent Task
```bash
./uswarm agent run seo --task "Analyze google.com SEO"
```

### Workflow 3: Create & Test Custom Agent
```bash
# Create
./uswarm agent create my_analyzer --type worker

# Edit the generated files:
# - agents/workers/my_analyzer_agent.py
# - skills/workers/my_analyzer.json

# Test
./uswarm agent run my_analyzer --task "Test task"
```

### Workflow 4: Research with Knowledge Base
```bash
# Add documentation
./uswarm rag add ./docs/api_guide.md

# Query
./uswarm rag query "How does this work?"
```

### Workflow 5: Full Product Launch
```bash
./uswarm swarm run full
```

### Workflow 6: Complex Goal with APEX
```bash
./uswarm swarm apex --goal "Launch eco-friendly water bottles in US market targeting fitness enthusiasts"
```

---

## 🔗 Backward Compatibility (Old Way Still Works)

```bash
# These OLD commands still work:
python main.py                       # Old interactive menu
python main.py --agent seo          # Old agent mode
python main.py --swarm product      # Old swarm mode
python main.py --orchestrator       # Old orchestrator

# But these NEW commands are recommended:
./uswarm                             # New interactive menu
./uswarm agent run seo               # New agent mode
./uswarm swarm run product           # New swarm mode
./uswarm swarm apex                  # New orchestrator
```

---

## 💡 Tips & Tricks

### Use Bash Wrapper (Easier)
```bash
# Better than:
.venv/bin/python uswarm.py agent list

# Just do:
./uswarm agent list
```

### Chain Commands
```bash
# List agents first
./uswarm agent list

# Then run one
./uswarm agent run seo --task "Your task"
```

### Save Output
```bash
# Redirect to file
./uswarm agent list > agents.txt

# Pipe to grep
./uswarm agent list | grep ecommerce
```

### Interactive for Complex Tasks
```bash
# Use interactive when unsure about options
./uswarm swarm apex
# Menu prompts you through the process
```

---

## 🎯 Available Agents (30 Total)

**E-Commerce:**
- seo, product, ads, social, banner, store_manager, browser_operator

**External:**
- web_research, email_drafting, stock_research, customer_support, social_media
- unit_test_generator, competitive_analysis, multi_debate

**Specialized:**
- research, strategy, analysis, orchestrator, allocator, outreach
- follow_up, fiverr_manager, gig_creation, account_management
- classifier, memory, thinking, scraping_lead_gen

---

## 🔍 Troubleshooting

### Command Not Found
```bash
# Make sure you're in the right directory
cd /path/to/UltraSwarm-main

# Use the wrapper (includes venv activation)
./uswarm agent list
```

### Permission Denied
```bash
# Make scripts executable
chmod +x uswarm
chmod +x uswarm.py
```

### Python Not Found
```bash
# Use venv explicitly
.venv/bin/python uswarm.py agent list

# Or activate venv first
source .venv/bin/activate
python uswarm.py agent list
```

### Agent Won't Run
```bash
# Check .env has GOOGLE_API_KEY
cat .env

# If missing, add it:
echo "GOOGLE_API_KEY=your_key_here" >> .env
```

---

## 📊 System Info

| Item | Value |
|------|-------|
| Entry Point | `./uswarm` or `python uswarm.py` |
| CLI Framework | Typer |
| Agents | 30+ available |
| Skills | 8+ available |
| Commands | 40+ available |
| Swarms | 4 pre-built |
| Startup Time | <500ms |

---

## 🐝 That's It!

You're ready to use UltraSwarm. Start with:

```bash
./uswarm
```

Then explore the interactive menu or use specific commands. Happy swarming! 🚀
