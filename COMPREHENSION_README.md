# UltraSwarm — Comprehension Guide

## Architecture

Multi-agent orchestration. Manager → Helper → Worker tiers. No agent-to-agent direct comms. All via Orchestrator → Allocator.

System Layers:

```
User Goal
    ↓
Orchestrator (APEX) — Supreme coordinator
    ↓ (plans via)
ThinkingAgent — Task decomposition
    ↓ (routes via)
AllocatorAgent — Best-agent matching
    ↓ (dispatches to)
Agent Registry — 100+ agents across domains
```

## Agent Domains

| Domain | Folder | Agents |
|--------|--------|--------|
| E-commerce | agents/ecommerce/ | SEO, Product, Ads, Social, Banner, Store Manager |
| Outreach | agents/outreach/ | Research, Strategy, Message, Analysis, Memory, Followup, Notification |
| Fiverr | agents/fiverr/ | Manager, Gig Creation, Account, Scraping Lead Gen |
| External | agents/external/ | Web Research, Email, Stock, Support, Social, Tests, Debate |
| Helpers | agents/helpers/ | Thinking, Search |
| Browser | agents/browser_operator_agent.py | Browser automation |

## Core Components

### BaseAgent (core/base_agent.py)
- Dynamic skill loading from JSON
- RAG context injection
- Standardized execute_task() interface

### Orchestrator (agents/managers/orchestrator_agent.py)
- run() — Plan → Allocate → Execute → Assemble
- dispatch_to_swarm() — Direct domain routing
- refresh_registry() — Auto-discover new agents

### Allocator (agents/managers/allocator_agent.py)
- assign(subtask, agents) — LLM-based best-fit selection
- Returns agent name with confidence score

## Skills System

Skills = Runtime capabilities. JSON files → LLM prompt injection.

skills/
├── ecommerce/      # Product, SEO, Ads, Social, Banner, Store
├── external/       # Web research, Email, Debate, etc.
└── helpers/        # Task decomposition, Search

tools/skill_loader.py loads skills → injects into system prompt.

## Tools (tools/)

| Tool | Purpose |
|------|---------|
| browser.py | DuckDuckGo search, page fetch, automation |
| browser_actions.py | BrowserActionRunner, BrowserPlannerLoop |
| store_admin.py | Shopify/WooCommerce admin |
| output_manager.py | Save results to disk |
| rag_manager.py | Vector search local docs |
| swarm_memory.py | Session context persistence |

## Data Flow

```
User Input
    ↓
Orchestrator.run(goal)
    ↓
ThinkingAgent → Plan (JSON subtasks)
    ↓
Allocator.assign(task, agents) → Agent Name
    ↓
Agent.execute_task(task, context)
    ↓
Tools invoked (browser, store, search)
    ↓
ExecutionResult returned
    ↓
Context passed to next agent
    ↓
Final synthesis returned to user
```

## External Agents (500-AI-Agents)

- WebResearchAgent — Search + synthesis
- EmailDraftingAgent — Professional emails
- StockResearchAgent — Financial analysis
- CustomerSupportAgent — Ticket responses
- SocialMediaAgent — Multi-platform content
- UnitTestGeneratorAgent — Code tests
- CompetitiveAnalysisAgent — Competitor profiling
- MultiAgentDebateAgent — FOR/AGAINST/judge system

## Fiverr Sub-Swarm

- agents/fiverr/shared/config.py — Environment credentials
- agents/fiverr/shared/state.py — Persistent session state
- Browser-based Fiverr automation

## Configuration

```env
GOOGLE_API_KEY=your_key
BROWSER_HEADLESS=false
BROWSER_USE_AUTO_START=true
FIVERR_USERNAME=your_user
FIVERR_PASSWORD=your_pass
```

## Running

```bash
python main.py                           # Interactive menu
python main.py --agent seo               # Standalone agent
python main.py --swarm product           # Multi-agent pipeline
```

## Output Structure

```
outputs/
├── agent_name/
│   └── timestamp/
│       └── result.json
```

## Agent Contract

Every agent must have:
- name (str)
- role ("manager" | "worker" | "helper" | "domain")
- description (str)
- get_metadata() → dict
- run(input_data) → dict (AgentResult schema)

## Key Patterns

- Stateless between calls — Context passed explicitly
- Skills define capabilities — No code changes for new tasks
- Auto-discover agents — agents/registry.py imports all
- RAG fallback — Keyword search if vector DB fails
- Retry on failure — Configurable attempts per task

## Migration Notes

- base_agent.py uses AgentSkill Pydantic model (not old JSON schema)
- ExecutionResult replaces old AgentResult schema
- make_client() centralizes LLM client setup
- Skills loaded from skills/<domain>/<skill>.json

## Testing

tests/
├── test_base_agent.py
├── test_browser_operator_agent.py
├── test_browser_actions.py
└── ...

## Future Work

- Multi-language support
- A/B testing messages
- Human-in-the-loop approval
- Lead scoring & prediction
- Multi-modal content (images, video)
