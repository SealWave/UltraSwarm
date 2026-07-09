# 🐝 UltraSwarm CLI — Complete User Guide

**Modern command-line interface for managing your multi-agent system**

---

## Quick Start

### Interactive Mode (Default)
```bash
python main.py                  # Original menu
python main.py --cli            # New modern CLI (interactive)
python uswarm.py                # Standalone CLI app
```

### Command Mode
```bash
# List all agents
python uswarm.py agent list

# Run specific agent
python uswarm.py agent run seo

# Query knowledge base
python uswarm.py rag query "How do I optimize for search?"

# Create new agent
python uswarm.py agent create my_agent --type worker

# Run swarm
python uswarm.py swarm run product
```

---

## Commands Reference

### AGENTS — Discover & Execute

#### `agent list`
List all available agents with their domain and status
```bash
python uswarm.py agent list
```
**Output:** Table with 26+ agents (e-commerce, external, managers, helpers, workers)

#### `agent describe <name>`
Show detailed information about an agent
```bash
python uswarm.py agent describe seo
```
**Output:** Agent name, file path, domain, capabilities

#### `agent run <name> [OPTIONS]`
Run an agent interactively or with a specific task
```bash
# Interactive mode
python uswarm.py agent run seo

# Non-interactive (single task)
python uswarm.py agent run seo --task "Analyze google.com" --context '{"url":"google.com"}'

# With context JSON
python uswarm.py agent run product --context '{"topic":"fitness trackers"}'
```
**Options:**
- `--task, -t TEXT` — Single task to execute (skips interactive mode)
- `--context, -c TEXT` — JSON context input for the agent

#### `agent create <name> [OPTIONS]`
Scaffold a new agent from template
```bash
# User selects type in prompt
python uswarm.py agent create my_analyzer

# Specify type directly
python uswarm.py agent create my_analyzer --type worker
python uswarm.py agent create my_helper --type helper
```
**Options:**
- `--type, -t [worker|helper]` — Agent type (interactive choice if not specified)

**Output:**
- Generated agent file in `agents/{type}/`
- Generated skill JSON in `skills/{type}/`

---

### SKILLS — Capability Management

#### `skill list`
List all available skills
```bash
python uswarm.py skill list
```
**Output:** Table with skill names, domains, capabilities, descriptions

#### `skill describe <name>`
Show detailed skill information
```bash
python uswarm.py skill describe seo_agent
```
**Output:** Full skill details including system prompt preview

#### `skill validate <path>`
Validate a skill JSON file
```bash
python uswarm.py skill validate ./my_skill.json
```
**Checks:**
- Valid JSON syntax
- Required fields (name, description, system_prompt)
- Capabilities format
- Domain field

#### `skill add <path> [OPTIONS]`
Add a new skill (validate → copy → test → register)
```bash
python uswarm.py skill add ./my_skill.json
python uswarm.py skill add ./my_skill.json --no-test  # Skip testing
```
**Steps:**
1. Validates skill file
2. Copies to `skills/{domain}/`
3. Tests with mock agent
4. Auto-registers for use

**Output:** Success message with file locations

#### `skill remove <name> [OPTIONS]`
Remove a skill
```bash
python uswarm.py skill remove my_old_skill
python uswarm.py skill remove my_old_skill --confirm  # Skip confirmation
```

---

### RAG — Knowledge Base Control

#### `rag query <question> [OPTIONS]`
Query the knowledge base
```bash
python uswarm.py rag query "How do I optimize for mobile?"
python uswarm.py rag query "What's the best marketing strategy?" --budget 3000
```
**Options:**
- `--budget, -b INTEGER` — Token budget for answer (default: 2000)
- `--verbose, -v` — Show retrieval details

**Output:** Knowledge base answer as formatted panel

#### `rag status`
Show RAG system status
```bash
python uswarm.py rag status
```
**Shows:**
- System status (active/inactive)
- Documents indexed
- Total tokens
- Cache size
- Last updated

#### `rag add <path> [OPTIONS]`
Add a document to knowledge base
```bash
python uswarm.py rag add ./docs/api_guide.md
python uswarm.py rag add ./docs/guide.md --category documentation
```
**Options:**
- `--category, -c TEXT` — Document category (default: general)

**Supported formats:** .md, .txt, .pdf (text), .json

#### `rag list`
List all indexed documents
```bash
python uswarm.py rag list
```
**Output:** Table with document names, categories, sizes, timestamps

#### `rag index-stats`
Show detailed indexing statistics
```bash
python uswarm.py rag index-stats
```
**Shows:**
- Document count and total size
- Embedded chunks count
- Vector dimension
- Indexing method
- Performance metrics
- Query latency
- Cache hit rate

#### `rag clear-cache`
Clear RAG cache
```bash
python uswarm.py rag clear-cache
python uswarm.py rag clear-cache --confirm  # Skip confirmation
```

#### `rag reindex`
Reindex all knowledge documents
```bash
python uswarm.py rag reindex
python uswarm.py rag reindex --confirm  # Skip confirmation
```
**Warning:** Takes several minutes, refreshes all embeddings

---

### ORCHESTRATION — Multi-Agent Control

#### `swarm run <type>`
Run a swarm (multi-agent pipeline)
```bash
python uswarm.py swarm run product       # Product research swarm
python uswarm.py swarm run marketing     # Marketing campaign swarm
python uswarm.py swarm run seo           # SEO audit swarm
python uswarm.py swarm run full          # Full launch swarm (all agents)
```

