"""
agents/outreach/outreach_agent.py
==================================
OUTREACH MESSAGE AGENT
=======================
Writes personalised, multi-channel outreach messages.

Delegation model (uses shared agents, no duplication):
- Email drafting     →  agents/external/email_drafting_agent.EmailDraftingAgent
- Social content     →  agents/external/social_media_agent.SocialMediaAgent

This agent's unique value:
- Selects the correct shared agent based on target platform.
- Injects outreach-specific context: prospect profile, strategy, conversation memory.
- Handles platforms not covered by shared agents (WhatsApp, SMS, Telegram).
- Exposes run() / get_metadata() for Supreme Orchestrator compatibility.

Platform routing:
  Email         → EmailDraftingAgent.draft_email()
  LinkedIn      → SocialMediaAgent.generate_content() [linkedin platform]
  Facebook      → SocialMediaAgent.generate_content() [facebook platform]
  Instagram     → SocialMediaAgent.generate_content() [instagram platform]
  Twitter/X     → SocialMediaAgent.generate_content() [twitter platform]
  WhatsApp      → LLM direct (short-form, no shared agent covers this)
  SMS           → LLM direct (25-word hard limit)
  Telegram      → LLM direct (similar to WhatsApp)
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from agents.outreach.context import OutreachContext, DynamicStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OutreachMessageAgent")

OUTREACH_SYSTEM_PROMPT = """
You are the Senior Communications Writer for the AI Outreach Swarm.
You write messages that sound completely human, conversational, and personalised.

Copywriting Rules:
- NEVER open with clichés: "Hope this email finds you well", "Just following up",
  "I wanted to reach out", "Checking in".
- Keep it short. Senior executives do not read long messages.
- Address one specific pain point from the prospect profile.
- End with ONE simple Call to Action. Never more than one.
- Match platform tone precisely:
  * Email: Up to 150 words. Formal subject line + 3 short paragraphs + CTA.
  * LinkedIn: Up to 100 words. Reference their profile. Professional but warm.
  * WhatsApp/Telegram: Up to 60 words. Casual, conversational, emoji allowed.
  * SMS: Maximum 25 words. Direct. No pleasantries.
  * Facebook/Instagram: Up to 80 words. Friendly, visual reference where relevant.

