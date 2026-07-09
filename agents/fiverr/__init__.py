"""
agents/fiverr/
==============
Fiverr automation sub-swarm for the UltraSwarm multi-agent system.

The Fiverr_Manager orchestrates all Fiverr operations and delegates to five
specialized sub-agents. All agents follow the BaseAgent-compatible interface
used throughout the UltraSwarm system.

Agents:
    FiverrManager               — central orchestrator for all Fiverr tasks
    GigCreationAgent            — marketplace research and gig listing creation
    ScrapingLeadGenAgent        — web scraping and lead generation order fulfilment
    AccountManagementAgent      — gig metrics, order deadlines, account health
    InboxCommunicationAgent     — inbox monitoring and automated reply generation
    NotificationAgent           — real-time alerts via email and webhook channels

Usage:
    from agents.fiverr import FiverrManager, ALL_FIVERR_AGENTS

    # Or import individually:
    from agents.fiverr.fiverr_manager_agent import FiverrManager
"""

try:
    from agents.fiverr.fiverr_manager_agent import FiverrManager
except ImportError:
    FiverrManager = None  # type: ignore[assignment,misc]

try:
    from agents.fiverr.gig_creation_agent import GigCreationAgent
except ImportError:
    GigCreationAgent = None  # type: ignore[assignment,misc]

try:
    from agents.fiverr.scraping_lead_gen_agent import ScrapingLeadGenAgent
except ImportError:
    ScrapingLeadGenAgent = None  # type: ignore[assignment,misc]

try:
    from agents.fiverr.account_management_agent import AccountManagementAgent
except ImportError:
    AccountManagementAgent = None  # type: ignore[assignment,misc]

try:
    from agents.fiverr.inbox_communication_agent import InboxCommunicationAgent
except ImportError:
    InboxCommunicationAgent = None  # type: ignore[assignment,misc]

try:
    from agents.fiverr.notification_agent import NotificationAgent
except ImportError:
    NotificationAgent = None  # type: ignore[assignment,misc]

# All five sub-agent classes (excludes the manager orchestrator).
# None entries are filtered out so callers can safely iterate even when
# some agents have not yet been implemented.
ALL_FIVERR_AGENTS = [
    agent
    for agent in [
        GigCreationAgent,
        ScrapingLeadGenAgent,
        AccountManagementAgent,
        InboxCommunicationAgent,
        NotificationAgent,
    ]
    if agent is not None
]

__all__ = [
    "FiverrManager",
    "GigCreationAgent",
    "ScrapingLeadGenAgent",
    "AccountManagementAgent",
    "InboxCommunicationAgent",
    "NotificationAgent",
    "ALL_FIVERR_AGENTS",
]
