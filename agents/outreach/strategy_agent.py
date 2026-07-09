"""
agents/outreach/strategy_agent.py
==================================
The Strategy Agent generates dynamic outreach strategies using LLM reasoning
guided by OutreachContext. Zero hardcoded playbooks remain.

All strategy is generated from context + profile, with type-aware defaults
for fallback when LLM is unavailable.
"""

import os
import sys
import json
import logging
import re
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from agents.outreach.context import (
    OutreachContext,
    DynamicStrategy,
    ChannelStep,
    DripStep,
    VALID_OUTREACH_TYPES,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StrategyAgent")

STRATEGY_SYSTEM_PROMPT = """
You are the Lead Strategy Director for the AI Outreach Swarm.
Your job is to read a Prospect Profile and OutreachContext, then design a dynamic execution plan.

Your plan must be output in structured JSON containing:
1. target_contact_status: "APPROVED" or "REJECTED" (reject if competitor, spam, or ICP mismatch)
2. rejection_reason: If rejected, explain why (otherwise null)
3. channel_sequence: List of channel steps with {channel, order, trigger_condition, wait_days, message_hint}
4. persona_classification: Technical, Business Executive, Investor, Local SMB Owner, Creator, etc.
5. hook_strategy: The specific personalization angle
6. value_frame: How to frame value for this outreach_type
7. tone_directives: Formal, casual, consultative, direct, etc.
8. drip_plan: List of drip steps with {step_number, days_after_previous, message_theme, trigger_condition, channel, accelerate_on_open}
9. campaign_goal: The specific goal for this campaign
10. generated_by: "llm" or "rule_fallback"

Customize strategy based on outreach_type:
- INVESTOR: Longer intervals (7/14/21/45), credibility-first, traction metrics
- RECRUITMENT: Candidate-centric, growth opportunity framing
- PARTNERSHIP: Mutual benefit, shared audience alignment
- EVENT_PROMO: Compressed intervals, urgency + exclusivity
- PR_MEDIA: Formal, newsworthy angle
- CUSTOMER_SUCCESS: Retention focus, upsell framing
- LEAD_GEN: Standard cadence (3/7/14/30), problem-solution framing

Output ONLY valid JSON with all fields present.
"""


class StrategyAgent:
    """
    Generates dynamic outreach strategies using LLM reasoning guided by OutreachContext.
    No hardcoded playbooks — all strategy is generated from context + profile.
    """

    name = "outreach_strategy_agent"
    role = "worker"
    description = (
        "Generates dynamic outreach strategies based on prospect profile and OutreachContext. "
        "Produces multi-channel sequences, drip plans, and messaging directives. "
        "Zero hardcoded playbooks — all strategy is LLM-generated with rule-based fallback. "
        "Best for: campaign planning, channel selection, drip timing, message personalization."
    )

    # Default drip cadences by outreach type
    DEFAULT_DRIP_CADENCES = {
        "LEAD_GEN": [3, 7, 14, 30],
        "INVESTOR": [7, 14, 21, 45],
        "RECRUITMENT": [4, 10, 20],
        "PARTNERSHIP": [5, 12, 25],
        "EVENT_PROMO": [2, 5, 1],  # Last one is "day before event"
        "PR_MEDIA": [3, 7, 14],
        "CUSTOMER_SUCCESS": [3, 7, 14, 21],
        "GENERAL": [3, 7, 14, 30],
    }

    # Default channels by outreach type
    DEFAULT_CHANNELS = {
        "LEAD_GEN": ["linkedin", "email"],
        "INVESTOR": ["email", "linkedin"],
        "RECRUITMENT": ["linkedin", "email"],
        "PARTNERSHIP": ["linkedin", "email"],
        "EVENT_PROMO": ["email", "linkedin"],
        "PR_MEDIA": ["email"],
        "CUSTOMER_SUCCESS": ["email", "whatsapp"],
        "GENERAL": ["email"],
    }

    # Message themes for drip sequences
    DRIP_THEMES = [
        "social_proof",
        "resource_share",
        "direct_ask",
        "breakup",
        "urgency",
        "milestone_reference",
        "value_reminder",
    ]

    def __init__(self, client=None):
        self.client = client or self._init_client()

    def _init_client(self):
        try:
            return make_client(
                STRATEGY_SYSTEM_PROMPT,
                "OUTREACH-Strategy",
                api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}. Running in fallback mode.")
            return None

    # ── Registry interface ────────────────────────────────────────────────────

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": ["strategy_generation_skill", "channel_planning_skill", "drip_timing_skill"],
        }

    def run(self, input_data: dict) -> dict:
        """
        Supreme Orchestrator-compatible run() method.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,
                "context": {
                    "prospect_profile": str,
                    "outreach_context": OutreachContext (or dict),
                }
            }
        """
        task_id = input_data.get("task_id", "strategy_task")
        ctx = input_data.get("context", {})
        prospect_profile = ctx.get("prospect_profile", "")
        
        # Handle OutreachContext
        context_data = ctx.get("outreach_context")
        if isinstance(context_data, dict):
            context = OutreachContext.from_dict(context_data)
        elif isinstance(context_data, OutreachContext):
            context = context_data
        else:
            context = OutreachContext()

        try:
            strategy = self.develop_strategy(prospect_profile, context)
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": strategy.to_dict(),
                "error": None,
                "metadata": {"target_status": strategy.target_contact_status},
                "context_for_next": {"strategy": strategy},
            }
        except Exception as e:
            return {
                "success": False,
                "agent_name": self.name,
                "task_id": task_id,
                "output": None,
                "error": str(e),
                "metadata": {},
                "context_for_next": {},
            }

    # ── Core strategy generation ──────────────────────────────────────────────

    def develop_strategy(self, prospect_profile: str, context: OutreachContext) -> DynamicStrategy:
        """
        Generate a dynamic strategy for outreach based on profile and context.
        
        Args:
            prospect_profile: The prospect profile text
            context: OutreachContext with outreach_type, goal, ICP, etc.
        
        Returns:
            DynamicStrategy with channel sequence, drip plan, and messaging directives
        """
        # Check if prospect was rejected by ICP
        if context.icp_match and context.icp_match.recommendation == "REJECT":
            return self._create_rejection_strategy(context.icp_match)

        # Try LLM generation
        if self.client:
            try:
                strategy = self._llm_generate_strategy(prospect_profile, context)
                logger.info(f"LLM strategy generated: {strategy.target_contact_status}")
                return strategy
            except Exception as e:
                logger.warning(f"LLM strategy generation failed: {e}. Using rule fallback.")

        # Fall back to rule-based generation
        strategy = self._rule_based_strategy(prospect_profile, context)
        logger.info(f"Rule-based strategy generated: {strategy.target_contact_status}")
        return strategy

    def _llm_generate_strategy(self, prospect_profile: str, context: OutreachContext) -> DynamicStrategy:
        """Use LLM to generate strategy."""
        prompt = f"""Generate an outreach strategy for the following prospect.

Outreach Type: {context.outreach_type}
Outreach Goal: {context.outreach_goal}
Campaign Mode: {context.campaign_mode}
Preferred Channels: {context.preferred_channels}
Sender Persona: {context.sender_persona}
Value Proposition: {context.value_proposition}
Compliance Flags: {context.compliance_flags}

Prospect Profile:
{prospect_profile[:2000]}

Output a JSON object with these fields:
- target_contact_status: "APPROVED" or "REJECTED"
- rejection_reason: null or string explaining why
- channel_sequence: List of {{"channel", "order", "trigger_condition", "wait_days", "message_hint"}}
- persona_classification: string describing prospect type
- hook_strategy: specific personalization angle
- value_frame: how to frame value
- tone_directives: formal/casual/etc.
- drip_plan: List of {{"step_number", "days_after_previous", "message_theme", "trigger_condition", "channel", "accelerate_on_open"}}
- campaign_goal: string
- generated_by: "llm"

Output ONLY valid JSON, no other text."""

        response = self.client.ask(prompt) if hasattr(self.client, "ask") else ""
        
        # Parse JSON from response
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON from LLM: {response[:200]}")

        # Build DynamicStrategy from parsed data
        return self._build_strategy_from_dict(data, context)

    def _rule_based_strategy(self, profile: str, context: OutreachContext) -> DynamicStrategy:
        """Generate strategy using rules when LLM is unavailable."""
        profile_lower = profile.lower()
        
        # Determine channel sequence
        channels = context.preferred_channels or self.DEFAULT_CHANNELS.get(context.outreach_type, ["email"])
        channel_sequence = []
        for i, channel in enumerate(channels[:3], 1):
            channel_sequence.append(ChannelStep(
                channel=channel,
                order=i,
                trigger_condition="always" if i == 1 else f"no_reply_after_{3 * i}_days",
                wait_days=0 if i == 1 else 3 * (i - 1),
                message_hint="",
            ))

        # Determine persona
        persona = "Business Executive"
        if any(kw in profile_lower for kw in ["cto", "developer", "engineer", "technical"]):
            persona = "Technical"
        elif any(kw in profile_lower for kw in ["investor", "vc", "fund", "partner at"]):
            persona = "Investor"
        elif any(kw in profile_lower for kw in ["founder", "ceo", "co-founder"]):
            persona = "Founder"
        elif any(kw in profile_lower for kw in ["local", "owner", "smb"]):
            persona = "Local SMB Owner"

        # Determine hook
        hook = "General operations improvement"
        if "series a" in profile_lower or "funding" in profile_lower:
            hook = "Recent funding - supporting growth phase"
        elif "scaling" in profile_lower or "hiring" in profile_lower:
            hook = "Team scaling and operational efficiency"
        elif "automation" in profile_lower:
            hook = "Automation opportunities in current workflow"

        # Determine value frame based on outreach type
        value_frames = {
            "INVESTOR": "Track record and traction metrics for investment thesis",
            "RECRUITMENT": "Growth opportunity and career advancement potential",
            "PARTNERSHIP": "Mutual benefit and shared audience growth",
            "EVENT_PROMO": "Exclusive access and time-sensitive opportunity",
            "PR_MEDIA": "Newsworthy story and industry insights",
            "CUSTOMER_SUCCESS": "Value realization and continued success",
            "LEAD_GEN": "Problem-solution fit and measurable outcomes",
            "GENERAL": "Value proposition aligned with business goals",
        }

        # Determine tone based on outreach type
        tones = {
            "INVESTOR": "Warm, peer-level, credibility-first",
            "RECRUITMENT": "Candidate-centric, no pressure, growth-focused",
            "PARTNERSHIP": "Collaborative, mutual benefit framing",
            "EVENT_PROMO": "Urgent but professional, exclusive",
            "PR_MEDIA": "Formal, newsworthy, concise",
            "CUSTOMER_SUCCESS": "Supportive, relationship-focused",
            "LEAD_GEN": "Consultative, value-focused",
            "GENERAL": "Professional and direct",
        }

        # Build drip plan
        cadence = self.DEFAULT_DRIP_CADENCES.get(context.outreach_type, [3, 7, 14, 30])
        drip_plan = []
        themes = ["direct_ask", "social_proof", "resource_share", "breakup"]
        for i, days in enumerate(cadence, 1):
            drip_plan.append(DripStep(
                step_number=i,
                days_after_previous=days,
                message_theme=themes[min(i - 1, len(themes) - 1)],
                trigger_condition="no_reply",
                channel=channels[0] if channels else "email",
                accelerate_on_open=True,
            ))

        return DynamicStrategy(
            target_contact_status="APPROVED",
            rejection_reason=None,
            channel_sequence=channel_sequence,
            persona_classification=persona,
            hook_strategy=hook,
            value_frame=value_frames.get(context.outreach_type, value_frames["GENERAL"]),
            tone_directives=tones.get(context.outreach_type, tones["GENERAL"]),
            drip_plan=drip_plan,
            campaign_goal=context.outreach_goal,
            generated_by="rule_fallback",
        )

    def _create_rejection_strategy(self, icp_match) -> DynamicStrategy:
        """Create a rejection strategy when ICP score is below threshold."""
        return DynamicStrategy(
            target_contact_status="REJECTED",
            rejection_reason=f"ICP score {icp_match.score:.2f} below threshold. Failed: {', '.join(icp_match.failed_criteria[:3])}",
            channel_sequence=[],
            persona_classification="",
            hook_strategy="",
            value_frame="",
            tone_directives="",
            drip_plan=[],
            campaign_goal="",
            generated_by="rule_fallback",
        )

    def _build_strategy_from_dict(self, data: Dict[str, Any], context: OutreachContext) -> DynamicStrategy:
        """Build DynamicStrategy from LLM response dictionary."""
        channel_sequence = []
        for cs in data.get("channel_sequence", []):
            if isinstance(cs, dict):
                channel_sequence.append(ChannelStep(
                    channel=cs.get("channel", "email"),
                    order=cs.get("order", 1),
                    trigger_condition=cs.get("trigger_condition", "always"),
                    wait_days=cs.get("wait_days", 0),
                    message_hint=cs.get("message_hint", ""),
                ))

        drip_plan = []
        for ds in data.get("drip_plan", []):
            if isinstance(ds, dict):
                drip_plan.append(DripStep(
                    step_number=ds.get("step_number", 1),
                    days_after_previous=ds.get("days_after_previous", 3),
                    message_theme=ds.get("message_theme", "direct_ask"),
                    trigger_condition=ds.get("trigger_condition", "no_reply"),
                    channel=ds.get("channel", "email"),
                    accelerate_on_open=ds.get("accelerate_on_open", False),
                ))

        return DynamicStrategy(
            target_contact_status=data.get("target_contact_status", "APPROVED"),
            rejection_reason=data.get("rejection_reason"),
            channel_sequence=channel_sequence,
            persona_classification=data.get("persona_classification", ""),
            hook_strategy=data.get("hook_strategy", ""),
            value_frame=data.get("value_frame", ""),
            tone_directives=data.get("tone_directives", ""),
            drip_plan=drip_plan,
            campaign_goal=data.get("campaign_goal", context.outreach_goal),
            generated_by="llm",
        )


