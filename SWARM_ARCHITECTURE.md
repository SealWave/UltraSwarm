# Swarm Agent System — Full Architecture & Development Plan

> **Document Purpose:** This is the master development reference for building and scaling the Swarm multi-agent system. Every section is written to give an AI coder (or human developer) enough detail to implement each component without ambiguity. Read this fully before writing any code.

---

## Table of Contents

1. [System Philosophy](#1-system-philosophy)
2. [Full Directory Structure](#2-full-directory-structure)
3. [Skill System — Deep Dive](#3-skill-system--deep-dive)
4. [Base Agent Class](#4-base-agent-class)
5. [Manager Agents](#5-manager-agents)
   - 5.1 [Orchestrator Agent](#51-orchestrator-agent)
   - 5.2 [Allocator Agent](#52-allocator-agent)
6. [Helper Agents](#6-helper-agents)
   - 6.1 [Thinking Agent (Task Maker)](#61-thinking-agent-task-maker)
   - 6.2 [Search Agent](#62-search-agent)
7. [Worker Agents — Generic](#7-worker-agents--generic)
8. [E-Commerce Domain Agents](#8-e-commerce-domain-agents)
9. [CLI — Agent Scaffolding & Management](#9-cli--agent-scaffolding--management)
10. [Inter-Agent Communication Protocol](#10-inter-agent-communication-protocol)
11. [Orchestrator Planning System](#11-orchestrator-planning-system)
12. [Skill-to-Agent Default Mappings](#12-skill-to-agent-default-mappings)
13. [State & Memory Management](#13-state--memory-management)
14. [Error Handling & Fallback Strategy](#14-error-handling--fallback-strategy)
15. [Testing & Verification Plan](#15-testing--verification-plan)
16. [Implementation Phases / Roadmap](#16-implementation-phases--roadmap)
17. [Glossary](#17-glossary)

---

## 1. System Philosophy

### 1.1 What This System Is

This is a **dynamic multi-agent orchestration system** built on top of an LLM backend. It is NOT a hardcoded pipeline. The system is designed to:

- Accept any high-level user goal in natural language.
- Automatically decompose that goal into structured subtasks.
- Dispatch each subtask to the right specialist agent.
- Chain outputs between agents to produce a final result.
- Be extensible: adding a new domain (e.g., legal research, content creation, data analysis) requires only adding new agent files and skill JSON files — no changes to the core orchestration layer.

### 1.2 Agent Classification

All agents fall into exactly one of three tiers:

| Tier | Role | Who uses them | Who they talk to |
|---|---|---|---|
| **Manager** | Plan, route, monitor | User / Top-level | Helpers + Workers |
| **Helper** | Cognitive / utility tasks | Managers | No downstream agents |
| **Worker** | Execute domain actions | Managers via Allocator | Tools & APIs only |

### 1.3 Core Design Rules (must be followed during implementation)

1. **No agent knows about another agent directly.** All routing goes through the Orchestrator → Allocator.
2. **Every agent is stateless between calls.** Context must be passed explicitly.
3. **Skills are the contract.** An agent's capabilities are fully defined by the skills it loads. If it doesn't have a skill, it cannot perform that action.
4. **The Thinking Agent is always the first step.** Even for simple tasks, the Orchestrator calls the ThinkingAgent first to produce a validated plan before any action is taken.
5. **E-Commerce is a domain, not the system.** All e-commerce logic lives in `agents/ecommerce/` and uses a shared base. The core orchestration layer has zero e-commerce-specific code.

---

## 2. Full Directory Structure

```
swarm/
│
├── main.py                        # CLI entry point — all user interaction starts here
├── config.py                      # API keys, model names, environment config
├── requirements.txt
├── README.md
├── ARCHITECTURE.md                # This document (symlink or copy)
│
├── core/                          # Shared base classes — no domain logic here
│   ├── __init__.py
│   ├── base_agent.py              # BaseAgent class (all agents inherit this)
│   ├── message_bus.py             # Handles inter-agent message passing
│   ├── plan_schema.py             # Pydantic models for Plan, Task, SubTask objects
│   └── result_schema.py           # Pydantic models for AgentResult objects
│
├── agents/
│   ├── __init__.py
│   │
│   ├── managers/                  # Tier 1: Planning and routing
│   │   ├── __init__.py
│   │   ├── orchestrator_agent.py  # The boss — receives goals, drives the plan
│   │   └── allocator_agent.py     # The dispatcher — routes subtasks to workers
│   │
│   ├── helpers/                   # Tier 2: Cognitive/utility, no external side effects
│   │   ├── __init__.py
│   │   ├── thinking_agent.py      # Task decomposition — turns goals into JSON plans
│   │   └── search_agent.py        # Web research — searches and summarizes
│   │
│   ├── workers/                   # Tier 3: Domain-specific execution
│   │   ├── __init__.py
│   │   └── [scaffolded workers go here]
│   │
│   └── ecommerce/                 # E-commerce domain (self-contained)
│       ├── __init__.py
│       ├── ads_agent.py
│       ├── banner_agent.py
│       ├── product_agent.py
│       ├── seo_agent.py
│       ├── social_agent.py
│       └── store_manager_agent.py
│
├── skills/                        # JSON skill definitions loaded at runtime
│   ├── browser_search_input_skill.json
│   ├── web_summarize_skill.json
│   ├── google_search_skill.json
│   ├── task_decomposition_skill.json
│   ├── agent_allocation_skill.json
│   ├── plan_review_skill.json
│   ├── ecommerce/
│   │   ├── product_research_skill.json
│   │   ├── seo_writing_skill.json
│   │   ├── ad_copy_skill.json
│   │   ├── banner_design_skill.json
│   │   └── social_copy_skill.json
│   └── [domain]/                  # Future domains add their skills here
│
├── tools/                         # Callable tools (NOT agents — pure functions)
│   ├── __init__.py
│   ├── skill_loader.py            # Reads and caches skill JSON files
│   ├── browser.py                 # google_search(), fetch_page(), click()
│   ├── file_io.py                 # read_file(), write_file(), append_file()
│   ├── summarizer.py              # chunk_and_summarize() for long content
│   └── scaffolder.py             # generate_agent_file() — used by CLI
│
├── swarms/                        # Pre-defined swarm pipelines (optional, kept for backwards compat)
│   └── ecommerce/
│       ├── product_research_swarm.py
│       └── seo_swarm.py
│
├── memory/                        # Persistent memory stores
│   ├── session_store.py           # In-memory KV for a single session
│   └── vector_store.py            # (Future) Embedding-based long-term memory
│
└── tests/
    ├── test_base_agent.py
    ├── test_thinking_agent.py
    ├── test_allocator_agent.py
    ├── test_orchestrator_agent.py
    ├── test_search_agent.py
    ├── test_skill_loader.py
    └── test_cli_scaffold.py
```

---

## 3. Skill System — Deep Dive

### 3.1 What a Skill Is

A **skill** is a JSON file that defines a specific capability. It is injected into an agent's system prompt to give that agent structured knowledge about HOW to do something — the expected inputs, outputs, steps, and constraints of a task.

Think of skills as **training instructions** embedded at runtime. The LLM uses the skill content to correctly structure its behavior and outputs.

### 3.2 Skill JSON Schema

Every skill file must follow this schema:

```json
{
  "skill_id": "google_search_skill",
  "skill_name": "Google Web Search",
  "version": "1.0.0",
  "description": "Enables the agent to perform structured Google searches and return ranked, summarized results.",
  "domain": "research",
  "compatible_agent_tiers": ["helper", "worker"],
  "input_schema": {
    "query": "string — the search query",
    "max_results": "integer — max number of results to return (default: 5)",
    "result_format": "enum: ['summary', 'full', 'urls_only']"
  },
  "output_schema": {
    "results": "array of objects",
    "each_result": {
      "title": "string",
      "url": "string",
      "snippet": "string",
      "relevance_score": "float 0.0-1.0"
    }
  },
  "instructions": [
    "Always validate the query string before calling the search tool.",
    "Filter out results from social media platforms unless the user explicitly requests them.",
    "If zero results are returned, reformulate the query with broader terms and retry once.",
    "Rank results by relevance to the original query, not by position in search engine output."
  ],
  "example_input": {
    "query": "best open source LLM frameworks 2024",
    "max_results": 5,
    "result_format": "summary"
  },
  "example_output": {
    "results": [
      {
        "title": "Top LLM Frameworks in 2024",
        "url": "https://example.com/article",
        "snippet": "LangChain, LlamaIndex, and AutoGen lead...",
        "relevance_score": 0.92
      }
    ]
  },
  "tool_dependencies": ["tools.browser.google_search", "tools.browser.fetch_page"],
  "constraints": [
    "Never make more than 10 search calls per task.",
    "Always cite the source URL in your output."
  ]
}
```

### 3.3 How `skill_loader.py` Works

**File:** `tools/skill_loader.py`

The skill loader is a simple, cached file reader. Here is its complete expected implementation:

```python
# tools/skill_loader.py

import json
import os
from functools import lru_cache
from typing import Union

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")

@lru_cache(maxsize=128)
def load_skill(skill_id: str) -> dict:
    """
    Load a single skill JSON by its skill_id.
    Searches recursively through all subdirectories of skills/.
    Raises FileNotFoundError if the skill does not exist.
    """
    for root, _, files in os.walk(SKILLS_DIR):
        for f in files:
            if f == f"{skill_id}.json":
                with open(os.path.join(root, f), "r") as fp:
                    return json.load(fp)
    raise FileNotFoundError(f"Skill '{skill_id}' not found in {SKILLS_DIR}")


def load_skills(skill_ids: list[str]) -> dict[str, dict]:
    """
    Load multiple skills at once. Returns a dict keyed by skill_id.
    """
    return {sid: load_skill(sid) for sid in skill_ids}


def skill_to_prompt_block(skill: dict) -> str:
    """
    Converts a loaded skill dict into a formatted string block
    that can be injected directly into a system prompt.
    """
    lines = [
        f"## SKILL: {skill['skill_name']} (v{skill['version']})",
        f"**Description:** {skill['description']}",
        "",
        "**Instructions:**",
    ]
    for i, instruction in enumerate(skill.get("instructions", []), 1):
        lines.append(f"  {i}. {instruction}")
    lines.append("")
    lines.append("**Constraints:**")
    for constraint in skill.get("constraints", []):
        lines.append(f"  - {constraint}")
    lines.append("")
    lines.append(f"**Expected Input:** {json.dumps(skill.get('input_schema', {}), indent=2)}")
    lines.append(f"**Expected Output:** {json.dumps(skill.get('output_schema', {}), indent=2)}")
    return "\n".join(lines)


def build_skills_prompt_section(skill_ids: list[str]) -> str:
    """
    Loads all requested skills and returns a combined prompt string
    ready to be appended to any agent's system prompt.
    """
    skills = load_skills(skill_ids)
    blocks = [skill_to_prompt_block(s) for s in skills.values()]
    header = "---\n# LOADED SKILLS\nThe following skills define your available capabilities:\n\n"
    return header + "\n\n---\n\n".join(blocks)
```

### 3.4 How Skills Flow Into an Agent

The flow from JSON file to agent behavior:

```
skills/google_search_skill.json
        │
        ▼
tools/skill_loader.py::load_skill("google_search_skill")
        │   returns dict
        ▼
tools/skill_loader.py::skill_to_prompt_block(skill_dict)
        │   returns formatted string
        ▼
core/base_agent.py::_build_system_prompt()
        │   appends skill block to base system prompt
        ▼
LLM API call with system="{base_prompt}\n\n{skill_blocks}"
        │
        ▼
Agent now "knows" the skill and behaves accordingly
```

### 3.5 Skill Domains

Skills are organized by domain within `skills/`:

| Domain | Folder | Example Skills |
|---|---|---|
| Research | `skills/` root | `google_search_skill`, `web_summarize_skill` |
| E-Commerce | `skills/ecommerce/` | `product_research_skill`, `ad_copy_skill` |
| Planning | `skills/` root | `task_decomposition_skill`, `plan_review_skill` |
| Allocation | `skills/` root | `agent_allocation_skill` |
| Future: Legal | `skills/legal/` | *(to be created)* |
| Future: Finance | `skills/finance/` | *(to be created)* |

---

## 4. Base Agent Class

**File:** `core/base_agent.py`

Every agent in the system — manager, helper, or worker — **must** inherit from `BaseAgent`. This class provides all the boilerplate so agent files focus only on their unique logic.

### 4.1 Class Specification

```python
# core/base_agent.py

import os
import json
from abc import ABC, abstractmethod
from typing import Optional
from tools.skill_loader import build_skills_prompt_section
# from your LLM client library — e.g. openai, anthropic, etc.
# from your_llm_lib import make_client   # <-- implement per your setup


class BaseAgent(ABC):
    """
    Abstract base class for all Swarm agents.

    Subclasses MUST define:
      - name (str)            : Unique agent identifier used for routing
      - role (str)            : One of "manager", "helper", "worker"
      - description (str)     : 1-2 sentence summary of what this agent does.
                                Used by the Allocator to match tasks to agents.
      - default_skills (list) : List of skill_ids this agent always loads
      - base_system_prompt (str): The agent's core persona/instructions

    Subclasses MUST implement:
      - run(input_data: dict) -> dict
    """

    # --- Subclass must define these ---
    name: str = "base_agent"
    role: str = "worker"              # "manager" | "helper" | "worker"
    description: str = ""
    default_skills: list[str] = []    # skill_ids from skills/ directory
    base_system_prompt: str = "You are a helpful AI agent."

    def __init__(self, extra_skills: Optional[list[str]] = None, verbose: bool = False):
        """
        Initialize agent, build LLM client, and construct full system prompt.

        Args:
            extra_skills: Additional skill_ids to load on top of default_skills.
                          Used by Orchestrator to dynamically augment agents.
            verbose: If True, print debug output during runs.
        """
        self.verbose = verbose
        self.client = self._make_client()
        self.conversation_history = []  # Maintains message history for multi-turn

        # Merge default + any dynamic extra skills
        all_skills = list(set(self.default_skills + (extra_skills or [])))
        self.loaded_skills = all_skills

        # Build the complete system prompt
        self.system_prompt = self._build_system_prompt(all_skills)

        if self.verbose:
            print(f"[{self.name}] Initialized with skills: {all_skills}")

    def _make_client(self):
        """
        Initialize the LLM client using config.py settings.
        Override this in subclasses if using a different model/provider.
        """
        import config
        # Example for OpenAI — replace with your actual client setup
        # return openai.OpenAI(api_key=config.OPENAI_API_KEY)
        raise NotImplementedError("Implement _make_client() in core/base_agent.py using your LLM library")

    def _build_system_prompt(self, skill_ids: list[str]) -> str:
        """
        Constructs the full system prompt by combining:
        1. The agent's base persona/instructions
        2. Agent metadata (name, role, description)
        3. All loaded skill blocks

        Returns the final string passed as `system` to every LLM call.
        """
        meta_block = (
            f"# AGENT IDENTITY\n"
            f"- Name: {self.name}\n"
            f"- Role: {self.role}\n"
            f"- Description: {self.description}\n\n"
        )

        skill_block = ""
        if skill_ids:
            skill_block = build_skills_prompt_section(skill_ids)

        return f"{self.base_system_prompt}\n\n{meta_block}{skill_block}"

    def chat(self, user_message: str, reset_history: bool = False) -> str:
        """
        Send a message to the LLM and get a response.
        Maintains conversation_history for multi-turn sessions.

        Args:
            user_message: The prompt to send.
            reset_history: If True, clears history before this call (new task).

        Returns:
            The LLM's response as a plain string.
        """
        if reset_history:
            self.conversation_history = []

        self.conversation_history.append({"role": "user", "content": user_message})

        # --- Replace below with your actual LLM call ---
        # response = self.client.chat.completions.create(
        #     model=config.MODEL_NAME,
        #     messages=[{"role": "system", "content": self.system_prompt}]
        #              + self.conversation_history,
        # )
        # reply = response.choices[0].message.content
        raise NotImplementedError("Implement the LLM call inside chat() in base_agent.py")

        self.conversation_history.append({"role": "assistant", "content": reply})

        if self.verbose:
            print(f"[{self.name}] User: {user_message[:80]}...")
            print(f"[{self.name}] Reply: {reply[:80]}...")

        return reply

    def chat_json(self, user_message: str, reset_history: bool = False) -> dict:
        """
        Same as chat() but expects and parses a JSON response.
        Strips markdown code fences before parsing.
        Raises ValueError if the response is not valid JSON.
        """
        raw = self.chat(user_message, reset_history=reset_history)
        # Strip markdown fences if present
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"[{self.name}] Expected JSON but got: {raw[:200]}") from e

    def get_metadata(self) -> dict:
        """
        Returns agent identity info. Used by the Allocator to match tasks.
        """
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": self.loaded_skills,
        }

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        """
        Main execution method. Subclasses must implement this.

        Args:
            input_data: A dict containing whatever the agent needs to do its job.
                        The Orchestrator always passes a standardized dict — see
                        Section 10 (Inter-Agent Communication Protocol).

        Returns:
            A dict following the AgentResult schema — see core/result_schema.py.
        """
        raise NotImplementedError
```

### 4.2 `AgentResult` Schema

**File:** `core/result_schema.py`

Every agent's `run()` method must return a dict matching this structure:

```python
# core/result_schema.py

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentResult:
    """
    Standardized return format for all agent run() calls.
    The Orchestrator uses this to chain outputs between agents.
    """
    success: bool                    # Did the agent complete its task?
    agent_name: str                  # Which agent produced this result
    task_id: str                     # ID of the subtask this result answers
    output: Any                      # The actual result (string, dict, list, etc.)
    error: Optional[str] = None      # Error message if success=False
    metadata: dict = field(default_factory=dict)  # Token usage, timing, etc.
    context_for_next: Optional[dict] = None  # Data the next agent in chain needs

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "context_for_next": self.context_for_next,
        }
```

---

## 5. Manager Agents

Manager agents sit at **Tier 1**. They never execute domain tasks directly. Their only job is to plan, route, and monitor.

---

### 5.1 Orchestrator Agent

**File:** `agents/managers/orchestrator_agent.py`
**Inherits:** `BaseAgent`

#### Role

The Orchestrator is the **entry point for all user goals**. It:
1. Receives a raw user goal (natural language string).
2. Calls the **ThinkingAgent** to decompose it into a structured plan.
3. Reviews the plan and approves or requests a revision.
4. Calls the **AllocatorAgent** for each subtask to get the right worker.
5. Executes the plan sequentially (or in parallel where safe).
6. Collects results and passes context between steps.
7. Returns the final assembled output to the user.

#### Class Definition

```python
# agents/managers/orchestrator_agent.py

from core.base_agent import BaseAgent
from core.result_schema import AgentResult


class OrchestratorAgent(BaseAgent):

    name = "orchestrator_agent"
    role = "manager"
    description = (
        "Top-level manager agent. Receives a user goal, decomposes it into "
        "a structured plan using the ThinkingAgent, routes each subtask to "
        "the correct worker via the AllocatorAgent, and assembles the final output."
    )
    default_skills = [
        "plan_review_skill",      # Knows how to evaluate a task plan
        "agent_allocation_skill", # Understands agent capabilities
    ]
    base_system_prompt = """
You are the Orchestrator — the master coordinator of a multi-agent AI system.

Your responsibilities:
1. You receive high-level goals from the user.
2. You NEVER execute tasks yourself — you always delegate.
3. You review plans from the ThinkingAgent and ensure they are correct and complete.
4. You track the state of each subtask and ensure outputs from one step feed correctly into the next.
5. You handle failures gracefully — if a worker fails, you decide whether to retry, skip, or abort.
6. You always return a clear, user-facing summary of the final result.

CRITICAL RULES:
- Never skip the planning step (ThinkingAgent).
- Never allow an agent to receive a task without the required context.
- Always validate that the final output is coherent before returning it to the user.
"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Lazy imports to avoid circular dependencies
        from agents.helpers.thinking_agent import ThinkingAgent
        from agents.managers.allocator_agent import AllocatorAgent

        self.thinking_agent = ThinkingAgent(verbose=self.verbose)
        self.allocator_agent = AllocatorAgent(verbose=self.verbose)

        # Registry of all available worker + helper agents.
        # The Allocator needs this to match tasks to agents.
        # IMPORTANT: Add new agents here when you create them.
        self._agent_registry = self._build_agent_registry()

    def _build_agent_registry(self) -> dict:
        """
        Imports and instantiates all available agents.
        Returns a dict keyed by agent name.
        Add new agents here as they are created.
        """
        from agents.helpers.search_agent import SearchAgent
        # from agents.workers.writer_agent import WriterAgent  # example

        registry = {}
        for agent_class in [SearchAgent]:  # expand this list
            instance = agent_class(verbose=self.verbose)
            registry[instance.name] = instance
        return registry

    def run(self, input_data: dict) -> dict:
        """
        Main orchestration loop.

        Args:
            input_data: {
                "goal": str,           # The user's high-level request
                "context": dict,       # Optional: any pre-existing context
                "session_id": str,     # Unique ID for this session
                "max_retries": int,    # Default: 2
            }

        Returns:
            AgentResult dict with assembled final output.
        """
        goal = input_data.get("goal", "")
        context = input_data.get("context", {})
        session_id = input_data.get("session_id", "default")
        max_retries = input_data.get("max_retries", 2)

        if not goal:
            return AgentResult(
                success=False, agent_name=self.name,
                task_id="root", output=None,
                error="No goal provided."
            ).to_dict()

        print(f"\n[Orchestrator] New goal received: {goal}")

        # ── Step 1: Get a plan from ThinkingAgent ──
        plan = self._get_plan(goal, context)
        if not plan:
            return AgentResult(
                success=False, agent_name=self.name,
                task_id="root", output=None,
                error="ThinkingAgent failed to produce a valid plan."
            ).to_dict()

        print(f"[Orchestrator] Plan received: {len(plan['subtasks'])} subtasks")

        # ── Step 2: Execute the plan ──
        results = []
        accumulated_context = dict(context)

        for subtask in plan["subtasks"]:
            task_id = subtask["task_id"]
            print(f"\n[Orchestrator] Executing subtask {task_id}: {subtask['title']}")

            # Get the right agent from the Allocator
            assigned_agent_name = self.allocator_agent.assign(
                subtask=subtask,
                available_agents=[a.get_metadata() for a in self._agent_registry.values()]
            )

            if assigned_agent_name not in self._agent_registry:
                print(f"[Orchestrator] WARNING: No agent found for '{assigned_agent_name}'. Skipping.")
                continue

            agent = self._agent_registry[assigned_agent_name]

            # Build the input for this agent, including accumulated context
            agent_input = {
                "task_id": task_id,
                "instruction": subtask["instruction"],
                "required_output": subtask["required_output"],
                "context": accumulated_context,
                "skills_hint": subtask.get("suggested_skills", []),
            }

            # Execute with retry logic
            result = self._execute_with_retry(agent, agent_input, max_retries)
            results.append(result)

            # Feed this result into context for next agents
            if result["success"] and result.get("context_for_next"):
                accumulated_context.update(result["context_for_next"])

            # If a critical task fails, abort the plan
            if not result["success"] and subtask.get("critical", False):
                print(f"[Orchestrator] Critical task {task_id} failed. Aborting plan.")
                break

        # ── Step 3: Assemble final output ──
        final_output = self._assemble_final_output(goal, plan, results)

        return AgentResult(
            success=True,
            agent_name=self.name,
            task_id="root",
            output=final_output,
            metadata={"subtask_count": len(plan["subtasks"]), "results": results}
        ).to_dict()

    def _get_plan(self, goal: str, context: dict) -> Optional[dict]:
        """Ask ThinkingAgent to produce a plan, with one retry if invalid."""
        plan = self.thinking_agent.run({"goal": goal, "context": context})
        if plan.get("success"):
            return plan.get("output")
        return None

    def _execute_with_retry(self, agent, agent_input: dict, max_retries: int) -> dict:
        """Run an agent with automatic retry on failure."""
        for attempt in range(1, max_retries + 1):
            result = agent.run(agent_input)
            if result["success"]:
                return result
            print(f"[Orchestrator] Attempt {attempt}/{max_retries} failed for {agent.name}: {result.get('error')}")
        return result  # Return the last failed result

    def _assemble_final_output(self, goal: str, plan: dict, results: list) -> str:
        """
        Ask the LLM to synthesize all subtask results into a
        coherent final answer for the user.
        """
        results_summary = "\n".join([
            f"Step {r['task_id']}: {'✓' if r['success'] else '✗'} — {str(r['output'])[:200]}"
            for r in results
        ])
        prompt = (
            f"The user's original goal was: '{goal}'\n\n"
            f"Here are the results from each step:\n{results_summary}\n\n"
            f"Please synthesize these results into a clear, complete answer for the user."
        )
        return self.chat(prompt, reset_history=True)
```

---

### 5.2 Allocator Agent

**File:** `agents/managers/allocator_agent.py`
**Inherits:** `BaseAgent`

#### Role

The Allocator is the **dispatcher**. It takes a single subtask (from the Thinking Agent's plan) and decides which available agent is best suited to handle it. It does NOT call agents — it only makes the routing decision.

#### Matching Logic

The Allocator receives:
- The subtask object (with `title`, `instruction`, `required_skills`, `output_type`)
- A list of all available agent metadata dicts (from `agent.get_metadata()`)

It uses the LLM to score each candidate agent and returns the `name` of the best match.

#### Class Definition

```python
# agents/managers/allocator_agent.py

import json
from core.base_agent import BaseAgent
from core.result_schema import AgentResult


class AllocatorAgent(BaseAgent):

    name = "allocator_agent"
    role = "manager"
    description = (
        "Dispatcher agent. Given a subtask and a list of available agents, "
        "determines which agent is best suited to execute the task based on "
        "agent descriptions, skills, and task requirements."
    )
    default_skills = ["agent_allocation_skill"]
    base_system_prompt = """
You are the Allocator — a specialist in routing tasks to the correct agent.

Given a subtask description and a list of available agents (with their names,
roles, descriptions, and skills), your job is to select the SINGLE best agent
for the task.

You MUST respond with a valid JSON object in this exact format:
{
  "selected_agent": "agent_name_here",
  "confidence": 0.95,
  "reason": "Brief explanation of why this agent was chosen"
}

RULES:
- Only select from the provided agent list. Never invent agent names.
- If no agent is a good match, return the agent with the closest skill match
  and set confidence below 0.5.
- Never assign manager agents to execution tasks.
- Prefer agents whose default_skills explicitly match the task's required_skills.
"""

    def assign(self, subtask: dict, available_agents: list[dict]) -> str:
        """
        Determine which agent should handle the given subtask.

        Args:
            subtask: A single subtask dict from the ThinkingAgent's plan.
            available_agents: List of agent metadata dicts from get_metadata().

        Returns:
            The name (str) of the selected agent.
        """
        prompt = (
            f"SUBTASK:\n{json.dumps(subtask, indent=2)}\n\n"
            f"AVAILABLE AGENTS:\n{json.dumps(available_agents, indent=2)}\n\n"
            f"Select the best agent for this subtask and respond in JSON."
        )

        try:
            decision = self.chat_json(prompt, reset_history=True)
            agent_name = decision.get("selected_agent", "")
            confidence = decision.get("confidence", 0.0)
            reason = decision.get("reason", "")

            print(f"[Allocator] → {agent_name} (confidence: {confidence:.0%}) | {reason}")
            return agent_name
        except (ValueError, KeyError) as e:
            print(f"[Allocator] ERROR parsing decision: {e}")
            # Fallback: return first available worker
            workers = [a for a in available_agents if a["role"] == "worker"]
            return workers[0]["name"] if workers else ""

    def run(self, input_data: dict) -> dict:
        """run() wrapper for BaseAgent compatibility. Use assign() directly."""
        agent_name = self.assign(
            subtask=input_data.get("subtask", {}),
            available_agents=input_data.get("available_agents", [])
        )
        return AgentResult(
            success=bool(agent_name),
            agent_name=self.name,
            task_id=input_data.get("task_id", ""),
            output=agent_name
        ).to_dict()
```

---

## 6. Helper Agents

Helper agents sit at **Tier 2**. They perform cognitive or utility tasks and do NOT call other agents.

---

### 6.1 Thinking Agent (Task Maker)

**File:** `agents/helpers/thinking_agent.py`
**Inherits:** `BaseAgent`

#### Role

The Thinking Agent is the **brain of the planning system**. It receives any high-level user goal and decomposes it into a structured JSON plan of ordered subtasks. Every subtask in the plan specifies exactly what needs to be done, what type of output is needed, what skills are required, and whether it depends on earlier steps.

#### Plan Output Schema

The ThinkingAgent MUST output a JSON object matching this schema (define in `core/plan_schema.py`):

```json
{
  "goal": "Original user goal string",
  "goal_summary": "One sentence restatement of the goal",
  "estimated_steps": 4,
  "subtasks": [
    {
      "task_id": "task_001",
      "title": "Short task title",
      "instruction": "Detailed instruction for the agent that will execute this task.",
      "required_output": "Description of what the output of this task must look like.",
      "output_type": "text | json | list | url | file",
      "suggested_agent_role": "helper | worker",
      "suggested_skills": ["google_search_skill", "web_summarize_skill"],
      "depends_on": [],
      "critical": true,
      "context_keys_needed": [],
      "context_keys_produced": ["search_results"]
    },
    {
      "task_id": "task_002",
      "title": "Summarize findings",
      "instruction": "Given the search results from the previous step, write a 300-word summary.",
      "required_output": "A 300-word prose summary of the research.",
      "output_type": "text",
      "suggested_agent_role": "worker",
      "suggested_skills": ["web_summarize_skill"],
      "depends_on": ["task_001"],
      "critical": false,
      "context_keys_needed": ["search_results"],
      "context_keys_produced": ["summary"]
    }
  ]
}
```

**Key fields explained:**
- `task_id`: Sequential identifier used for dependency resolution.
- `instruction`: The exact prompt-level instruction the assigned agent will receive.
- `required_output`: What the Orchestrator will validate against when the task finishes.
- `suggested_skills`: Hint to the Allocator about what skills the assigned agent needs.
- `depends_on`: List of `task_id`s that must complete before this task can start.
- `critical`: If `true` and this task fails, the entire plan is aborted.
- `context_keys_needed`: Keys that must exist in `accumulated_context` before this runs.
- `context_keys_produced`: Keys this task adds to `accumulated_context` for downstream tasks.

#### Class Definition

```python
# agents/helpers/thinking_agent.py

import json
from core.base_agent import BaseAgent
from core.result_schema import AgentResult


class ThinkingAgent(BaseAgent):

    name = "thinking_agent"
    role = "helper"
    description = (
        "Cognitive decomposition agent. Receives a high-level user goal and "
        "breaks it into a structured, ordered JSON plan of subtasks. "
        "Each subtask specifies its instruction, required output, needed skills, "
        "and dependencies on other tasks."
    )
    default_skills = ["task_decomposition_skill"]
    base_system_prompt = """
You are the Thinking Agent — a world-class AI task planner.

Your ONLY job is to receive a user's goal and produce a detailed, structured
execution plan in JSON format. You do NOT execute tasks. You think.

Your plan must:
1. Break the goal into the minimum number of necessary subtasks (no redundancy).
2. Order subtasks so that dependencies are always satisfied before a task runs.
3. For each subtask, write a clear, self-contained instruction that another AI agent
   can execute without needing to ask questions.
4. Identify what skills each subtask requires.
5. Identify what data each task produces and what data it needs from earlier tasks.

OUTPUT FORMAT: You must ONLY respond with a valid JSON object.
No preamble, no explanation, no markdown fences.
The JSON must strictly follow the plan schema you have been given.

RULES:
- Never create more than 10 subtasks for a single goal.
- Never create circular dependencies.
- If the goal is very simple (e.g., "search for X"), one subtask is fine.
- Every instruction must be specific enough that a blind agent can execute it.
- Context keys must be snake_case strings.
"""

    def run(self, input_data: dict) -> dict:
        """
        Decompose a goal into a structured plan.

        Args:
            input_data: {
                "goal": str,       # The high-level user goal
                "context": dict,   # Optional pre-existing context
            }

        Returns:
            AgentResult with output = the plan dict, or error if parsing fails.
        """
        goal = input_data.get("goal", "")
        context = input_data.get("context", {})

        context_str = f"\n\nAvailable context keys: {list(context.keys())}" if context else ""
        prompt = (
            f"USER GOAL: {goal}{context_str}\n\n"
            f"Produce a complete execution plan in the required JSON format."
        )

        try:
            plan = self.chat_json(prompt, reset_history=True)
            self._validate_plan(plan)
            print(f"[ThinkingAgent] Plan produced: {len(plan['subtasks'])} subtasks")
            return AgentResult(
                success=True,
                agent_name=self.name,
                task_id="planning",
                output=plan
            ).to_dict()
        except (ValueError, KeyError, AssertionError) as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                task_id="planning",
                output=None,
                error=str(e)
            ).to_dict()

    def _validate_plan(self, plan: dict):
        """Basic structural validation of the generated plan."""
        assert "subtasks" in plan, "Plan missing 'subtasks' key"
        assert isinstance(plan["subtasks"], list), "'subtasks' must be a list"
        assert len(plan["subtasks"]) > 0, "Plan has no subtasks"
        for task in plan["subtasks"]:
            assert "task_id" in task, f"Subtask missing task_id: {task}"
            assert "instruction" in task, f"Subtask missing instruction: {task}"
            assert "suggested_skills" in task, f"Subtask missing suggested_skills: {task}"
```

---

### 6.2 Search Agent

**File:** `agents/helpers/search_agent.py`
**Inherits:** `BaseAgent`

#### Role

The Search Agent is a **dedicated web research agent**. It accepts a search query, executes Google searches using `tools/browser.py`, reads the most relevant pages, and returns a structured summary of its findings.

It is the default agent for any task that requires gathering external information.

#### Class Definition

```python
# agents/helpers/search_agent.py

from core.base_agent import BaseAgent
from core.result_schema import AgentResult
from tools.browser import google_search, fetch_page
from tools.summarizer import chunk_and_summarize


class SearchAgent(BaseAgent):

    name = "search_agent"
    role = "helper"
    description = (
        "Web research agent. Given a search query or research topic, performs "
        "Google searches, reads top result pages, and returns a structured "
        "summary of findings. Best for: gathering external information, "
        "fact-checking, competitive research, current events."
    )
    default_skills = [
        "google_search_skill",   # How to construct and execute searches
        "web_summarize_skill",   # How to summarize web page content
    ]
    base_system_prompt = """
You are the Search Agent — an expert web researcher.

Your job is to:
1. Receive a research topic or question.
2. Formulate 1-3 targeted search queries.
3. Execute those searches using the tools available to you.
4. Read the most relevant pages.
5. Synthesize a clear, factual summary of your findings.

OUTPUT FORMAT: Always return a JSON object with this structure:
{
  "summary": "Prose summary of findings (200-400 words)",
  "key_facts": ["fact 1", "fact 2", "..."],
  "sources": [{"title": "...", "url": "..."}],
  "search_queries_used": ["query 1", "query 2"]
}

RULES:
- Cite sources for every factual claim.
- If search results are conflicting, note the conflict in your summary.
- Never fabricate URLs or facts.
- If you cannot find relevant information, say so clearly in the summary.
"""

    def run(self, input_data: dict) -> dict:
        """
        Perform a web search and return summarized findings.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,      # The research question or topic
                "context": dict,         # May contain previous search results
                "max_searches": int,     # Default: 3
                "depth": str,            # "shallow" (snippets only) | "deep" (read pages)
            }

        Returns:
            AgentResult with output = research summary dict.
        """
        instruction = input_data.get("instruction", "")
        task_id = input_data.get("task_id", "search_task")
        max_searches = input_data.get("max_searches", 3)
        depth = input_data.get("depth", "deep")

        # Step 1: Generate search queries
        query_prompt = (
            f"Research task: {instruction}\n\n"
            f"Generate {max_searches} targeted Google search queries for this task. "
            f"Return ONLY a JSON array of query strings."
        )
        try:
            queries = self.chat_json(query_prompt, reset_history=True)
            if not isinstance(queries, list):
                queries = [instruction]  # Fallback to raw instruction
        except ValueError:
            queries = [instruction]

        # Step 2: Execute searches and collect raw content
        raw_content = []
        sources = []
        for query in queries[:max_searches]:
            search_results = google_search(query, max_results=5)
            for result in search_results:
                sources.append({"title": result["title"], "url": result["url"]})
                if depth == "deep":
                    page_text = fetch_page(result["url"])
                    if page_text:
                        raw_content.append(f"SOURCE: {result['url']}\n{page_text[:3000]}")
                else:
                    raw_content.append(result.get("snippet", ""))

        # Step 3: Summarize collected content
        combined = "\n\n---\n\n".join(raw_content)
        if len(combined) > 8000:
            combined = chunk_and_summarize(combined, target_length=6000)

        synthesis_prompt = (
            f"Research task: {instruction}\n\n"
            f"Here is the raw content from web searches:\n\n{combined}\n\n"
            f"Synthesize this into a structured JSON response with keys: "
            f"summary, key_facts, sources, search_queries_used."
        )

        try:
            result_data = self.chat_json(synthesis_prompt, reset_history=False)
            result_data["sources"] = sources  # Ensure sources are populated
            result_data["search_queries_used"] = queries

            return AgentResult(
                success=True,
                agent_name=self.name,
                task_id=task_id,
                output=result_data,
                context_for_next={"search_results": result_data}
            ).to_dict()
        except ValueError as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                task_id=task_id,
                output=None,
                error=str(e)
            ).to_dict()
```

---

## 7. Worker Agents — Generic

Worker agents sit at **Tier 3**. They execute a specific domain task and return a result. They never call other agents.

### 7.1 Worker Agent Template

When scaffolding a new worker agent via CLI, this is the generated template:

```python
# agents/workers/{agent_name}.py
# AUTO-GENERATED BY: python main.py --scaffold-agent {AgentName}
# Edit the values marked with TODO.

from core.base_agent import BaseAgent
from core.result_schema import AgentResult


class {AgentName}(BaseAgent):

    name = "{agent_name}"             # TODO: Unique snake_case identifier
    role = "worker"
    description = (
        "TODO: Write 1-2 sentences describing what this agent does "
        "and what kinds of tasks it should be assigned."
    )
    default_skills = [
        # TODO: Add skill_ids this agent always needs.
        # Example: "google_search_skill", "web_summarize_skill"
    ]
    base_system_prompt = """
TODO: Write this agent's core persona and instructions.
Be specific about its expertise, output format, and any rules it must follow.
"""

    def run(self, input_data: dict) -> dict:
        """
        Execute the assigned task.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,
                "required_output": str,
                "context": dict,
            }
        """
        task_id = input_data.get("task_id", "")
        instruction = input_data.get("instruction", "")
        context = input_data.get("context", {})

        # TODO: Implement task logic here.
        # Use self.chat() for text responses.
        # Use self.chat_json() for structured responses.
        # Use tools from tools/ for external actions.

        try:
            prompt = f"Task: {instruction}\n\nContext: {context}"
            response = self.chat(prompt, reset_history=True)

            return AgentResult(
                success=True,
                agent_name=self.name,
                task_id=task_id,
                output=response,
                context_for_next={}  # TODO: Populate with data for downstream agents
            ).to_dict()
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                task_id=task_id,
                output=None,
                error=str(e)
            ).to_dict()
```

### 7.2 Registering a New Worker

After creating a new worker agent file, you **must** do two things:

1. **Add it to the Orchestrator's `_build_agent_registry()`** in `orchestrator_agent.py`:
   ```python
   from agents.workers.my_new_agent import MyNewAgent
   # Add MyNewAgent to the list in _build_agent_registry()
   ```

2. **Create its skill JSON files** in `skills/` if they don't already exist.

---

## 8. E-Commerce Domain Agents

All e-commerce agents live in `agents/ecommerce/`. They are **self-contained** — the core orchestration layer has no knowledge of them by default. They become available when explicitly loaded into the Orchestrator's registry.

### 8.1 Loading E-Commerce Agents

To enable e-commerce capabilities, pass a flag when launching:
```bash
python main.py --enable-domain ecommerce
```

This loads the e-commerce agents into the registry dynamically. See Section 9 (CLI) for implementation.

### 8.2 E-Commerce Agent Definitions

#### `agents/ecommerce/product_agent.py`
- **Name:** `ecommerce_product_agent`
- **Description:** Researches products, compares prices, identifies features, and writes product descriptions.
- **Default Skills:** `product_research_skill`, `google_search_skill`
- **Input:** `{ product_name, target_audience, competitor_urls }`
- **Output:** `{ description, features_list, price_range, competitor_summary }`

#### `agents/ecommerce/seo_agent.py`
- **Name:** `ecommerce_seo_agent`
- **Description:** Writes SEO-optimized content including meta descriptions, title tags, and keyword-rich product copy.
- **Default Skills:** `seo_writing_skill`, `web_summarize_skill`
- **Input:** `{ product_description, target_keywords, page_type }`
- **Output:** `{ title_tag, meta_description, h1, body_copy, keyword_density_report }`

#### `agents/ecommerce/ads_agent.py`
- **Name:** `ecommerce_ads_agent`
- **Description:** Creates Google Ads and Meta Ads copy including headlines, descriptions, and CTAs.
- **Default Skills:** `ad_copy_skill`
- **Input:** `{ product_name, usp, audience_persona, platform, character_limits }`
- **Output:** `{ headlines: [], descriptions: [], cta: str }`

#### `agents/ecommerce/social_agent.py`
- **Name:** `ecommerce_social_agent`
- **Description:** Writes social media posts for Instagram, TikTok, Twitter/X, and LinkedIn.
- **Default Skills:** `social_copy_skill`
- **Input:** `{ product_name, platform, tone, hashtag_count }`
- **Output:** `{ posts: [{ platform, copy, hashtags }] }`

#### `agents/ecommerce/banner_agent.py`
- **Name:** `ecommerce_banner_agent`
- **Description:** Generates banner ad copy and layout briefs for design teams.
- **Default Skills:** `banner_design_skill`
- **Input:** `{ product, campaign_theme, sizes: ["728x90", "300x250"] }`
- **Output:** `{ banners: [{ size, headline, subtext, cta, visual_direction }] }`

#### `agents/ecommerce/store_manager_agent.py`
- **Name:** `ecommerce_store_manager_agent`
- **Description:** Coordinates all e-commerce agents for full store content generation. Produces a complete product page package.
- **Default Skills:** `product_research_skill`, `seo_writing_skill`, `ad_copy_skill`
- **Note:** This agent acts as a mini-orchestrator within the e-commerce domain. It directly chains product → SEO → ads → social → banner agents internally.

### 8.3 E-Commerce Skill Files

| Skill ID | File | Description |
|---|---|---|
| `product_research_skill` | `skills/ecommerce/product_research_skill.json` | How to research products, extract specs, compare competitors |
| `seo_writing_skill` | `skills/ecommerce/seo_writing_skill.json` | SEO content rules, keyword density, meta tag formats |
| `ad_copy_skill` | `skills/ecommerce/ad_copy_skill.json` | Platform-specific ad formats, character limits, CTA formulas |
| `banner_design_skill` | `skills/ecommerce/banner_design_skill.json` | Banner sizes, layout rules, copy constraints |
| `social_copy_skill` | `skills/ecommerce/social_copy_skill.json` | Platform tone guides, hashtag strategies, post formats |

---

## 9. CLI — Agent Scaffolding & Management

**File:** `main.py`

The CLI is the **primary developer interface**. It handles both end-user interaction (running swarms) and developer tasks (creating agents, managing skills).

### 9.1 Complete CLI Argument Map

```bash
# Run the interactive menu
python main.py

# Run a goal through the full orchestrator
python main.py --goal "Research competitors for product X and write a blog post"

# Enable a specific domain
python main.py --goal "..." --enable-domain ecommerce

# Create a new worker agent scaffold
python main.py --scaffold-agent WriterAgent

# Create a new skill JSON scaffold
python main.py --scaffold-skill web_scraping_skill --domain research

# List all registered agents
python main.py --list-agents

# List all available skills
python main.py --list-skills

# Test a specific agent in isolation
python main.py --test-agent search_agent --input '{"instruction": "find info about LLMs"}'

# Test the ThinkingAgent's decomposition on a goal
python main.py --plan "Research top 5 Python frameworks and compare them"

# Run the full verification suite
python main.py --verify
```

### 9.2 `--scaffold-agent` Implementation

**File:** `tools/scaffolder.py`

When `python main.py --scaffold-agent WriterAgent` is called:

```python
# tools/scaffolder.py

import os
import re

WORKERS_DIR = os.path.join("agents", "workers")
SKILLS_DIR = "skills"


def generate_agent_file(agent_name: str) -> str:
    """
    Generate a boilerplate agent file from the worker template.
    Writes to agents/workers/{snake_name}.py

    Args:
        agent_name: PascalCase name e.g. "WriterAgent"

    Returns:
        Path to the created file.
    """
    # Convert PascalCase to snake_case for filename and name attribute
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', agent_name).lower()
    file_path = os.path.join(WORKERS_DIR, f"{snake_name}.py")

    if os.path.exists(file_path):
        raise FileExistsError(f"Agent file already exists: {file_path}")

    template = f'''# agents/workers/{snake_name}.py
# AUTO-GENERATED: {agent_name}
# Edit the values marked with TODO.

from core.base_agent import BaseAgent
from core.result_schema import AgentResult


class {agent_name}(BaseAgent):

    name = "{snake_name}"
    role = "worker"
    description = (
        "TODO: 1-2 sentences describing what this agent does."
    )
    default_skills = [
        # TODO: Add skill_ids. Example: "google_search_skill"
    ]
    base_system_prompt = """
TODO: Write this agent\'s core persona and task instructions.
"""

    def run(self, input_data: dict) -> dict:
        task_id = input_data.get("task_id", "")
        instruction = input_data.get("instruction", "")
        context = input_data.get("context", {{}})

        try:
            prompt = f"Task: {{instruction}}\\n\\nContext: {{context}}"
            response = self.chat(prompt, reset_history=True)
            return AgentResult(
                success=True, agent_name=self.name,
                task_id=task_id, output=response,
                context_for_next={{}}
            ).to_dict()
        except Exception as e:
            return AgentResult(
                success=False, agent_name=self.name,
                task_id=task_id, output=None, error=str(e)
            ).to_dict()
'''
    os.makedirs(WORKERS_DIR, exist_ok=True)
    with open(file_path, "w") as f:
        f.write(template)

    print(f"[Scaffolder] Created: {file_path}")
    print(f"[Scaffolder] Next steps:")
    print(f"  1. Edit {file_path} — fill in TODO sections")
    print(f"  2. Add any new skill JSON files to skills/")
    print(f"  3. Register the agent in orchestrator_agent.py _build_agent_registry()")
    return file_path


def generate_skill_file(skill_id: str, domain: str = "") -> str:
    """
    Generate a boilerplate skill JSON file.

    Args:
        skill_id: snake_case skill identifier e.g. "web_scraping_skill"
        domain: Optional subdirectory e.g. "ecommerce"
    """
    target_dir = os.path.join(SKILLS_DIR, domain) if domain else SKILLS_DIR
    file_path = os.path.join(target_dir, f"{skill_id}.json")

    if os.path.exists(file_path):
        raise FileExistsError(f"Skill file already exists: {file_path}")

    import json
    template = {
        "skill_id": skill_id,
        "skill_name": "TODO: Human-readable name",
        "version": "1.0.0",
        "description": "TODO: What does this skill enable the agent to do?",
        "domain": domain or "general",
        "compatible_agent_tiers": ["worker"],
        "input_schema": {"TODO_param": "TODO_type — description"},
        "output_schema": {"TODO_output": "TODO_type — description"},
        "instructions": [
            "TODO: Step-by-step instructions for how to use this skill.",
            "TODO: Add as many instructions as needed."
        ],
        "constraints": [
            "TODO: Add any rules or limits for this skill."
        ],
        "tool_dependencies": [],
        "example_input": {},
        "example_output": {}
    }

    os.makedirs(target_dir, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(template, f, indent=2)

    print(f"[Scaffolder] Created: {file_path}")
    return file_path
```

### 9.3 `--list-agents` Implementation

```python
def list_agents():
    """Scan agents/ directory and print all registered agents with metadata."""
    import importlib, inspect
    from core.base_agent import BaseAgent

    for tier in ["managers", "helpers", "workers", "ecommerce"]:
        tier_dir = os.path.join("agents", tier)
        if not os.path.exists(tier_dir):
            continue
        print(f"\n{'='*40}\n  [{tier.upper()}]\n{'='*40}")
        for fname in sorted(os.listdir(tier_dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            module_path = f"agents.{tier}.{fname[:-3]}"
            try:
                mod = importlib.import_module(module_path)
                for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(cls, BaseAgent) and cls is not BaseAgent:
                        print(f"  {cls.name}")
                        print(f"    Role: {cls.role}")
                        print(f"    Desc: {cls.description[:80]}...")
                        print(f"    Skills: {cls.default_skills}")
            except Exception as e:
                print(f"  [ERROR loading {module_path}: {e}]")
```

---

## 10. Inter-Agent Communication Protocol

All agents communicate through standardized input/output dicts. Never pass raw strings between agents — always use the schemas below.

### 10.1 Standard Task Input Dict

```python
# What the Orchestrator sends to every worker/helper agent
task_input = {
    "task_id": "task_001",           # From the ThinkingAgent plan
    "instruction": str,              # The specific instruction for this task
    "required_output": str,          # What the output should look like
    "context": {                     # Accumulated context from all prior tasks
        "search_results": {...},     # Example: search_agent's output
        "product_name": "...",       # Example: passed from session
        # Any context_for_next keys from previous AgentResults
    },
    "skills_hint": [str],            # Suggested skills from ThinkingAgent
    "session_id": str,               # Links to session memory store
    "timeout_seconds": int,          # Default: 60
}
```

### 10.2 Standard AgentResult Dict

```python
# What every agent returns
agent_result = {
    "success": bool,
    "agent_name": str,
    "task_id": str,
    "output": Any,                   # The actual result
    "error": str | None,
    "metadata": {
        "tokens_used": int,
        "duration_seconds": float,
        "model": str,
    },
    "context_for_next": {            # Keys added to accumulated_context
        "summary": "...",
        # etc.
    }
}
```

### 10.3 Message Flow Diagram

```
User Input
    │
    ▼
main.py (CLI)
    │  { goal, session_id }
    ▼
OrchestratorAgent.run()
    │
    ├──► ThinkingAgent.run({ goal })
    │           │
    │           ▼
    │       Returns: Plan JSON with N subtasks
    │
    │   FOR EACH subtask in plan:
    │       │
    │       ├──► AllocatorAgent.assign({ subtask, available_agents })
    │       │           │
    │       │           ▼
    │       │       Returns: agent_name string
    │       │
    │       ├──► registry[agent_name].run({ task_input })
    │       │           │
    │       │           ▼
    │       │       Returns: AgentResult
    │       │
    │       └──► accumulated_context.update(result["context_for_next"])
    │
    ├──► OrchestratorAgent._assemble_final_output(goal, plan, all_results)
    │
    ▼
Final AgentResult → User
```

---

## 11. Orchestrator Planning System

The Orchestrator has a built-in **planning review loop** before execution begins. Here is the detailed flow:

### 11.1 Plan Review Steps

```
1. RECEIVE GOAL
   └─ User provides goal string.

2. GENERATE PLAN (ThinkingAgent)
   └─ ThinkingAgent.run({ goal }) → Plan JSON

3. VALIDATE PLAN STRUCTURE
   └─ Orchestrator._validate_plan_structure(plan)
      - Check all required keys are present
      - Check dependencies are satisfiable (no circular refs)
      - Check no subtask has more than 2 context_keys_produced

4. FEASIBILITY CHECK (LLM-based)
   └─ Orchestrator asks its own LLM:
      "Given this plan and the available agents {agent_list},
       is every subtask assignable? Are there gaps?"
      - If gaps found: request plan revision from ThinkingAgent (max 2 revisions)
      - If plan is feasible: proceed

5. DEPENDENCY RESOLUTION
   └─ Sort subtasks by dependency order (topological sort)
      - Tasks with no depends_on run first
      - Tasks blocked by dependencies wait

6. EXECUTION
   └─ Subtasks execute in resolved order
      - Sequential execution by default
      - Tasks with no shared dependencies can run in parallel (future feature)

7. CONTEXT PROPAGATION
   └─ Each completed task's context_for_next is merged into accumulated_context
      - This accumulated_context is passed to all subsequent tasks

8. FAILURE HANDLING
   └─ If a subtask fails:
      - critical=True: abort the plan, return error summary
      - critical=False: log warning, skip to next task, continue
      - max_retries exceeded: mark as failed, proceed if not critical
```

### 11.2 Plan Validation Code

```python
# In orchestrator_agent.py

def _validate_plan_structure(self, plan: dict) -> bool:
    """
    Validates plan structure before execution.
    Returns True if valid, raises ValueError with details if not.
    """
    required_keys = ["goal", "subtasks"]
    for key in required_keys:
        if key not in plan:
            raise ValueError(f"Plan missing required key: '{key}'")

    task_ids = set()
    for task in plan["subtasks"]:
        tid = task.get("task_id")
        if not tid:
            raise ValueError(f"Subtask missing task_id: {task}")
        if tid in task_ids:
            raise ValueError(f"Duplicate task_id: {tid}")
        task_ids.add(tid)

    # Check all dependencies reference existing task_ids
    for task in plan["subtasks"]:
        for dep in task.get("depends_on", []):
            if dep not in task_ids:
                raise ValueError(f"Task '{task['task_id']}' depends on unknown task '{dep}'")

    return True

def _topological_sort(self, subtasks: list) -> list:
    """
    Sort subtasks so that tasks are always executed after their dependencies.
    Uses Kahn's algorithm (BFS-based topological sort).
    """
    from collections import deque, defaultdict

    in_degree = defaultdict(int)
    graph = defaultdict(list)
    task_map = {t["task_id"]: t for t in subtasks}

    for task in subtasks:
        tid = task["task_id"]
        for dep in task.get("depends_on", []):
            graph[dep].append(tid)
            in_degree[tid] += 1
        if tid not in in_degree:
            in_degree[tid] = 0

    queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
    sorted_tasks = []

    while queue:
        tid = queue.popleft()
        sorted_tasks.append(task_map[tid])
        for neighbor in graph[tid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_tasks) != len(subtasks):
        raise ValueError("Circular dependency detected in plan!")

    return sorted_tasks
```

---

## 12. Skill-to-Agent Default Mappings

This table is the **single source of truth** for which skills each agent loads by default. When adding a new agent, add its row here.

| Agent | File | Role | Default Skills |
|---|---|---|---|
| `orchestrator_agent` | `managers/orchestrator_agent.py` | manager | `plan_review_skill`, `agent_allocation_skill` |
| `allocator_agent` | `managers/allocator_agent.py` | manager | `agent_allocation_skill` |
| `thinking_agent` | `helpers/thinking_agent.py` | helper | `task_decomposition_skill` |
| `search_agent` | `helpers/search_agent.py` | helper | `google_search_skill`, `web_summarize_skill` |
| `ecommerce_product_agent` | `ecommerce/product_agent.py` | worker | `product_research_skill`, `google_search_skill` |
| `ecommerce_seo_agent` | `ecommerce/seo_agent.py` | worker | `seo_writing_skill`, `web_summarize_skill` |
| `ecommerce_ads_agent` | `ecommerce/ads_agent.py` | worker | `ad_copy_skill` |
| `ecommerce_social_agent` | `ecommerce/social_agent.py` | worker | `social_copy_skill` |
| `ecommerce_banner_agent` | `ecommerce/banner_agent.py` | worker | `banner_design_skill` |
| `ecommerce_store_manager_agent` | `ecommerce/store_manager_agent.py` | worker | `product_research_skill`, `seo_writing_skill`, `ad_copy_skill` |

### 12.1 Skill File Checklist

Before adding a skill_id to an agent's `default_skills`, verify:
- [ ] The JSON file exists in `skills/` (or the appropriate subdirectory)
- [ ] The `skill_id` in the JSON matches the string you're using
- [ ] The `tool_dependencies` are implemented in `tools/`
- [ ] The skill has at least 3 `instructions` entries
- [ ] The skill has at least 1 `constraints` entry

---

## 13. State & Memory Management

### 13.1 Session Store

**File:** `memory/session_store.py`

The session store is an **in-memory key-value store** scoped to a single run. It holds the `accumulated_context` and allows agents to look up earlier results.

```python
# memory/session_store.py

class SessionStore:
    """
    Simple in-memory KV store for a single orchestration session.
    Thread-safe via a lock for future async support.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._store = {}

    def set(self, key: str, value) -> None:
        self._store[key] = value

    def get(self, key: str, default=None):
        return self._store.get(key, default)

    def update(self, data: dict) -> None:
        self._store.update(data)

    def all(self) -> dict:
        return dict(self._store)

    def keys(self) -> list:
        return list(self._store.keys())
```

### 13.2 Conversation History Per Agent

Each agent maintains its own `conversation_history` list (defined in `BaseAgent`). This list is:
- **Reset** when `reset_history=True` is passed to `chat()` — at the start of a new task.
- **Preserved** within a multi-turn task for follow-up reasoning.
- **Not shared** between agents (each agent instance is independent).

### 13.3 Future: Vector Memory

In a future iteration, `memory/vector_store.py` will allow agents to store and retrieve relevant past outputs using embedding similarity. This enables the system to "remember" research from previous sessions. This is NOT in scope for Phase 1.

---

## 14. Error Handling & Fallback Strategy

### 14.1 Error Categories

| Error Type | Where It Happens | Handling Strategy |
|---|---|---|
| LLM response not JSON | `BaseAgent.chat_json()` | Strip fences, retry once, raise ValueError |
| Skill file not found | `skill_loader.load_skill()` | Raise `FileNotFoundError` immediately |
| Agent not in registry | `Orchestrator._execute_with_retry()` | Log warning, skip subtask if not critical |
| Search tool failure | `SearchAgent.run()` | Return `success=False` with error, Orchestrator retries |
| Plan has circular deps | `Orchestrator._topological_sort()` | Abort, return error to user |
| Critical subtask fails | Orchestrator execution loop | Abort plan, return partial results |
| Non-critical subtask fails | Orchestrator execution loop | Log, skip, continue with next subtask |
| ThinkingAgent invalid plan | `Orchestrator._get_plan()` | Request revision (max 2 retries), then abort |

### 14.2 Global Exception Handler in main.py

```python
# In main.py — wrap all orchestrator calls

try:
    result = orchestrator.run({"goal": goal, "session_id": session_id})
    if result["success"]:
        print("\n✅ RESULT:\n", result["output"])
    else:
        print("\n❌ FAILED:", result["error"])
except KeyboardInterrupt:
    print("\n[Interrupted by user]")
except Exception as e:
    print(f"\n[FATAL ERROR]: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
```

---

## 15. Testing & Verification Plan

### 15.1 Unit Tests

**File:** `tests/test_skill_loader.py`
- `test_load_skill_found()` — load a known skill, check dict keys
- `test_load_skill_not_found()` — expect FileNotFoundError
- `test_skill_to_prompt_block()` — check output contains skill name and instructions
- `test_build_skills_prompt_section()` — multiple skills, check both appear in output
- `test_load_skill_caching()` — call twice, verify `lru_cache` hit (mock file read)

**File:** `tests/test_base_agent.py`
- `test_agent_metadata()` — verify `get_metadata()` returns correct name, role, skills
- `test_system_prompt_includes_skills()` — check that skill content appears in system_prompt
- `test_chat_json_strips_fences()` — mock LLM response with ```json fences, verify parse

**File:** `tests/test_thinking_agent.py`
- `test_valid_goal_produces_plan()` — pass a goal, check plan has subtasks
- `test_plan_has_required_keys()` — verify each subtask has task_id, instruction, etc.
- `test_simple_goal_few_subtasks()` — simple goal should produce ≤3 subtasks
- `test_invalid_llm_response_returns_error()` — mock bad JSON, check success=False

**File:** `tests/test_allocator_agent.py`
- `test_assign_matching_agent()` — task needing search → assigns search_agent
- `test_assign_no_match_fallback()` — no agents available → returns first worker
- `test_assign_never_picks_manager()` — manager agents never returned

**File:** `tests/test_orchestrator_agent.py`
- `test_full_plan_executes()` — mock all agents, verify all steps run in order
- `test_critical_task_failure_aborts()` — mock critical task failure, verify abort
- `test_non_critical_failure_continues()` — mock non-critical failure, verify continuation
- `test_context_propagation()` — verify context_for_next flows into next task's context

**File:** `tests/test_cli_scaffold.py`
- `test_scaffold_agent_creates_file()` — verify file created at correct path
- `test_scaffold_agent_file_content()` — check class name and name attribute in file
- `test_scaffold_agent_name_conflict()` — verify FileExistsError if agent exists
- `test_scaffold_skill_creates_file()` — verify JSON file created
- `test_scaffold_skill_with_domain()` — verify file in correct subdirectory

### 15.2 Integration Tests (Manual)

```bash
# Test 1: Verify scaffold and agent registration
python main.py --scaffold-agent TestWorker
# Expected: agents/workers/test_worker.py created

python main.py --list-agents
# Expected: test_worker appears under [WORKERS] section

# Test 2: ThinkingAgent plan output
python main.py --plan "Research the top 3 cloud providers and summarize their pricing"
# Expected: JSON plan with 2-4 subtasks, search task first

# Test 3: SearchAgent in isolation
python main.py --test-agent search_agent --input '{"instruction": "find latest news about multi-agent AI systems", "task_id": "test_001"}'
# Expected: JSON with summary, key_facts, sources

# Test 4: Full orchestration (simple goal)
python main.py --goal "What are the top 5 Python web frameworks in 2024?"
# Expected: 2-3 subtask plan, search runs first, final summary returned

# Test 5: E-Commerce domain
python main.py --goal "Write product copy for a wireless keyboard" --enable-domain ecommerce
# Expected: product_agent researches, seo_agent writes copy, result returned

# Test 6: Existing swarms still work (backwards compatibility)
python main.py
# Select: "Product Research Swarm" from the menu
# Expected: Runs without ImportError (ecommerce agents still importable)
```

---

## 16. Implementation Phases / Roadmap

### Phase 1 — Core Infrastructure (Start Here)

Priority: **MUST** complete before any domain work.

| Task | File(s) | Est. Effort |
|---|---|---|
| Implement `config.py` with model/key settings | `config.py` | Small |
| Implement `BaseAgent` with `_make_client()` for your LLM | `core/base_agent.py` | Medium |
| Implement `skill_loader.py` fully (with cache) | `tools/skill_loader.py` | Small |
| Write `plan_schema.py` and `result_schema.py` | `core/` | Small |
| Create `task_decomposition_skill.json` | `skills/` | Small |
| Create `agent_allocation_skill.json` | `skills/` | Small |
| Implement `ThinkingAgent` | `agents/helpers/thinking_agent.py` | Medium |
| Implement `AllocatorAgent` | `agents/managers/allocator_agent.py` | Medium |
| Implement `OrchestratorAgent` | `agents/managers/orchestrator_agent.py` | Large |
| Add `session_store.py` | `memory/session_store.py` | Small |
| Write unit tests for all Phase 1 components | `tests/` | Medium |

### Phase 2 — Helper Agents & CLI

| Task | File(s) | Est. Effort |
|---|---|---|
| Implement `google_search_skill.json` | `skills/` | Small |
| Implement `web_summarize_skill.json` | `skills/` | Small |
| Implement `tools/browser.py` | `tools/browser.py` | Medium |
| Implement `tools/summarizer.py` | `tools/summarizer.py` | Small |
| Implement `SearchAgent` | `agents/helpers/search_agent.py` | Medium |
| Implement `--scaffold-agent` CLI flag | `main.py`, `tools/scaffolder.py` | Medium |
| Implement `--scaffold-skill` CLI flag | `main.py`, `tools/scaffolder.py` | Small |
| Implement `--list-agents` and `--list-skills` | `main.py` | Small |
| Implement `--test-agent` flag | `main.py` | Small |
| Implement `--plan` flag (ThinkingAgent preview) | `main.py` | Small |
| Write Phase 2 unit and integration tests | `tests/` | Medium |

### Phase 3 — E-Commerce Domain Migration

| Task | File(s) | Est. Effort |
|---|---|---|
| Move existing agents to `agents/ecommerce/` | `agents/ecommerce/` | Small |
| Update all imports in existing swarms | `swarms/ecommerce/` | Small |
| Update `main.py` imports | `main.py` | Small |
| Make ecommerce agents subclass `BaseAgent` | All ecommerce agents | Medium |
| Create all ecommerce skill JSON files | `skills/ecommerce/` | Medium |
| Implement `--enable-domain` CLI flag | `main.py` | Small |
| Verify all existing swarms still work | Manual test | Medium |

### Phase 4 — New Domains (Future)

Each new domain follows the same pattern:
1. Create `agents/{domain}/` directory with worker agents.
2. Create `skills/{domain}/` with skill JSON files.
3. Register agents in `_build_agent_registry()` under a domain flag.
4. Test with `--enable-domain {domain}`.

Suggested future domains:
- `content` — Blog writing, social media management, newsletter drafting
- `research` — Academic research, literature review, citation management
- `data` — CSV analysis, charting, data cleaning, report generation
- `legal` — Contract review, clause extraction, compliance checking (note: not legal advice)
- `code` — Code review, refactoring suggestions, documentation generation

---

## 17. Glossary

| Term | Definition |
|---|---|
| **Agent** | An LLM-backed class that receives a task input and returns a structured result. |
| **Skill** | A JSON file defining a specific capability, injected into an agent's system prompt. |
| **Plan** | A JSON object produced by the ThinkingAgent, containing an ordered list of subtasks. |
| **Subtask** | A single unit of work within a plan, assigned to one agent by the Allocator. |
| **Orchestrator** | The top-level manager that drives the full task execution loop. |
| **Allocator** | A routing agent that matches subtasks to the best available worker. |
| **ThinkingAgent** | A cognitive helper that decomposes goals into structured plans. |
| **accumulated_context** | A growing dict passed between agents; each agent adds its outputs to it. |
| **context_for_next** | The subset of an agent's output that should be forwarded to the next agent. |
| **AgentResult** | The standardized dict every agent's `run()` method must return. |
| **Registry** | The dict of instantiated agents available to the Orchestrator. |
| **Domain** | A self-contained collection of agents and skills for a specific field (e.g., ecommerce). |
| **Tier** | Agent classification: manager (1), helper (2), worker (3). |
| **Scaffolding** | Auto-generating a boilerplate agent or skill file via the CLI. |
| **BaseAgent** | The abstract parent class all agents must inherit from. |
| **Session** | One complete run from user goal to final output; has its own `session_id` and `SessionStore`. |

---

*End of Document — Version 1.0*
*Next Review: After Phase 2 completion*