**Swarm Types:**
- **product** — SEO + Product Research + Store Management
- **marketing** — Ads + Social Media + Banners
- **seo** — Full SEO audit with keyword analysis
- **full** — Complete product launch pipeline

**Interactive prompts:** Each swarm asks for relevant inputs

#### `swarm apex [OPTIONS]`
Run the Supreme Orchestrator (APEX)
```bash
# Interactive mode
python uswarm.py swarm apex

# Single goal (non-interactive)
python uswarm.py swarm apex --goal "Research fitness tracker market and create launch plan"
```
**Options:**
- `--goal, -g TEXT` — Single goal to execute (optional)

**Features:**
- Loads all agents from registry
- Breaks down goals into subtasks
- Delegates to appropriate agents
- Shows registry size and completed subtasks

---

## Usage Patterns

### Pattern 1: Discovery
```bash
# See what you have
python uswarm.py agent list          # 26+ agents
python uswarm.py skill list          # Available skills
python uswarm.py agent describe seo  # Agent details
```

### Pattern 2: Quick Task Execution
```bash
# Run single task without interactive mode
python uswarm.py agent run seo --task "Analyze google.com"
```

### Pattern 3: Knowledge Management
```bash
# Add docs to knowledge base
python uswarm.py skill add ./new_skill.json

# Query knowledge
python uswarm.py rag query "How do I use this?"

# Monitor indexing
python uswarm.py rag status
```

### Pattern 4: Agent Development
```bash
# Create new agent
python uswarm.py agent create my_analyzer --type worker

# Edit generated files in agents/workers/ and skills/workers/
# Then test
python uswarm.py agent run my_analyzer --task "test task"
```

### Pattern 5: Complex Operations
```bash
# Run multi-agent swarm
python uswarm.py swarm run product

# Or use orchestrator for free-form goals
python uswarm.py swarm apex --goal "Your complex goal here"
```

---

## Integration with Existing Code

### Option 1: Use New CLI (Recommended)
```bash
python uswarm.py agent run seo
```

### Option 2: Keep Old Interactive Menu
```bash
python main.py                    # Original menu still works
python main.py --agent seo        # Existing flags still work
python main.py --swarm product    # Existing flags still work
```

### Option 3: Mixed Mode
```bash
python main.py --cli              # New CLI with old entry point
```

---

## Agent Scaffolding Template

When you create an agent with `agent create`, you get:

### Worker Agent Template
```python
class MyAgentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            skill_name="my_agent",
            domain="workers"
        )
    
    def execute_task(self, task: str, context: dict = None):
        return super().execute_task(task, context)
```

### Helper Agent Template
```python
class MyAgentAgent(BaseAgent):
    def think(self, prompt: str, context: dict = None) -> str:
        result = self.execute_task(prompt, context)
        return result.message if result.status == "success" else ""
```

### Generated Skill File
```json
{
  "name": "my_agent",
  "description": "My Agent — Specialized agent",
  "domain": "workers",
  "system_prompt": "You are the my_agent agent...",
  "capabilities": ["task_execution", "analysis"],
  "models": ["gemini-2.5-flash-preview-05-20"],
  "temperature": 0.7
}
```

---

## Feature Matrix

| Feature | Command | Status |
|---------|---------|--------|
| List agents | `agent list` | ✅ Implemented |
| Run agent | `agent run <name>` | ✅ Implemented |
| Create agent | `agent create <name>` | ✅ Implemented |
| Describe agent | `agent describe <name>` | ✅ Implemented |
| List skills | `skill list` | ✅ Implemented |
| Add skill | `skill add <path>` | ✅ Implemented |
| Validate skill | `skill validate <path>` | ✅ Implemented |
| Query knowledge base | `rag query <q>` | ✅ Implemented |
| RAG status | `rag status` | ✅ Implemented |
| Add document | `rag add <path>` | ✅ Implemented |
| Run swarms | `swarm run <type>` | ✅ Implemented |
| Run orchestrator | `swarm apex` | ✅ Implemented |
| Interactive menu | (no args) | ✅ Implemented |
| Tab completion | (shell built-in) | ✅ Supported |

---

## Architecture

```
main.py (entry point, backward compatible)
  └─ --cli flag → cli/main.py
  └─ old flags  → existing code

uswarm.py (standalone CLI entry point)
  └─ cli/main.py (Typer app)
     ├─ cli/commands/agent.py
     ├─ cli/commands/skill.py
     ├─ cli/commands/rag.py
     ├─ cli/commands/orchestrator.py
     └─ cli/utils.py (shared functions)
```

---

## Troubleshooting

### CLI doesn't start
```bash
# Ensure Typer is installed
pip install typer shellingham

# Or use uv
uv pip install typer shellingham
```

### Import errors
```bash
# Make sure you're in the project directory
cd /path/to/UltraSwarm-main

# Use venv Python
.venv/bin/python uswarm.py
```

### Agent list is empty
```bash
# Check agents/ directory exists
ls agents/

# Check for _agent.py files
find agents -name "*_agent.py" | head
```

### RAG commands fail
```bash
# Install langchain dependencies
uv pip install langchain langchain-community langchain-google-genai
```

---

## Next Steps

- ✅ Agent discovery and execution
- ✅ Agent scaffolding with templates
- ✅ Skill management
- ✅ Knowledge base integration
- ✅ Full swarm control
- 🔄 Shell completion installation
- 🔄 Package distribution (pip/uv)

---

## Support

For issues or feature requests:
1. Check the agent/skill files for errors
2. Run with `--help` for command syntax
3. Review generated agent templates
4. Check knowledge base status

Happy swarming! 🐝
