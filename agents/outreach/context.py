"""
agents/outreach/context.py
===========================
Shared data envelope types for the generalized outreach swarm.

All agents read from and write to OutreachContext, enabling adaptive behavior
driven by LLM reasoning rather than hardcoded playbooks.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
import json


@dataclass
class ICPMatchResult:
    """Result of ICP (Ideal Customer Profile) matching for a prospect."""
    score: float  # 0.0 – 1.0
    matched_criteria: List[str] = field(default_factory=list)
    failed_criteria: List[str] = field(default_factory=list)
    recommendation: str = "APPROVE"  # APPROVE | DEPRIORITIZE | REJECT
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ICPMatchResult":
        """Deserialize from dictionary."""
        return cls(
            score=data.get("score", 0.0),
            matched_criteria=data.get("matched_criteria", []),
            failed_criteria=data.get("failed_criteria", []),
            recommendation=data.get("recommendation", "APPROVE"),
            confidence=data.get("confidence", 0.0),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ICPMatchResult":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ChannelStep:
    """A step in the multi-channel sequence."""
    channel: str  # email | linkedin | whatsapp | sms | ...
    order: int  # 1 = primary, 2 = secondary fallback, etc.
    trigger_condition: str = "always"  # "always" | "no_reply_after_{N}_days" | "bounce"
    wait_days: int = 0  # days before attempting this channel
    message_hint: str = ""  # optional tone/content hint for this channel

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChannelStep":
        """Deserialize from dictionary."""
        return cls(
            channel=data.get("channel", ""),
            order=data.get("order", 1),
            trigger_condition=data.get("trigger_condition", "always"),
            wait_days=data.get("wait_days", 0),
            message_hint=data.get("message_hint", ""),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ChannelStep":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class DripStep:
    """A step in the drip campaign sequence."""
    step_number: int
    days_after_previous: int  # dynamic — not hardcoded
    message_theme: str = "direct_ask"  # social_proof | resource_share | direct_ask | breakup | urgency | milestone_reference
    trigger_condition: str = "no_reply"  # no_reply | low_engagement | high_engagement | always
    channel: str = "email"
    accelerate_on_open: bool = False  # compress interval if open/click detected

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DripStep":
        """Deserialize from dictionary."""
        return cls(
            step_number=data.get("step_number", 1),
            days_after_previous=data.get("days_after_previous", 1),
            message_theme=data.get("message_theme", "direct_ask"),
            trigger_condition=data.get("trigger_condition", "no_reply"),
            channel=data.get("channel", "email"),
            accelerate_on_open=data.get("accelerate_on_open", False),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "DripStep":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class DynamicStrategy:
    """LLM-generated strategy for a prospect, driven by OutreachContext."""
    target_contact_status: str  # APPROVED | REJECTED
    rejection_reason: Optional[str] = None
    channel_sequence: List[ChannelStep] = field(default_factory=list)
    persona_classification: str = ""  # inferred from profile + context
    hook_strategy: str = ""  # specific personalization angle
    value_frame: str = ""  # how to frame value for this outreach_type
    tone_directives: str = ""
    drip_plan: List[DripStep] = field(default_factory=list)
    campaign_goal: str = ""
    generated_by: str = "llm"  # "llm" | "rule_fallback"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        data = asdict(self)
        # Convert nested dataclasses
        data["channel_sequence"] = [cs.to_dict() if isinstance(cs, ChannelStep) else cs for cs in self.channel_sequence]
        data["drip_plan"] = [ds.to_dict() if isinstance(ds, DripStep) else ds for ds in self.drip_plan]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DynamicStrategy":
        """Deserialize from dictionary."""
        channel_sequence = [
            ChannelStep.from_dict(cs) if isinstance(cs, dict) else cs
            for cs in data.get("channel_sequence", [])
        ]
        drip_plan = [
            DripStep.from_dict(ds) if isinstance(ds, dict) else ds
            for ds in data.get("drip_plan", [])
        ]
        return cls(
            target_contact_status=data.get("target_contact_status", "APPROVED"),
            rejection_reason=data.get("rejection_reason"),
            channel_sequence=channel_sequence,
            persona_classification=data.get("persona_classification", ""),
            hook_strategy=data.get("hook_strategy", ""),
            value_frame=data.get("value_frame", ""),
            tone_directives=data.get("tone_directives", ""),
            drip_plan=drip_plan,
            campaign_goal=data.get("campaign_goal", ""),
            generated_by=data.get("generated_by", "llm"),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "DynamicStrategy":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class OutreachContext:
    """
    Shared data envelope that flows through every agent in the outreach pipeline.
    
    This context carries the outreach_type, goal, ICP constraints, channel preferences,
    and behavioral signals. Every agent reads from and contributes to this context.
    """
    # --- Classification (set by ClassifierAgent, immutable) ---
    outreach_type: str = "GENERAL"  # LEAD_GEN | PARTNERSHIP | INVESTOR | RECRUITMENT | EVENT_PROMO | PR_MEDIA | CUSTOMER_SUCCESS | GENERAL
    outreach_goal: str = "START_CONVERSATION"  # START_CONVERSATION | BOOK_INTRO_CALL | GET_REPLY | REQUEST_DEMO | COLLECT_INFO | SECURE_COMMITMENT
    campaign_mode: str = "SINGLE_PROSPECT"  # SINGLE_PROSPECT | BULK_CAMPAIGN
    campaign_id: str = ""

    # --- ICP (set by ClassifierAgent, refined by ResearchAgent) ---
    icp: Dict[str, Any] = field(default_factory=lambda: {"min_icp_score": 0.3})

    # --- Channel preferences (set by ClassifierAgent + StrategyAgent) ---
    preferred_channels: List[str] = field(default_factory=lambda: ["email"])
    channel_fallback_policy: str = "SEQUENTIAL"  # SEQUENTIAL | PARALLEL | ESCALATE

    # --- Messaging (set by StrategyAgent) ---
    sender_persona: str = ""
    value_proposition: str = ""
    compliance_flags: List[str] = field(default_factory=list)  # e.g. ["GDPR", "CAN-SPAM"]

    # --- Runtime state (mutated as pipeline progresses) ---
    contact_id: str = ""
    prospect_profile: Optional[str] = None
    icp_match: Optional[ICPMatchResult] = None
    strategy: Optional[DynamicStrategy] = None
    engagement_signals: List[Dict[str, Any]] = field(default_factory=list)
    current_drip_step: int = 0
    opted_out: bool = False
    campaign_stage: str = "CLASSIFYING"  # CLASSIFYING | RESEARCHING | STRATEGIZING | OUTREACHING | WAITING | ANALYZING | COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        data = asdict(self)
        # Convert nested dataclasses
        if self.icp_match is not None:
            data["icp_match"] = self.icp_match.to_dict() if isinstance(self.icp_match, ICPMatchResult) else self.icp_match
        if self.strategy is not None:
            data["strategy"] = self.strategy.to_dict() if isinstance(self.strategy, DynamicStrategy) else self.strategy
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutreachContext":
        """Deserialize from dictionary."""
        icp_match = None
        if data.get("icp_match") is not None:
            icp_match = ICPMatchResult.from_dict(data["icp_match"]) if isinstance(data["icp_match"], dict) else data["icp_match"]

        strategy = None
        if data.get("strategy") is not None:
            strategy = DynamicStrategy.from_dict(data["strategy"]) if isinstance(data["strategy"], dict) else data["strategy"]

        return cls(
            outreach_type=data.get("outreach_type", "GENERAL"),
            outreach_goal=data.get("outreach_goal", "START_CONVERSATION"),
            campaign_mode=data.get("campaign_mode", "SINGLE_PROSPECT"),
            campaign_id=data.get("campaign_id", ""),
            icp=data.get("icp", {"min_icp_score": 0.3}),
            preferred_channels=data.get("preferred_channels", ["email"]),
            channel_fallback_policy=data.get("channel_fallback_policy", "SEQUENTIAL"),
            sender_persona=data.get("sender_persona", ""),
            value_proposition=data.get("value_proposition", ""),
            compliance_flags=data.get("compliance_flags", []),
            contact_id=data.get("contact_id", ""),
            prospect_profile=data.get("prospect_profile"),
            icp_match=icp_match,
            strategy=strategy,
            engagement_signals=data.get("engagement_signals", []),
            current_drip_step=data.get("current_drip_step", 0),
            opted_out=data.get("opted_out", False),
            campaign_stage=data.get("campaign_stage", "CLASSIFYING"),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "OutreachContext":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


# Valid taxonomy sets for validation
VALID_OUTREACH_TYPES = {
    "LEAD_GEN", "PARTNERSHIP", "INVESTOR", "RECRUITMENT",
    "EVENT_PROMO", "PR_MEDIA", "CUSTOMER_SUCCESS", "GENERAL"
}

VALID_OUTREACH_GOALS = {
    "START_CONVERSATION", "BOOK_INTRO_CALL", "GET_REPLY",
    "REQUEST_DEMO", "COLLECT_INFO", "SECURE_COMMITMENT"
}

VALID_CAMPAIGN_MODES = {"SINGLE_PROSPECT", "BULK_CAMPAIGN"}

VALID_CAMPAIGN_STAGES = {
    "CLASSIFYING", "RESEARCHING", "STRATEGIZING", "OUTREACHING",
    "WAITING", "ANALYZING", "COMPLETED", "REJECTED"
}

VALID_ICP_RECOMMENDATIONS = {"APPROVE", "DEPRIORITIZE", "REJECT"}

VALID_CONTACT_STATUSES = {"APPROVED", "REJECTED"}

VALID_CHANNEL_FALLBACK_POLICIES = {"SEQUENTIAL", "PARALLEL", "ESCALATE"}

VALID_STAGE_RECOMMENDATIONS = {"ADVANCE", "PAUSE", "ESCALATE_TO_HUMAN", "STOP"}
