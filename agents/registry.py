"""
agents/registry.py
==================
UNIVERSAL AGENT REGISTRY
=========================
Single source of truth for every agent in the UltraSwarm codebase.

This module imports and exposes every available agent so that the Supreme
Orchestrator (agents/managers/orchestrator_agent.py) can load them all in
one place without needing to know each agent's folder.

Adding a new agent to the system:
1. Create your agent file in the appropriate folder.
2. Add it to this file in the correct section.
3. Add it to ALL_AGENTS at the bottom.

Agent interface contract:
  - name: str class attribute
  - role: str class attribute ("manager" | "worker" | "helper" | "domain")
  - description: str class attribute
  - get_metadata() -> dict
  - run(input_data: dict) -> dict
"""

from __future__ import annotations
import logging
from typing import Type, Dict, List, Any

logger = logging.getLogger("AgentRegistry")

# ─────────────────────────────────────────────────────────────────────────────
# HELPER AGENTS
# ─────────────────────────────────────────────────────────────────────────────
def _load_helpers() -> List[Any]:
    agents = []
    try:
        from agents.helpers.search_agent import SearchAgent
        agents.append(SearchAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load SearchAgent: {e}")
    try:
        from agents.helpers.thinking_agent import ThinkingAgent
        agents.append(ThinkingAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load ThinkingAgent: {e}")
    return agents


# ─────────────────────────────────────────────────────────────────────────────
# EXTERNAL / GENERAL-PURPOSE AGENTS
# ─────────────────────────────────────────────────────────────────────────────
def _load_external() -> List[Any]:
    agents = []
    try:
        from agents.external import ALL_EXTERNAL_AGENTS
        agents.extend(ALL_EXTERNAL_AGENTS)
    except Exception as e:
        logger.warning(f"[Registry] Could not load external agents: {e}")
    return agents


# ─────────────────────────────────────────────────────────────────────────────
# OUTREACH SWARM AGENTS
# ─────────────────────────────────────────────────────────────────────────────
def _load_outreach() -> List[Any]:
    agents = []
    try:
        from agents.outreach import ALL_OUTREACH_AGENTS
        agents.extend(ALL_OUTREACH_AGENTS)
    except Exception as e:
        logger.warning(f"[Registry] Could not load outreach agents: {e}")
    return agents


# ─────────────────────────────────────────────────────────────────────────────
# ECOMMERCE AGENTS
# ─────────────────────────────────────────────────────────────────────────────
def _load_ecommerce() -> List[Any]:
    agents = []
    try:
        from agents.ecommerce.social_agent import SocialAgent
        agents.append(SocialAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load SocialAgent: {e}")
    try:
        from agents.ecommerce.seo_agent import SEOAgent
        agents.append(SEOAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load SEOAgent: {e}")
    try:
        from agents.ecommerce.product_agent import ProductAgent
        agents.append(ProductAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load ProductAgent: {e}")
    try:
        from agents.ecommerce.ads_agent import AdsAgent
        agents.append(AdsAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load AdsAgent: {e}")
    try:
        from agents.ecommerce.store_manager_agent import StoreManagerAgent
        agents.append(StoreManagerAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load StoreManagerAgent: {e}")
    return agents


# ─────────────────────────────────────────────────────────────────────────────
# FIVERR AGENTS
# ─────────────────────────────────────────────────────────────────────────────
def _load_fiverr() -> List[Any]:
    agents = []
    try:
        from agents.fiverr.fiverr_manager_agent import FiverrManagerAgent
        agents.append(FiverrManagerAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load FiverrManagerAgent: {e}")
    try:
        from agents.fiverr.gig_creation_agent import GigCreationAgent
        agents.append(GigCreationAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load GigCreationAgent: {e}")
    try:
        from agents.fiverr.account_management_agent import AccountManagementAgent
        agents.append(AccountManagementAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load AccountManagementAgent: {e}")
    try:
        from agents.fiverr.scraping_lead_gen_agent import ScrapingLeadGenAgent
        agents.append(ScrapingLeadGenAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load ScrapingLeadGenAgent: {e}")
    return agents


# ─────────────────────────────────────────────────────────────────────────────
# BROWSER / TOOL AGENTS
# ─────────────────────────────────────────────────────────────────────────────
def _load_browser() -> List[Any]:
    agents = []
    try:
        from agents.browser_operator_agent import BrowserOperatorAgent
        agents.append(BrowserOperatorAgent)
    except Exception as e:
        logger.warning(f"[Registry] Could not load BrowserOperatorAgent: {e}")
    return agents


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_registry(verbose: bool = False) -> Dict[str, Any]:
    """
    Instantiates every available agent and returns a dict keyed by agent name.
    Agents that fail to instantiate are skipped with a warning — the system
    degrades gracefully rather than crashing.
    
    Features:
    - Registers dependencies between agents
    - Detects circular dependencies
    - Logs any conflicts found

    Returns:
        dict: { agent_name (str) -> agent_instance }
    """
    all_classes = (
        _load_helpers()
        + _load_external()
        + _load_outreach()
        + _load_ecommerce()
        + _load_fiverr()
        + _load_browser()
    )

    registry: Dict[str, Any] = {}
    
    # Get dependency resolver from BaseAgent
    try:
        from core.base_agent import BaseAgent
        resolver = BaseAgent.get_dependency_resolver()
    except Exception as e:
        logger.warning(f"[Registry] Could not get dependency resolver: {e}")
        resolver = None
    
    for cls in all_classes:
        try:
            # Most agents accept verbose; some don't — handle both
            try:
                instance = cls(verbose=verbose)
            except TypeError:
                instance = cls()

            name = getattr(instance, "name", cls.__name__.lower())
            registry[name] = instance
            logger.debug(f"[Registry] Loaded: {name}")
            
            # Register dependencies explicitly (per design choice Q3)
            # Each agent class can define its own dependencies as a class attribute
            if resolver and hasattr(cls, "dependencies"):
                deps = getattr(cls, "dependencies", [])
                if isinstance(deps, list):
                    resolver.register_dependency(name, deps)
                    logger.debug(f"[Registry] Registered dependencies for {name}: {deps}")
        
        except Exception as e:
            logger.warning(f"[Registry] Could not instantiate {cls.__name__}: {e}")

    # Detect conflicts after all agents are loaded
    if resolver:
        agent_names = list(registry.keys())
        conflicts = resolver.detect_conflicts(agent_names)
        
        if conflicts:
            logger.warning(f"[Registry] Dependency conflicts detected: {conflicts}")
        else:
            logger.debug("[Registry] No dependency conflicts detected")

    logger.info(f"[Registry] {len(registry)} agents loaded successfully.")
    return registry


def list_agents(registry: Dict[str, Any]) -> None:
    """Pretty-print all loaded agents grouped by role."""
    from rich.console import Console
    from rich.table import Table
    console = Console()

    table = Table(title="Universal Agent Registry", show_lines=True)
    table.add_column("Name", style="cyan")
    table.add_column("Role", style="magenta")
    table.add_column("Description", style="white", max_width=70)

    # Sort by role then name
    sorted_agents = sorted(
        registry.values(),
        key=lambda a: (getattr(a, "role", "z"), getattr(a, "name", ""))
    )
    for agent in sorted_agents:
        table.add_row(
            getattr(agent, "name", "?"),
            getattr(agent, "role", "?"),
            getattr(agent, "description", "")[:70],
        )
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE: Domain-specific sub-registries
# ─────────────────────────────────────────────────────────────────────────────

SWARM_DOMAINS = {
    "outreach": "agents.outreach.orchestrator_agent.OutreachSwarmOrchestrator",
    "ecommerce": "agents.ecommerce.store_manager_agent.StoreManagerAgent",
    "fiverr": "agents.fiverr.fiverr_manager_agent.FiverrManagerAgent",
}


def get_domain_agent(domain: str, verbose: bool = False):
    """
    Returns the top-level coordinator agent for a given swarm domain.
    Used by the Supreme Orchestrator's dispatch_to_swarm() method.
    """
    import importlib
    path = SWARM_DOMAINS.get(domain.lower())
    if not path:
        raise ValueError(f"Unknown swarm domain: '{domain}'. Available: {list(SWARM_DOMAINS.keys())}")

    module_path, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    try:
        return cls(verbose=verbose)
    except TypeError:
        return cls()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, __file__.replace("agents/registry.py", ""))
    registry = build_registry(verbose=True)
    list_agents(registry)
