"""
agents/outreach/classifier_agent.py
====================================
OUTREACH CLASSIFIER AGENT
==========================
Entry point agent that interprets raw outreach goals into structured OutreachContext.

This agent eliminates all hardcoded assumptions from downstream agents by classifying
the user's intent into:
- outreach_type (LEAD_GEN, PARTNERSHIP, INVESTOR, etc.)
- outreach_goal (BOOK_INTRO_CALL, GET_REPLY, etc.)
- campaign_mode (SINGLE_PROSPECT or BULK_CAMPAIGN)

Falls back to rule-based keyword matching when LLM is unavailable.
"""

import os
import sys
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from agents.outreach.context import (
    OutreachContext,
    VALID_OUTREACH_TYPES,
    VALID_OUTREACH_GOALS,
    VALID_CAMPAIGN_MODES,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OutreachClassifierAgent")


CLASSIFIER_SYSTEM_PROMPT = """
You are an Outreach Classification Specialist for an elite AI Outreach Swarm.
You receive a free-text outreach goal and classify it into structured parameters.

Your task is to analyze the goal and return a JSON object with:
1. outreach_type: One of LEAD_GEN, PARTNERSHIP, INVESTOR, RECRUITMENT, EVENT_PROMO, PR_MEDIA, CUSTOMER_SUCCESS, GENERAL
2. outreach_goal: One of START_CONVERSATION, BOOK_INTRO_CALL, GET_REPLY, REQUEST_DEMO, COLLECT_INFO, SECURE_COMMITMENT
3. campaign_mode: SINGLE_PROSPECT or BULK_CAMPAIGN
4. icp_hints: Dictionary with industries, seniority_levels, company_size_range, geo, keywords, exclusions
5. preferred_channels: Ordered list of channels (email, linkedin, whatsapp, sms)
6. sender_persona: Who we are presenting as
7. value_proposition: Core value statement for this campaign
8. compliance_flags: List of compliance requirements (GDPR, CAN-SPAM, etc.)

Classification rules:
- "investor", "fund", "raise", "series", "pitch" → INVESTOR
- "hire", "candidate", "recruit", "role", "position", "talent" → RECRUITMENT
- "partner", "partnership", "collaborate", "integration" → PARTNERSHIP
- "event", "webinar", "conference", "rsvp", "attend" → EVENT_PROMO
- "press", "media", "journalist", "coverage", "article", "interview" → PR_MEDIA
- "customer", "upsell", "renewal", "success", "nps" → CUSTOMER_SUCCESS
- Default → LEAD_GEN or GENERAL

Goal inference:
- "book a call", "meeting", "intro" → BOOK_INTRO_CALL
- "demo", "show", "presentation" → REQUEST_DEMO
- "just get a reply", "response" → GET_REPLY
- "learn more", "collect info" → COLLECT_INFO
- "close", "commit", "sign" → SECURE_COMMITMENT
- Default → START_CONVERSATION

Campaign mode:
- Single name mentioned → SINGLE_PROSPECT
- "list", "bulk", "all", "many", "campaign" → BULK_CAMPAIGN
- Default → SINGLE_PROSPECT

Output MUST be valid JSON with all fields present.
"""


# Keyword mappings for rule-based fallback
OUTREACH_TYPE_KEYWORDS = {
    "INVESTOR": ["investor", "fund", "raise", "series", "pitch", "funding", "venture", "angel", "capital"],
    "RECRUITMENT": ["hire", "candidate", "recruit", "role", "position", "talent", "job", "hiring", "employment"],
    "PARTNERSHIP": ["partner", "partnership", "collaborate", "integration", "alliance", "joint venture"],
    "EVENT_PROMO": ["event", "webinar", "conference", "rsvp", "attend", "summit", "workshop", "meetup"],
    "PR_MEDIA": ["press", "media", "journalist", "coverage", "article", "interview", "publication", "news"],
    "CUSTOMER_SUCCESS": ["customer", "upsell", "renewal", "success", "nps", "retention", "account"],
    "LEAD_GEN": ["lead", "prospect", "sale", "demo", "meeting", "call", "client"],
}

OUTREACH_GOAL_KEYWORDS = {
    "BOOK_INTRO_CALL": ["book", "call", "meeting", "intro", "schedule", "appointment"],
    "REQUEST_DEMO": ["demo", "show", "presentation", "demonstration"],
    "GET_REPLY": ["reply", "response", "answer", "get back"],
    "COLLECT_INFO": ["learn", "collect", "info", "information", "understand"],
    "SECURE_COMMITMENT": ["close", "commit", "sign", "agree", "deal", "contract"],
}

CAMPAIGN_MODE_KEYWORDS = {
    "BULK_CAMPAIGN": ["list", "bulk", "all", "many", "campaign", "multiple", "batch"],
}


class OutreachClassifierAgent:
    """
    Entry point agent that classifies raw outreach goals into structured OutreachContext.
    
    This agent is the first step in the generalized outreach pipeline, enabling
    all downstream agents to operate without hardcoded playbooks.
    """

    name = "outreach_classifier_agent"
    role = "worker"
    description = (
        "Classifies raw outreach goals into structured OutreachContext. "
        "Determines outreach_type (LEAD_GEN, PARTNERSHIP, INVESTOR, etc.), "
        "outreach_goal, campaign_mode, and initial ICP hints. "
        "Uses LLM classification with rule-based fallback. "
        "Returns fully populated OutreachContext ready to seed the pipeline. "
        "Best for: campaign initialization, intent classification, ICP derivation."
    )

    # Default channel preferences by outreach type
    DEFAULT_CHANNELS = {
        "LEAD_GEN": ["linkedin", "email"],
        "PARTNERSHIP": ["linkedin", "email"],
        "INVESTOR": ["email", "linkedin"],
        "RECRUITMENT": ["linkedin", "email"],
        "EVENT_PROMO": ["email", "linkedin"],
        "PR_MEDIA": ["email"],
        "CUSTOMER_SUCCESS": ["email", "whatsapp"],
        "GENERAL": ["email"],
    }

    def __init__(self, client=None, verbose: bool = False):
        self.verbose = verbose
        self.client = client or self._init_client()

    def _init_client(self):
        """Initialize LLM client for classification."""
        try:
            return make_client(
                CLASSIFIER_SYSTEM_PROMPT,
                "OUTREACH-Classifier",
                api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            logger.warning(f"LLM client init failed: {e}. Will use rule-based fallback.")
            return None

    # ── Registry interface ────────────────────────────────────────────────────

    def get_metadata(self) -> dict:
        """Return agent metadata for registry."""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": ["outreach_classification_skill", "icp_derivation_skill"],
        }

    def run(self, input_data: dict) -> dict:
        """
        Supreme Orchestrator-compatible run() method.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,  # Free-text: "Find investors for our Series A"
                "context": {
                    "raw_goal": str,  # Alternative to instruction
                    "hints": dict,    # Optional hints to guide classification
                }
            }

        Returns:
            {
                "success": bool,
                "agent_name": str,
                "task_id": str,
                "output": dict,  # OutreachContext as dict
                "error": Optional[str],
                "metadata": dict,
                "context_for_next": {"outreach_context": OutreachContext},
            }
        """
        task_id = input_data.get("task_id", "classify_task")
        ctx = input_data.get("context", {})
        instruction = input_data.get("instruction", "")
        raw_goal = ctx.get("raw_goal", instruction)
        hints = ctx.get("hints", {})

        try:
            context = self.classify(raw_goal, hints)
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": context.to_dict(),
                "error": None,
                "metadata": {"outreach_type": context.outreach_type},
                "context_for_next": {"outreach_context": context},
            }
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {
                "success": False,
                "agent_name": self.name,
                "task_id": task_id,
                "output": None,
                "error": str(e),
                "metadata": {},
                "context_for_next": {},
            }

    # ── Core classification ───────────────────────────────────────────────────

    def classify(self, raw_goal: str, hints: Dict[str, Any] = None) -> OutreachContext:
        """
        Classify a raw outreach goal into structured OutreachContext.

        Args:
            raw_goal: Free-text goal (e.g., "Find angel investors for our pre-seed round")
            hints: Optional hints to guide classification (e.g., {"campaign_mode": "BULK_CAMPAIGN"})

        Returns:
            Fully populated OutreachContext ready to seed the pipeline.
        """
        hints = hints or {}

        # Try LLM classification first
        if self.client:
            try:
                context = self._llm_classify(raw_goal, hints)
                if self.verbose:
                    logger.info(f"LLM classification: {context.outreach_type} / {context.outreach_goal}")
                return context
            except Exception as e:
                logger.warning(f"LLM classification failed, using rule fallback: {e}")

        # Fall back to rule-based classification
        context = self._rule_based_classify(raw_goal, hints)
        if self.verbose:
            logger.info(f"Rule-based classification: {context.outreach_type} / {context.outreach_goal}")
        return context

    def _llm_classify(self, raw_goal: str, hints: Dict[str, Any]) -> OutreachContext:
        """Use LLM to classify the raw goal."""
        prompt = f"""Classify this outreach goal into structured parameters.

Goal: {raw_goal}

{f"Additional hints: {json.dumps(hints)}" if hints else ""}

Return a JSON object with these fields:
- outreach_type: One of {list(VALID_OUTREACH_TYPES)}
- outreach_goal: One of {list(VALID_OUTREACH_GOALS)}
- campaign_mode: One of {list(VALID_CAMPAIGN_MODES)}
- icp: Dictionary with industries, seniority_levels, company_size_range, geo, keywords, exclusions, min_icp_score
- preferred_channels: Ordered list of channels
- sender_persona: Who we are presenting as
- value_proposition: Core value statement
- compliance_flags: List of compliance requirements

Output ONLY valid JSON, no other text."""

        response = self.client.ask(prompt)
        
        # Parse JSON from response
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON from LLM: {response[:200]}")

        # Validate and build OutreachContext
        return OutreachContext(
            outreach_type=data.get("outreach_type", "GENERAL"),
            outreach_goal=data.get("outreach_goal", "START_CONVERSATION"),
            campaign_mode=data.get("campaign_mode", hints.get("campaign_mode", "SINGLE_PROSPECT")),
            campaign_id=hints.get("campaign_id", str(uuid.uuid4())),
            icp=data.get("icp", {"min_icp_score": 0.3}),
            preferred_channels=data.get("preferred_channels", ["email"]),
            channel_fallback_policy=hints.get("channel_fallback_policy", "SEQUENTIAL"),
            sender_persona=data.get("sender_persona", ""),
            value_proposition=data.get("value_proposition", ""),
            compliance_flags=data.get("compliance_flags", []),
            contact_id=hints.get("contact_id", ""),
        )

    def _rule_based_classify(self, raw_goal: str, hints: Dict[str, Any]) -> OutreachContext:
        """Use keyword matching to classify when LLM is unavailable."""
        goal_lower = raw_goal.lower()

        # Determine outreach_type
        outreach_type = "GENERAL"
        type_scores = {}
        for otype, keywords in OUTREACH_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > 0:
                type_scores[otype] = score
        if type_scores:
            outreach_type = max(type_scores, key=type_scores.get)

        # Determine outreach_goal
        outreach_goal = "START_CONVERSATION"
        goal_scores = {}
        for goal, keywords in OUTREACH_GOAL_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > 0:
                goal_scores[goal] = score
        if goal_scores:
            outreach_goal = max(goal_scores, key=goal_scores.get)

        # Determine campaign_mode
        campaign_mode = "SINGLE_PROSPECT"
        for mode, keywords in CAMPAIGN_MODE_KEYWORDS.items():
            if any(kw in goal_lower for kw in keywords):
                campaign_mode = mode
                break

        # Use hints to override if provided
        if hints.get("campaign_mode"):
            campaign_mode = hints["campaign_mode"]

        # Build ICP hints from goal text
        icp = self._extract_icp_hints(raw_goal)
        if hints.get("icp"):
            icp.update(hints["icp"])

        # Get default channels for this outreach type
        preferred_channels = self.DEFAULT_CHANNELS.get(outreach_type, ["email"])
        if hints.get("preferred_channels"):
            preferred_channels = hints["preferred_channels"]

        return OutreachContext(
            outreach_type=outreach_type,
            outreach_goal=outreach_goal,
            campaign_mode=campaign_mode,
            campaign_id=hints.get("campaign_id", str(uuid.uuid4())),
            icp=icp,
            preferred_channels=preferred_channels,
            channel_fallback_policy=hints.get("channel_fallback_policy", "SEQUENTIAL"),
            sender_persona=hints.get("sender_persona", ""),
            value_proposition=hints.get("value_proposition", ""),
            compliance_flags=hints.get("compliance_flags", []),
            contact_id=hints.get("contact_id", ""),
        )

    def _extract_icp_hints(self, raw_goal: str) -> Dict[str, Any]:
        """Extract ICP hints from goal text using simple heuristics."""
        icp = {"min_icp_score": 0.3}
        goal_lower = raw_goal.lower()

        # Industry hints
        industries = []
        industry_keywords = {
            "saas": "SaaS",
            "fintech": "Fintech",
            "healthcare": "Healthcare",
            "enterprise": "Enterprise Software",
            "startup": "Startups",
            "e-commerce": "E-commerce",
            "ai": "AI/ML",
            "crypto": "Crypto/Web3",
        }
        for kw, industry in industry_keywords.items():
            if kw in goal_lower:
                industries.append(industry)
        if industries:
            icp["industries"] = industries

        # Seniority hints
        seniority = []
        if any(kw in goal_lower for kw in ["ceo", "founder", "c-level", "executive"]):
            seniority.append("C-Level")
        if any(kw in goal_lower for kw in ["vp", "vice president", "director"]):
            seniority.append("VP/Director")
        if any(kw in goal_lower for kw in ["manager", "lead"]):
            seniority.append("Manager")
        if seniority:
            icp["seniority_levels"] = seniority

        # Company size hints
        if any(kw in goal_lower for kw in ["enterprise", "large", "fortune"]):
            icp["company_size_range"] = "1000+"
        elif any(kw in goal_lower for kw in ["startup", "small", "early"]):
            icp["company_size_range"] = "1-50"

        # Geo hints (simple extraction)
        geo_keywords = ["us", "usa", "united states", "europe", "uk", "asia", "india"]
        geo = [kw.upper() for kw in geo_keywords if kw in goal_lower]
        if geo:
            icp["geo"] = geo

        return icp