# --- CLI / Mock Simulation execution interface ---
def run_interactive_simulation():
    print("=" * 60)
    print("AI Outreach Swarm - Strategy Agent Simulation")
    print("=" * 60)

    mock_profile_tech = """
    # PROSPECT PROFILE
    ### Prospect Overview
    - Name: Alice Johnson
    - Title: CTO
    - Responsibilities: Enterprise software development, pipeline engineering.

    ### Company Profile
    - Company: InnovateCorp
    - Industry: Tech Software
    - Pain Points: Slow deployments, dev team scaling overhead.
    """

    strategy_agent = StrategyAgent()

    # Test with different outreach types
    contexts = [
        OutreachContext(outreach_type="LEAD_GEN", outreach_goal="BOOK_INTRO_CALL", preferred_channels=["linkedin", "email"]),
        OutreachContext(outreach_type="INVESTOR", outreach_goal="SECURE_COMMITMENT", preferred_channels=["email"]),
        OutreachContext(outreach_type="RECRUITMENT", outreach_goal="START_CONVERSATION", preferred_channels=["linkedin"]),
    ]

    for i, ctx in enumerate(contexts, 1):
        print(f"\n--- TEST {i}: {ctx.outreach_type} ---")
        strategy = strategy_agent.develop_strategy(mock_profile_tech, ctx)
        print(json.dumps(strategy.to_dict(), indent=2))


if __name__ == "__main__":
    run_interactive_simulation()
