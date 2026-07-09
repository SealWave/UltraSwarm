"""
agents/managers/orchestrator_agent.py
======================================
ULTRASWARM SUPREME ORCHESTRATOR
================================
The singular command centre for the entire UltraSwarm multi-agent system.

ROLE: You are the supreme controlling intelligence of UltraSwarm — a fully
automated AI agent operating system. Every agent in this codebase reports to
you. You receive goals, decompose them, delegate to specialists, synthesize
results, and return polished outputs. You do NOT perform tasks yourself.

ARCHITECTURE this agent operates within:
  ┌─────────────────────────────────────────┐
  │           SUPREME ORCHESTRATOR          │  ← You are here
  │   agents/managers/orchestrator_agent    │
  └──────────────┬──────────────────────────┘
                 │ Plans via
                 ▼
  ┌──────────────────────┐
  │    ThinkingAgent     │  Decomposes goals into subtask plans
  └──────────┬───────────┘
             │ Routes via
             ▼
  ┌──────────────────────┐
  │    AllocatorAgent    │  Selects best agent for each subtask
  └──────────┬───────────┘
             │ Dispatches to
             ▼
  ┌───────────────────────────────────────────────────────────────┐
  │                    UNIVERSAL AGENT REGISTRY                   │
  │  helpers/    external/    outreach/    ecommerce/    fiverr/  │
  │  browser_operator_agent.py                                    │
  │  (Auto-discovered — see agents/registry.py)                   │
  └───────────────────────────────────────────────────────────────┘

WORKFLOW (what happens when you send a goal):
  1. Auto-refresh registry (new agents discovered automatically).
  2. ThinkingAgent creates a JSON subtask plan.
  3. AllocatorAgent matches each subtask to the best registered agent.
  4. Each agent executes and returns context for the next step.
  5. Final answer is synthesised from all outputs.

FAST PATH — dispatch_to_swarm():
  When a goal maps to a full domain (outreach campaign, ecommerce tasks,
  Fiverr gig management), the Orchestrator can skip decomposition and route
  directly to the domain coordinator agent.
"""

import json
import logging
import os
from typing import Optional

from core.base_agent import BaseAgent
from core.result_schema import AgentResult

logger = logging.getLogger("SupremeOrchestrator")


SUPREME_SYSTEM_PROMPT = """
You are APEX — the Supreme Orchestrator of UltraSwarm.

UltraSwarm is an autonomous multi-agent operating system with the following specialist teams:

OUTREACH TEAM (agents/outreach/)
  • outreach_orchestrator     — runs end-to-end outreach campaigns
  • outreach_research_agent   — profiles prospects using web + competitive analysis
  • outreach_strategy_agent   — designs platform strategy and campaign goals
  • outreach_message_agent    — writes personalised multi-platform messages
  • outreach_analysis_agent   — classifies incoming replies (emotion, intent, urgency)
  • outreach_memory_agent     — persists conversation history and context
  • outreach_followup_agent   — manages multi-day drip sequences
  • notification_watcher      — monitors inboxes for replies (webhook daemon)

ECOMMERCE TEAM (agents/ecommerce/)
  • seo_agent                 — keyword research, on-page optimisation, SEO strategy
  • social_agent              — platform-native content for Instagram, TikTok, Pinterest
  • product_agent             — product listings, descriptions, market positioning
  • ads_agent                 — paid ad copy and targeting strategy
  • store_manager_agent       — end-to-end ecommerce store orchestration
  • banner_agent              — visual banner and creative direction

FIVERR TEAM (agents/fiverr/)
  • fiverr_manager_agent      — coordinates Fiverr gig lifecycle
  • gig_creation_agent        — writes optimised Fiverr gig listings
  • account_management_agent  — manages account health and optimisation
  • scraping_lead_gen_agent   — prospect lead generation via scraping

EXTERNAL / GENERAL PURPOSE (agents/external/)
  • web_research_agent        — web search + structured research reports
  • email_drafting_agent      — professional email composition
  • social_media_agent        — Twitter/X, LinkedIn, Instagram content
  • competitive_analysis_agent— competitor profiling and market gaps
  • customer_support_agent    — support ticket responses and escalation
  • stock_research_agent      — financial analysis and investment thesis
  • unit_test_generator_agent — automated unit test generation
  • multi_agent_debate_agent  — structured two-sided debate with scoring

HELPERS (agents/helpers/)
  • thinking_agent            — task decomposition and planning (you use this internally)
  • search_agent              — web search and summarisation

BROWSER (agents/browser_operator_agent.py)
  • browser_operator_agent    — live browser control for web scraping, form filling, page navigation

YOUR RULES:
1. You NEVER execute tasks yourself. You delegate everything.
2. Always start with ThinkingAgent to decompose complex goals.
3. Use dispatch_to_swarm() when a goal clearly belongs to one domain
   (e.g. "run outreach for Alice Johnson" → dispatch to 'outreach').
4. Pass full context from each step to the next — never let agents work blind.
5. When a critical task fails, decide: retry / skip / abort. Document the choice.
6. Return a clear, complete, user-facing summary — never raw JSON dumps.
7. You are aware of ALL agents because the registry auto-discovers new ones.
   If a new agent appears that you don't recognise, treat it as a 'worker' role
   and let AllocatorAgent decide if it fits a subtask.
"""