Input you will receive:
- Platform (Email / LinkedIn / WhatsApp / SMS / Telegram / Facebook / Instagram)
- Prospect profile summary
- Campaign strategy context
- Conversation memory (prior exchanges)
- Sequence step (initial / reply / day-3 / day-7 / day-14 / day-30)
"""

# Platforms handled by LLM directly (no shared agent available)
DIRECT_PLATFORMS = {"whatsapp", "sms", "telegram"}

# Platforms routed to SocialMediaAgent
SOCIAL_PLATFORMS = {"linkedin", "facebook", "instagram", "twitter", "twitter/x"}


class OutreachAgent:
    """
    Outreach Message Agent.
    Routes platform-specific message drafting to the best available shared agent
    and falls back to LLM direct generation or static templates.
    """

    name = "outreach_message_agent"
    role = "worker"
    description = (
        "Drafts personalised outreach messages across all platforms: Email, LinkedIn, "
        "WhatsApp, Facebook, Instagram, SMS, Telegram. Delegates to EmailDraftingAgent "
        "for emails and SocialMediaAgent for social platforms. Accepts prospect profile, "
        "strategy JSON, and conversation memory to produce context-aware copy. "
        "Best for: initial outreach, replies, follow-up drip messages."
    )

    def __init__(self, client=None, verbose: bool = False):
        self.verbose = verbose
        self.client = client or self._init_client()
        self._email_agent = self._load_email_agent()
        self._social_agent = self._load_social_agent()

    # ── Client init ──────────────────────────────────────────────────────────

    def _init_client(self):
        try:
            return make_client(
                OUTREACH_SYSTEM_PROMPT,
                "OUTREACH-Message",
                api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            logger.warning(f"LLM client init failed: {e}. Running on template fallbacks.")
            return None

    # ── Shared agent loaders ──────────────────────────────────────────────────

    def _load_email_agent(self):
        try:
            from agents.external.email_drafting_agent import EmailDraftingAgent
            agent = EmailDraftingAgent(verbose=self.verbose)
            logger.info("EmailDraftingAgent loaded successfully.")
            return agent
        except Exception as e:
            logger.warning(f"EmailDraftingAgent unavailable: {e}")
            return None

    def _load_social_agent(self):
        try:
            from agents.external.social_media_agent import SocialMediaAgent
            agent = SocialMediaAgent(verbose=self.verbose)
            logger.info("SocialMediaAgent loaded successfully.")
            return agent
        except Exception as e:
            logger.warning(f"SocialMediaAgent unavailable: {e}")
            return None

    # ── Registry interface ────────────────────────────────────────────────────

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": ["copywriting_skill", "email_drafting_skill", "social_media_skill",
                       "outreach_messaging_skill"],
        }

    def run(self, input_data: dict) -> dict:
        """
        Supreme Orchestrator-compatible run() method.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,          # Free-text task description
                "context": {
                    "strategy": dict,         # Strategy JSON from StrategyAgent
                    "prospect_profile": str,  # Profile from ResearchAgent
                    "memory_summary": str,    # Context from MemoryAgent
                    "sequence_step": str,     # "initial" | "reply" | "day-3" | etc.
                }
            }
        """
        task_id = input_data.get("task_id", "outreach_message_task")
        ctx = input_data.get("context", {})

        strategy = ctx.get("strategy", {})
        profile = ctx.get("prospect_profile", ctx.get("research_results", {}).get("summary", ""))
        memory = ctx.get("memory_summary", "")
        step = ctx.get("sequence_step", "initial")

        try:
            message = self.draft_message(strategy, str(profile), memory, step)
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": message,
                "error": None,
                "metadata": {"platform": strategy.get("primary_platform", "Email"), "step": step},
                "context_for_next": {"drafted_message": message},
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

    # ── Core drafting pipeline ────────────────────────────────────────────────

    def draft_message(
        self,
        strategy: Dict[str, Any],
        prospect_profile: str,
        memory: str = "",
        step: str = "initial",
        context: OutreachContext = None
    ) -> str:
        """
        Routes to the appropriate shared agent or generates directly.
        
        Args:
            strategy: Strategy dict or DynamicStrategy from StrategyAgent
            prospect_profile: Prospect profile text
            memory: Conversation history summary
            step: Sequence step (initial, reply, day-3, etc.)
            context: Optional OutreachContext for type-aware drafting and compliance
        
        Returns:
            Drafted message string, or empty string if opted_out
        """
        # Handle DynamicStrategy object
        if isinstance(strategy, DynamicStrategy):
            strategy = strategy.to_dict()
        
        # Check opted_out flag
        if context and context.opted_out:
            logger.info(f"Contact {context.contact_id} is opted out. Returning empty message.")
            return ""
        
        platform = strategy.get("primary_platform", "Email").lower()
        persona = strategy.get("target_persona_classification", "Business Executive")
        hook = strategy.get("personalization_hook_strategy", "operational efficiency")
        tone = strategy.get("tone_and_style_directives", "professional and concise")

        logger.info(f"Drafting {step} message for platform: {platform.upper()}")

        # Get type-specific framing
        type_framing = ""
        if context:
            type_framing = self._get_type_framing(context.outreach_type, hook)

        # ── Route: Email ──────────────────────────────────────────────────────
        if platform == "email":
            message = self._draft_email(prospect_profile, hook, tone, memory, step, persona, context)
            # Apply compliance flags
            if context and "GDPR" in context.compliance_flags or "CAN-SPAM" in context.compliance_flags:
                message = self._apply_compliance(message, context)
            return message

        # ── Route: Social platforms (LinkedIn, Facebook, Instagram, Twitter) ──
        if platform in SOCIAL_PLATFORMS:
            return self._draft_social(platform, prospect_profile, hook, tone, strategy, step, context)

        # ── Route: Direct (WhatsApp, SMS, Telegram) ───────────────────────────
        if platform in DIRECT_PLATFORMS:
            return self._draft_direct(platform, prospect_profile, hook, memory, step, context)

        # ── Unknown platform → LLM direct ────────────────────────────────────
        return self._draft_llm_direct(platform, strategy, prospect_profile, memory, step, context)

    def _get_type_framing(self, outreach_type: str, hook: str) -> str:
        """Get type-specific framing hints for the message."""
        framing = {
            "INVESTOR": f"Credibility-first approach. Lead with traction and metrics. Hook: {hook}",
            "RECRUITMENT": f"Candidate-centric, growth opportunity framing. No pressure. Hook: {hook}",
            "PARTNERSHIP": f"Mutual benefit framing. Shared audience/tech alignment. Hook: {hook}",
            "EVENT_PROMO": f"Urgency + exclusivity. Clear RSVP CTA. Hook: {hook}",
            "PR_MEDIA": f"Newsworthy angle. Industry insights. Hook: {hook}",
            "CUSTOMER_SUCCESS": f"Retention focus. Value realization. Hook: {hook}",
            "LEAD_GEN": f"Problem-solution framing. Measurable outcomes. Hook: {hook}",
            "GENERAL": hook,
        }
        return framing.get(outreach_type, hook)

    def _apply_compliance(self, message: str, context: OutreachContext) -> str:
        """Apply compliance requirements to the message."""
        if "GDPR" in context.compliance_flags:
            # Add unsubscribe link
            if "unsubscribe" not in message.lower():
                message += "\n\n---\nIf you no longer wish to receive emails, please unsubscribe here: [UNSUBSCRIBE_LINK]"
        
        if "CAN-SPAM" in context.compliance_flags:
            # Add physical address
            if not any(kw in message.lower() for kw in ["address", "suite", "street", "ave", "rd"]):
                message += "\n\n[Your Company Name]\n[Physical Address]\n[City, State ZIP]"
        
        return message

    # ── Email via EmailDraftingAgent ──────────────────────────────────────────

    def _draft_email(self, profile: str, hook: str, tone: str, memory: str, step: str, persona: str, context: OutreachContext = None) -> str:
        context_str = (
            f"This is a cold outreach email for a {persona}.\n"
            f"Personalisation hook: {hook}\n"
            f"Prospect profile summary:\n{profile[:800]}\n"
            f"Conversation history so far:\n{memory or 'None — this is the first message.'}\n"
            f"Sequence step: {step}"
        )
        if self._email_agent:
            try:
                result = self._email_agent.draft_email(
                    context=context_str,
                    tone=tone.split(",")[0].strip() if tone else "professional",
                    recipient="decision maker"
                )
                # Format into readable email text
                subject = result.get("subject", "Quick question")
                greeting = result.get("greeting", "Hi,")
                body = result.get("body", "")
                closing = result.get("closing", "Best regards,")
                sig = result.get("signature_placeholder", "[Your Name]")
                return f"Subject: {subject}\n\n{greeting}\n\n{body}\n\n{closing}\n{sig}"
            except Exception as e:
                logger.error(f"EmailDraftingAgent failed: {e}. Using LLM direct.")

        return self._draft_llm_direct("email", {}, profile, memory, step)

    # ── Social via SocialMediaAgent ───────────────────────────────────────────

    def _draft_social(self, platform: str, profile: str, hook: str, tone: str, strategy: dict, step: str, context: OutreachContext = None) -> str:
        topic = (
            f"Personalised outreach — {hook}. "
            f"Prospect context: {profile[:400]}. "
            f"Sequence step: {step}."
        )
        if self._social_agent:
            try:
                result = self._social_agent.generate_content(
                    topic=topic,
                    platforms=[platform],
                    tone=tone.split(",")[0].strip() if tone else "professional"
                )
                # Extract the relevant platform block
                if platform == "linkedin":
                    linkedin = result.get("linkedin", {})
                    return linkedin.get("post", str(result))
                if platform in ("facebook", "instagram"):
                    ig = result.get("instagram", result.get("facebook", {}))
                    return ig.get("caption", str(result))
                if platform in ("twitter", "twitter/x"):
                    tw = result.get("twitter_x", {})
                    return tw.get("tweet_1", str(result))
                return str(result)
            except Exception as e:
                logger.error(f"SocialMediaAgent failed: {e}. Using LLM direct.")

        return self._draft_llm_direct(platform, strategy, profile, "", step)

    # ── Direct LLM generation for WhatsApp / SMS / Telegram / fallback ───────

    def _draft_direct(self, platform: str, profile: str, hook: str, memory: str, step: str, context: OutreachContext = None) -> str:
        if self.client:
            prompt = (
                f"Write a {platform.upper()} outreach message.\n"
                f"Rules: {'25 words maximum.' if platform == 'sms' else '60 words maximum, casual tone.'}\n"
                f"Hook: {hook}\n"
                f"Prospect: {profile[:300]}\n"
                f"Memory: {memory or 'First contact.'}\n"
                f"Step: {step}\n"
                "Output only the message text, nothing else."
            )
            try:
                if hasattr(self.client, "generate_content"):
                    return self.client.generate_content(prompt).text
                elif hasattr(self.client, "invoke"):
                    resp = self.client.invoke(prompt)
                    return getattr(resp, "content", str(resp))
                elif hasattr(self.client, "ask"):
                    return self.client.ask(prompt)
            except Exception as e:
                logger.error(f"Direct LLM generation failed: {e}.")

        return self._fallback_template(platform, profile, hook, step)

    def _draft_llm_direct(self, platform: str, strategy: dict, profile: str, memory: str, step: str, context: OutreachContext = None) -> str:
        hook = strategy.get("personalization_hook_strategy", "operational efficiency")
        if self.client:
            prompt = (
                f"Draft a {platform} outreach message for the following prospect.\n"
                f"Prospect Profile:\n{profile[:600]}\n"
                f"Personalisation hook: {hook}\n"
                f"Memory / prior context: {memory or 'None.'}\n"
                f"Sequence step: {step}\n"
                f"Platform rules: {OUTREACH_SYSTEM_PROMPT.split('Copywriting Rules:')[1][:500]}"
                "Output the message only."
            )
            try:
                if hasattr(self.client, "generate_content"):
                    return self.client.generate_content(prompt).text
                elif hasattr(self.client, "invoke"):
                    resp = self.client.invoke(prompt)
                    return getattr(resp, "content", str(resp))
                elif hasattr(self.client, "ask"):
                    return self.client.ask(prompt)
            except Exception as e:
                logger.error(f"LLM direct generation failed: {e}.")

        return self._fallback_template(platform, profile, hook, step)

    # ── Static template fallback ──────────────────────────────────────────────

    def _fallback_template(self, platform: str, profile: str, hook: str, step: str) -> str:
        """Last-resort static templates when all LLM routes are unavailable."""
        logger.info(f"Using static fallback template for {platform} / {step}.")
        name = "there"
        company = "your company"
        for line in profile.split("\n"):
            line_lower = line.lower()
            if "name:" in line_lower:
                name = line.split(":")[-1].strip().split()[0]
            elif "company:" in line_lower:
                company = line.split(":")[-1].strip()

        templates = {
            "email": (
                f"Subject: Quick question re: {company}\n\n"
                f"Hi {name},\n\n"
                f"Noticed your team at {company} is focused on {hook}. "
                f"We help companies like yours automate the heavy lifting.\n\n"
                f"Do you have 10 minutes next Tuesday?\n\nBest,\n[Your Name]"
            ),
            "linkedin": (
                f"Hi {name}, saw your work at {company}. "
                f"We help teams with {hook} — thought it might be relevant. Happy to share more."
            ),
            "whatsapp": f"Hi {name}! Quick question — is {hook} something your team at {company} is currently tackling? Would love to share what we do. 🙌",
            "sms": f"Hi {name}, re {company}. We help with {hook}. Quick chat? Reply YES.",
            "telegram": f"Hey {name}, working on {hook} at {company}? We have a solution. Want details?",
            "facebook": f"Hi {name}! Saw your page for {company}. We help businesses with {hook}. Happy to send more info if interested!",
            "instagram": f"Hey {name}! 👋 Love what {company} is doing. We help teams like yours with {hook}. DM us to learn more! ✨",
        }
        return templates.get(platform, templates["email"])


# ── CLI mock simulation ───────────────────────────────────────────────────────
def run_interactive_simulation():
    print("=" * 60)
    print("Outreach Message Agent — Integration Simulation")
    print("=" * 60)
    print("Shared agents loaded: EmailDraftingAgent, SocialMediaAgent")
    print()

    agent = OutreachAgent(verbose=True)
    print(f"Registry metadata: {json.dumps(agent.get_metadata(), indent=2)}\n")

    for platform in ["Email", "LinkedIn", "WhatsApp", "SMS"]:
        strategy = {
            "primary_platform": platform,
            "target_persona_classification": "Business Executive",
            "personalization_hook_strategy": "reducing manual ops overhead",
            "tone_and_style_directives": "professional, concise"
        }
        profile = "Name: Alice Johnson\nCompany: InnovateCorp\nIndustry: Enterprise Software"
        print(f"\n{'─'*40}")
        print(f"Platform: {platform}")
        result = agent.run({
            "task_id": f"test_{platform.lower()}",
            "instruction": f"Draft {platform} message",
            "context": {
                "strategy": strategy,
                "prospect_profile": profile,
                "sequence_step": "initial"
            }
        })
        print(result.get("output", result.get("error")))


if __name__ == "__main__":
    run_interactive_simulation()
