"""
agents/outreach/__init__.py
============================
Exposes all Outreach Swarm agents and a convenience list for the universal
agent registry (agents/registry.py).

Usage:
    from agents.outreach import ALL_OUTREACH_AGENTS

    # Or individually:
    from agents.outreach.research_agent import OutreachResearchAgent
"""

# Context types
from agents.outreach.context import (
    OutreachContext,
    ICPMatchResult,
    DynamicStrategy,
    ChannelStep,
    DripStep,
    VALID_OUTREACH_TYPES,
    VALID_OUTREACH_GOALS,
    VALID_CAMPAIGN_MODES,
)

# Agents
from agents.outreach.orchestrator_agent import OrchestratorAgent as OutreachSwarmOrchestrator
from agents.outreach.research_agent import ResearchAgent as OutreachResearchAgent
from agents.outreach.strategy_agent import StrategyAgent as OutreachStrategyAgent
from agents.outreach.outreach_agent import OutreachAgent as OutreachMessageAgent
from agents.outreach.analysis_agent import AnalysisAgent as OutreachAnalysisAgent
from agents.outreach.memory_agent import MemoryAgent as OutreachMemoryAgent
from agents.outreach.follow_up_agent import FollowUpAgent as OutreachFollowUpAgent
from agents.outreach.notification_watcher import NotificationWatcher as OutreachNotificationWatcher
from agents.outreach.classifier_agent import OutreachClassifierAgent

ALL_OUTREACH_AGENTS = [
    OutreachSwarmOrchestrator,
    OutreachResearchAgent,
    OutreachStrategyAgent,
    OutreachMessageAgent,
    OutreachAnalysisAgent,
    OutreachMemoryAgent,
    OutreachFollowUpAgent,
    OutreachClassifierAgent,
]

__all__ = [
    # Context types
    "OutreachContext",
    "ICPMatchResult",
    "DynamicStrategy",
    "ChannelStep",
    "DripStep",
    "VALID_OUTREACH_TYPES",
    "VALID_OUTREACH_GOALS",
    "VALID_CAMPAIGN_MODES",
    # Agents
    "OutreachSwarmOrchestrator",
    "OutreachResearchAgent",
    "OutreachStrategyAgent",
    "OutreachMessageAgent",
    "OutreachAnalysisAgent",
    "OutreachMemoryAgent",
    "OutreachFollowUpAgent",
    "OutreachNotificationWatcher",
    "OutreachClassifierAgent",
    "ALL_OUTREACH_AGENTS",
]
