"""
agents/external/
================
Gemini-native wrapper agents for the 500-AI-Agents project patterns.

Each agent here adapts a 500-AI-Agents pattern (originally OpenAI/LangGraph/CrewAI)
to run on the EcomerseSwarm's Gemini backend, using the same AgentSkill system.

Agents:
    web_research_agent          — research, web search, fact-finding
    email_drafting_agent        — professional email composition
    stock_research_agent        — financial analysis and investment thesis
    customer_support_agent      — support ticket responses, escalation routing
    social_media_agent          — platform-native social content (multi-platform)
    unit_test_generator_agent   — unit test generation for any language
    competitive_analysis_agent  — competitor profiling and strategic recommendations
    multi_agent_debate_agent    — two-sided structured debate with scoring

Usage:
    from agents.external import ALL_EXTERNAL_AGENTS

    # Or import individually:
    from agents.external.web_research_agent import WebResearchAgent
"""

from agents.external.web_research_agent import WebResearchAgent
from agents.external.email_drafting_agent import EmailDraftingAgent
from agents.external.stock_research_agent import StockResearchAgent
from agents.external.customer_support_agent import CustomerSupportAgent
from agents.external.social_media_agent import SocialMediaAgent
from agents.external.unit_test_generator_agent import UnitTestGeneratorAgent
from agents.external.competitive_analysis_agent import CompetitiveAnalysisAgent
from agents.external.multi_agent_debate_agent import MultiAgentDebateAgent

ALL_EXTERNAL_AGENTS = [
    WebResearchAgent,
    EmailDraftingAgent,
    StockResearchAgent,
    CustomerSupportAgent,
    SocialMediaAgent,
    UnitTestGeneratorAgent,
    CompetitiveAnalysisAgent,
    MultiAgentDebateAgent,
]

__all__ = [
    "WebResearchAgent",
    "EmailDraftingAgent",
    "StockResearchAgent",
    "CustomerSupportAgent",
    "SocialMediaAgent",
    "UnitTestGeneratorAgent",
    "CompetitiveAnalysisAgent",
    "MultiAgentDebateAgent",
    "ALL_EXTERNAL_AGENTS",
]