class OrchestratorAgent(BaseAgent):

    name = "supreme_orchestrator"
    role = "manager"
    description = (
        "APEX — Supreme Orchestrator of UltraSwarm. Controls all agents across "
        "outreach, ecommerce, fiverr, external, helpers, and browser teams. "
        "Decomposes goals via ThinkingAgent, routes subtasks via AllocatorAgent "
        "using an auto-updating universal registry, and assembles final outputs. "
        "Use dispatch_to_swarm() for domain-specific campaigns."
    )
    default_skills = [
        "plan_review_skill",
        "agent_allocation_skill",
    ]
    base_system_prompt = SUPREME_SYSTEM_PROMPT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        from agents.helpers.thinking_agent import ThinkingAgent
        from agents.managers.allocator_agent import AllocatorAgent

        self.thinking_agent = ThinkingAgent(verbose=self.verbose)
        self.allocator_agent = AllocatorAgent(verbose=self.verbose)

        # Load universal registry (auto-discovers all agents)
        self._agent_registry = self._build_agent_registry()

    # ──────────────────────────────────────────────────────────────────────────
    # REGISTRY
    # ──────────────────────────────────────────────────────────────────────────

    def _build_agent_registry(self) -> dict:
        """
        Uses agents/registry.py to load every agent in the codebase.
        Manager-role agents are excluded from the worker pool (they don't
        execute tasks), except outreach_orchestrator which IS a valid dispatch
        target.
        """
        try:
            from agents.registry import build_registry
            registry = build_registry(verbose=getattr(self, "verbose", False))
            return {
                name: agent
                for name, agent in registry.items()
                if getattr(agent, "role", "") != "manager"
                or name == "outreach_orchestrator"
            }
        except Exception as e:
            logger.error(f"Universal registry failed, using minimal fallback: {e}")
            return self._build_minimal_registry()

    def _build_minimal_registry(self) -> dict:
        """Minimal fallback — mirrors the old behaviour."""
        from agents.helpers.search_agent import SearchAgent
        from agents.external import ALL_EXTERNAL_AGENTS
        agent_classes = [SearchAgent] + ALL_EXTERNAL_AGENTS
        registry = {}
        for cls in agent_classes:
            try:
                instance = cls(verbose=getattr(self, "verbose", False))
                registry[instance.name] = instance
            except Exception as e:
                logger.warning(f"Could not load {cls.__name__}: {e}")
        return registry

    def refresh_registry(self) -> int:
        """
        Hot-reloads the agent registry to pick up any newly added agents.
        Called automatically on each run() invocation.
        Returns the number of agents now in the registry.
        """
        self._agent_registry = self._build_agent_registry()
        count = len(self._agent_registry)
        logger.info(f"[APEX] Registry refreshed — {count} agents loaded.")
        return count

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, input_data: dict) -> dict:
        """
        Main orchestration loop.

        Args:
            input_data: {
                "goal": str,              # The user's high-level request
                "context": dict,          # Optional pre-existing context
                "session_id": str,        # Unique session identifier
                "max_retries": int,       # Default: 2
                "swarm_domain": str,      # Optional: "outreach"|"ecommerce"|"fiverr"
                                          #   skips decomposition, goes direct to domain
                "refresh_registry": bool, # Default: True — auto-discover new agents
            }
        """
        goal = input_data.get("goal", "")
        context = input_data.get("context", {})
        session_id = input_data.get("session_id", "default")
        max_retries = input_data.get("max_retries", 2)
        swarm_domain = input_data.get("swarm_domain", "")
        should_refresh = input_data.get("refresh_registry", True)

        if not goal:
            return AgentResult(
                success=False, agent_name=self.name,
                task_id="root", output=None,
                error="No goal provided."
            ).to_dict()

        # Auto-refresh registry every run to catch new agents
        if should_refresh:
            self.refresh_registry()

        print(f"\n[APEX] ═══════════════════════════════════════════════")
        print(f"[APEX] Goal: {goal}")
        print(f"[APEX] Agents available: {len(self._agent_registry)}")
        print(f"[APEX] ═══════════════════════════════════════════════")

        # Fast path: full domain swarm dispatch
        if swarm_domain:
            return self.dispatch_to_swarm(swarm_domain, goal, context)

        # Standard path: plan → allocate → execute → assemble
        plan = self._get_plan(goal, context)
        if not plan:
            return AgentResult(
                success=False, agent_name=self.name,
                task_id="root", output=None,
                error="ThinkingAgent failed to produce a valid plan."
            ).to_dict()

        print(f"[APEX] Plan produced: {len(plan['subtasks'])} subtasks")

        results = []
        accumulated_context = dict(context)

        for subtask in plan["subtasks"]:
            task_id = subtask["task_id"]
            print(f"\n[APEX] ── Subtask {task_id}: {subtask.get('title', subtask.get('instruction', '')[:60])}")

            assigned = self.allocator_agent.assign(
                subtask=subtask,
                available_agents=[
                    self._get_agent_metadata(a)
                    for a in self._agent_registry.values()
                ]
            )

            if assigned not in self._agent_registry:
                print(f"[APEX] WARNING: No agent '{assigned}' found. Skipping.")
                continue

            agent = self._agent_registry[assigned]
            agent_input = {
                "task_id": task_id,
                "instruction": subtask["instruction"],
                "required_output": subtask.get("required_output", ""),
                "context": accumulated_context,
                "skills_hint": subtask.get("suggested_skills", []),
            }

            result = self._execute_with_retry(agent, agent_input, max_retries)
            results.append(result)

            if result.get("success") and result.get("context_for_next"):
                accumulated_context.update(result["context_for_next"])

            if not result.get("success") and subtask.get("critical", False):
                print(f"[APEX] Critical task {task_id} failed. Aborting plan.")
                break

        final_output = self._assemble_final_output(goal, plan, results)

        return AgentResult(
            success=True,
            agent_name=self.name,
            task_id="root",
            output=final_output,
            metadata={
                "session_id": session_id,
                "subtask_count": len(plan["subtasks"]),
                "results": results,
                "registry_size": len(self._agent_registry),
            }
        ).to_dict()

    def dispatch_to_swarm(self, domain: str, goal: str, context: dict = None) -> dict:
        """
        Routes a goal directly to the top-level coordinator of a named domain swarm.
        Skips ThinkingAgent decomposition — best for well-scoped domain tasks.

        Args:
            domain: "outreach" | "ecommerce" | "fiverr"
            goal:   Task description for the domain coordinator.
            context: Optional context dict.
        """
        print(f"\n[APEX] Dispatching to domain swarm: '{domain}'")
        try:
            from agents.registry import get_domain_agent
            domain_agent = get_domain_agent(domain)
            return domain_agent.run({
                "goal": goal,
                "context": context or {},
                "task_id": f"swarm_{domain}",
                "instruction": goal,
            })
        except Exception as e:
            logger.error(f"Swarm dispatch to '{domain}' failed: {e}")
            return AgentResult(
                success=False, agent_name=self.name,
                task_id=f"swarm_{domain}", output=None,
                error=str(e)
            ).to_dict()

    def list_available_agents(self) -> None:
        """Pretty-print the full registry to the console."""
        from agents.registry import list_agents
        list_agents(self._agent_registry)

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNALS
    # ──────────────────────────────────────────────────────────────────────────

    def _get_agent_metadata(self, agent) -> dict:
        if hasattr(agent, "get_metadata"):
            return agent.get_metadata()
        return {
            "name": getattr(agent, "name", "unknown"),
            "role": getattr(agent, "role", "worker"),
            "description": getattr(agent, "description", ""),
            "skills": getattr(agent, "default_skills", []),
        }

    def _get_plan(self, goal: str, context: dict) -> Optional[dict]:
        plan = self.thinking_agent.run({"goal": goal, "context": context})
        if plan.get("success"):
            return plan.get("output")
        return None

    def _execute_with_retry(self, agent, agent_input: dict, max_retries: int) -> dict:
        result = {}
        for attempt in range(1, max_retries + 1):
            try:
                result = agent.run(agent_input)
                if result.get("success"):
                    return result
                print(f"[APEX] Attempt {attempt}/{max_retries} failed for "
                      f"{getattr(agent, 'name', '?')}: {result.get('error')}")
            except Exception as e:
                print(f"[APEX] Exception on attempt {attempt}: {e}")
                result = {
                    "success": False,
                    "agent_name": getattr(agent, "name", "?"),
                    "task_id": agent_input.get("task_id", ""),
                    "output": None,
                    "error": str(e),
                    "context_for_next": {},
                }
        return result

    def _assemble_final_output(self, goal: str, plan: dict, results: list) -> str:
        results_summary = "\n".join([
            f"Step {r.get('task_id', '?')}: {'✓' if r.get('success') else '✗'} — "
            f"{str(r.get('output', ''))[:200]}"
            for r in results
        ])
        prompt = (
            f"The user's original goal was: '{goal}'\n\n"
            f"Execution results:\n{results_summary}\n\n"
            "Synthesise into a clear, complete, user-facing answer. "
            "Do not include raw JSON. Be direct and structured."
        )
        return self.chat(prompt, reset_history=True)
