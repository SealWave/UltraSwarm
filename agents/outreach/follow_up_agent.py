"""
agents/outreach/follow_up_agent.py
==================================
The Follow-up Agent manages drip sequences with behavioral timing.
Drip intervals are dynamic, driven by engagement signals rather than fixed calendar intervals.

Behavioral Timing:
- Per-type default drip cadences (LEAD_GEN: 3/7/14/30, INVESTOR: 7/14/21/45, etc.)
- Engagement acceleration: compress interval by 30% when open/click detected
- Message themes derived from DripStep.message_theme, not step number alone
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from agents.outreach.context import (
    OutreachContext,
    DripStep,
    DynamicStrategy,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FollowUpAgent")

FOLLOWUP_SYSTEM_PROMPT = """
You are the Retention and Follow-up Writer for the AI Outreach Swarm.
Your job is to draft value-add follow-up messages based on the drip step theme.

Rules:
- Never say "Just following up" or "Checking in".
- Focus each message on the theme provided:
  * social_proof: Share a metric or case study. E.g., "We helped company X reduce task times by 40%."
  * direct_ask: Direct scheduling. E.g., "Would you be open to a 5-minute call? Here is my booking link."
  * resource_share: Offer a checklist or quick audit. E.g., "I put together a brief checklist for automating email responses."
  * breakup: Friendly close-out. E.g., "Assuming this isn't a priority now. I won't reach out again, but feel free to connect later."
  * urgency: Time-sensitive opportunity. E.g., "This offer expires Friday - wanted to make sure you saw it."
  * milestone_reference: Reference a recent event. E.g., "Saw your company announced Series B - congrats!"
  * value_reminder: Remind of core value proposition. E.g., "Just wanted to circle back on how we could reduce your team's overhead."
- Keep the copy native to the platform (Email, LinkedIn, WhatsApp).
- Adapt tone based on outreach_type (more formal for INVESTOR, candidate-centric for RECRUITMENT, etc.).
"""


class FollowUpAgent:
    """
    Manages drip sequences with behavioral timing driven by engagement signals.
    
    Key features:
    - compute_next_drip_step() determines timing based on engagement
    - Per-type default drip cadences for fallback
    - Engagement acceleration: 30% compression when open/click detected
    - Message themes derived from DripStep.message_theme
    """
    
    name = "outreach_follow_up_agent"
    role = "worker"
    description = (
        "Manages drip sequences with behavioral timing. "
        "Computes next drip step based on engagement signals (opens, clicks, replies). "
        "Applies per-type default cadences and engagement acceleration. "
        "Generates follow-up messages themed by drip step strategy. "
        "Best for: follow-up scheduling, drip campaigns, engagement-based timing."
    )

    # Default drip cadences by outreach type (days between steps)
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
        "LEAD_GEN": "linkedin",
        "INVESTOR": "email",
        "RECRUITMENT": "linkedin",
        "PARTNERSHIP": "linkedin",
        "EVENT_PROMO": "email",
        "PR_MEDIA": "email",
        "CUSTOMER_SUCCESS": "email",
        "GENERAL": "email",
    }

    # Default message themes for drip steps (by step index)
    DEFAULT_THEMES = [
        "direct_ask",
        "social_proof",
        "resource_share",
        "breakup",
    ]

    # Engagement acceleration factor (30% compression)
    ACCELERATION_FACTOR = 0.70

    def __init__(self, client=None):
        self.client = client or self._init_client()
        
    def _init_client(self):
        try:
            return make_client(
                FOLLOWUP_SYSTEM_PROMPT,
                "OUTREACH-FollowUp",
                api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            logger.warning(f"Failed to initialize live Gemini client: {e}. Running fallback templates.")
            return None

    # ── Registry interface ────────────────────────────────────────────────────

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": ["drip_timing_skill", "follow_up_generation_skill", "engagement_analysis_skill"],
        }

    def run(self, input_data: dict) -> dict:
        """
        Supreme Orchestrator-compatible run() method.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,
                "context": {
                    "outreach_context": OutreachContext (or dict),
                    "engagement_signals": List[Dict],
                    "drip_step": DripStep (or dict),  # optional
                }
            }
        """
        task_id = input_data.get("task_id", "followup_task")
        ctx = input_data.get("context", {})
        
        # Handle OutreachContext
        context_data = ctx.get("outreach_context")
        if isinstance(context_data, dict):
            context = OutreachContext.from_dict(context_data)
        elif isinstance(context_data, OutreachContext):
            context = context_data
        else:
            context = OutreachContext()

        engagement_signals = ctx.get("engagement_signals", [])
        
        # Handle optional DripStep
        drip_step_data = ctx.get("drip_step")
        if isinstance(drip_step_data, dict):
            drip_step = DripStep.from_dict(drip_step_data)
        elif isinstance(drip_step_data, DripStep):
            drip_step = drip_step_data
        else:
            drip_step = None

        try:
            # If no drip_step provided, compute next one
            if drip_step is None:
                drip_step = self.compute_next_drip_step(context, engagement_signals)

            prospect_profile = context.prospect_profile or ""
            memory_summary = self._summarize_engagement(engagement_signals)
            
            message = self.generate_follow_up(
                prospect_profile=prospect_profile,
                memory_summary=memory_summary,
                context=context,
                drip_step=drip_step,
            )
            
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": {
                    "message": message,
                    "drip_step": drip_step.to_dict(),
                },
                "error": None,
                "metadata": {
                    "step_number": drip_step.step_number,
                    "days_after_previous": drip_step.days_after_previous,
                    "theme": drip_step.message_theme,
                },
                "context_for_next": {
                    "drip_step": drip_step,
                },
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

    # ── Core drip timing logic ────────────────────────────────────────────────

    def compute_next_drip_step(
        self,
        context: OutreachContext,
        engagement_signals: List[Dict[str, Any]],
    ) -> DripStep:
        """
        Compute the next drip step based on context and engagement signals.
        
        Args:
            context: OutreachContext with outreach_type, strategy, current_drip_step
            engagement_signals: List of engagement event dicts with 'event' key
                              (open, click, reply, bounce)
        
        Returns:
            DripStep with computed days_after_previous, message_theme, and channel
        
        Requirements:
            - 4.1: days_after_previous > 0 for all inputs
            - 4.2: non-empty channel for all inputs
            - 4.3: use per-type default cadence when no engagement signals
            - 4.4: compress by 30% when open/click detected and accelerate_on_open = True
        """
        outreach_type = context.outreach_type
        current_step = context.current_drip_step
        
        # Get the strategy's drip plan if available
        drip_plan = None
        if context.strategy and context.strategy.drip_plan:
            drip_plan = context.strategy.drip_plan
        
        # Determine the next step number
        next_step_number = current_step + 1
        
        # Get default cadence for this outreach type
        default_cadence = self.DEFAULT_DRIP_CADENCES.get(
            outreach_type,
            self.DEFAULT_DRIP_CADENCES["GENERAL"]
        )
        
        # Determine the base interval (days_after_previous)
        if drip_plan and next_step_number <= len(drip_plan):
            # Use the strategy's drip plan
            planned_step = drip_plan[next_step_number - 1]
            base_days = planned_step.days_after_previous
            message_theme = planned_step.message_theme
            channel = planned_step.channel
            accelerate_on_open = planned_step.accelerate_on_open
        else:
            # Fall back to default cadence
            step_index = min(next_step_number - 1, len(default_cadence) - 1)
            base_days = default_cadence[step_index] if step_index >= 0 else default_cadence[-1]
            
            # Determine theme based on step
            theme_index = min(next_step_number - 1, len(self.DEFAULT_THEMES) - 1)
            message_theme = self.DEFAULT_THEMES[max(0, theme_index)]
            
            # Determine channel
            channel = self.DEFAULT_CHANNELS.get(outreach_type, "email")
            
            # Default to True for acceleration
            accelerate_on_open = True
        
        # Apply engagement acceleration if applicable
        days_after_previous = self._apply_engagement_acceleration(
            base_days=base_days,
            engagement_signals=engagement_signals,
            accelerate_on_open=accelerate_on_open,
        )
        
        # Ensure days_after_previous is always positive (Requirement 4.1)
        if days_after_previous <= 0:
            days_after_previous = 1
        
        return DripStep(
            step_number=next_step_number,
            days_after_previous=days_after_previous,
            message_theme=message_theme,
            trigger_condition="no_reply",
            channel=channel,
            accelerate_on_open=accelerate_on_open,
        )

    def _apply_engagement_acceleration(
        self,
        base_days: int,
        engagement_signals: List[Dict[str, Any]],
        accelerate_on_open: bool,
    ) -> int:
        """
        Apply engagement-based interval compression.
        
        Requirement 4.4: Compress interval by 30% when open/click detected
        and accelerate_on_open = True.
        
        Args:
            base_days: The base interval from cadence or strategy
            engagement_signals: List of engagement events
            accelerate_on_open: Whether to apply acceleration
        
        Returns:
            Adjusted days_after_previous (compressed if applicable)
        """
        if not accelerate_on_open or not engagement_signals:
            return base_days
        
        # Check for open or click signals
        has_open_or_click = any(
            signal.get("event") in ("open", "click")
            for signal in engagement_signals
        )
        
        if has_open_or_click:
            # Compress by 30% (multiply by 0.70)
            compressed = int(base_days * self.ACCELERATION_FACTOR)
            logger.info(f"Engagement acceleration: {base_days} -> {compressed} days")
            # Ensure minimum of 1 day
            return max(1, compressed)
        
        return base_days

    # ── Message generation ────────────────────────────────────────────────────

    def generate_follow_up(
        self,
        prospect_profile: str,
        memory_summary: str,
        context: OutreachContext,
        drip_step: DripStep,
    ) -> str:
        """
        Drafts a follow-up message based on the drip step theme.
        
        Args:
            prospect_profile: The prospect profile text
            memory_summary: Summary of past interactions
            context: OutreachContext with outreach_type, goal, etc.
            drip_step: DripStep with message_theme and channel
        
        Returns:
            Drafted follow-up message string
        
        Requirement 4.5: Derive message themes from drip_step.message_theme
        """
        platform = drip_step.channel
        theme = drip_step.message_theme
        step = drip_step.step_number

        # Build prompt with context awareness
        prompt = (
            f"Draft a follow-up message with theme: {theme}\n"
            f"Sequence Step: {step}\n"
            f"Target Platform: {platform}\n"
            f"Outreach Type: {context.outreach_type}\n"
            f"Outreach Goal: {context.outreach_goal}\n"
            f"Prospect Profile:\n{prospect_profile}\n\n"
            f"Memory Summary:\n{memory_summary}\n\n"
            "Output drafted message text:"
        )

        if self.client:
            try:
                if hasattr(self.client, 'generate_content'):
                    return self.client.generate_content(prompt).text
                elif hasattr(self.client, 'invoke'):
                    response = self.client.invoke(prompt)
                    return getattr(response, 'content', str(response))
            except Exception as e:
                logger.error(f"LLM follow-up generation failed: {e}. Using fallback templates.")
                
        return self._fallback_drip(platform, step, theme, context.outreach_type)

    def _fallback_drip(
        self,
        platform: str,
        step: int,
        theme: str,
        outreach_type: str,
    ) -> str:
        """
        Predefined rule-based templates for follow-up sequences.
        Templates are themed by message_theme, not just step number.
        """
        logger.info(f"Generating fallback follow-up for step {step} on {platform} with theme '{theme}'.")
        plat = platform.lower()

        # Theme-based templates
        if theme == "social_proof":
            return self._theme_social_proof(plat, outreach_type)
        elif theme == "direct_ask":
            return self._theme_direct_ask(plat, outreach_type)
        elif theme == "resource_share":
            return self._theme_resource_share(plat, outreach_type)
        elif theme == "breakup":
            return self._theme_breakup(plat, outreach_type)
        elif theme == "urgency":
            return self._theme_urgency(plat, outreach_type)
        elif theme == "milestone_reference":
            return self._theme_milestone(plat, outreach_type)
        elif theme == "value_reminder":
            return self._theme_value_reminder(plat, outreach_type)
        else:
            # Default to direct_ask for unknown themes
            return self._theme_direct_ask(plat, outreach_type)

    def _theme_social_proof(self, plat: str, outreach_type: str) -> str:
        """Social proof / case study themed message."""
        if outreach_type == "INVESTOR":
            if plat == "email":
                return "Hi there, thought you'd find this relevant — we've helped similar funds reduce due diligence time by 40% using our automated analysis pipeline. Happy to share the case study if useful."
            return "Hey! We helped a similar fund cut DD time by 40%. Happy to share details if interested."
        
        if plat == "email":
            return "Hi there, thought you might find this useful—our customers recently cut customer reply latency by 50% using unified communication bots. Happy to share the 1-page case study if you're interested."
        elif plat == "linkedin":
            return "Hey! Thought you'd like to see how we helped team X reduce customer support queues by 40%. Happy to send over the case study details if interested."
        return "Hey! Quick stat: unified bots cut client response delay by 50%. Let me know if you want the details!"

    def _theme_direct_ask(self, plat: str, outreach_type: str) -> str:
        """Direct ask / calendar action themed message."""
        if outreach_type == "RECRUITMENT":
            if plat == "linkedin":
                return "Hey! I noticed your background and thought you'd be a great fit for a role we're hiring for. Open to a quick chat about it? Here's my calendar: [Calendar Link]"
            return "Hi there, I think there's a great opportunity that matches your experience. Open to a 10-minute call? Here's my link: [Calendar Link]"
        
        if plat == "email":
            return "Hi there, I know scheduling can be tough. If you're open to checking out a brief demo, here's my calendar booking link: [Calendar Link]. Feel free to select any 10-minute slot."
        elif plat == "linkedin":
            return "Hey! If you have 5 minutes to see a live demo of the swarm, here is my link: [Calendar Link]. Have a great week!"
        return "Hey, if you're open to a brief chat, select a time on my link: [Calendar Link]."

    def _theme_resource_share(self, plat: str, outreach_type: str) -> str:
        """Resource share / free value themed message."""
        if outreach_type == "PARTNERSHIP":
            if plat == "email":
                return "Hi there, I put together a partner integration roadmap that's helped similar companies launch integrations 3x faster. Happy to send it over if you're exploring partnerships."
            return "Hey! Drafted a partnership integration checklist. Happy to share if it'd help your team."
        
        if plat == "email":
            return "Hi there, I put together a custom template for mapping out multi-platform messaging strategies for teams in your sector. Let me know if you'd like me to email it over!"
        elif plat == "linkedin":
            return "Hey! Drafted a multi-platform flow chart for agency teams. Happy to share if you think it'd help your operations."
        return "Hey, I have a multi-platform routing template. Want me to send the PDF?"

    def _theme_breakup(self, plat: str, outreach_type: str) -> str:
        """Breakup / close-out themed message."""
        if plat == "email":
            return "Hi there, I'm assuming this isn't a priority for your team right now, which is completely fine. I won't reach out again. If things change, you can reach me here or at [Website]. All the best!"
        elif plat == "linkedin":
            return "Hey, assuming you're busy now. I won't follow up again, but let's connect if things open up in the future. Cheers!"
        return "Hey, won't follow up again since you're likely busy. Connect later if things change. Cheers!"

    def _theme_urgency(self, plat: str, outreach_type: str) -> str:
        """Urgency / time-sensitive themed message."""
        if outreach_type == "EVENT_PROMO":
            if plat == "email":
                return "Hi there, just a heads up that registration for our event closes this Friday. Would love to see you there if it fits your schedule. Here's the link: [Event Link]"
            return "Hey! Event registration closes Friday. Would be great to have you join — here's the link: [Event Link]"
        
        if plat == "email":
            return "Hi there, wanted to make sure you saw this before the end of the week. Happy to set up a quick call if you have any questions. Here's my calendar: [Calendar Link]"
        return "Hey, just wanted to circle back before the week ends. Let me know if you'd like to chat!"

    def _theme_milestone(self, plat: str, outreach_type: str) -> str:
        """Milestone reference themed message."""
        if plat == "email":
            return "Hi there, congrats on the recent announcement! Thought it might be relevant to discuss how we could support your next phase. Open to a brief call?"
        elif plat == "linkedin":
            return "Hey, saw the news about your recent milestone — congrats! Would love to connect on how we might help with what's next."
        return "Hey, congrats on the recent news! Open to a quick chat about potential collaboration?"

    def _theme_value_reminder(self, plat: str, outreach_type: str) -> str:
        """Value reminder themed message."""
        if outreach_type == "CUSTOMER_SUCCESS":
            if plat == "email":
                return "Hi there, just checking in to make sure you're getting full value from the platform. We've added some new features that might help with your workflow. Want a quick walkthrough?"
            return "Hey! Just checking in — want a quick walkthrough of some new features that might help your team?"
        
        if plat == "email":
            return "Hi there, just wanted to circle back on how we could help reduce your team's operational overhead. We've seen similar teams save 10+ hours per week. Open to a brief chat?"
        elif plat == "linkedin":
            return "Hey! Just wanted to follow up on how we might help streamline your operations. Let me know if you'd like to discuss."
        return "Hey, just circling back on reducing overhead. Open to a quick chat?"

    def _summarize_engagement(self, engagement_signals: List[Dict[str, Any]]) -> str:
        """Create a summary of engagement signals for context."""
        if not engagement_signals:
            return "No previous engagement recorded."
        
        summaries = []
        for signal in engagement_signals[-5:]:  # Last 5 signals
            event = signal.get("event", "unknown")
            platform = signal.get("platform", "unknown")
            timestamp = signal.get("timestamp", "")
            summaries.append(f"{event} on {platform}" + (f" at {timestamp}" if timestamp else ""))
        
        return "Recent engagement: " + ", ".join(summaries)

    # --- Legacy interface for backward compatibility ---
    
    def generate_follow_up_legacy(
        self,
        prospect_profile: str,
        memory_summary: str,
        platform: str,
        step: int,
    ) -> str:
        """
        Legacy interface for backward compatibility.
        Maps step number to theme and generates message.
        """
        # Map step to theme
        theme_index = min(step - 1, len(self.DEFAULT_THEMES) - 1)
        theme = self.DEFAULT_THEMES[max(0, theme_index)]
        
        # Create a minimal DripStep
        drip_step = DripStep(
            step_number=step,
            days_after_previous=3,
            message_theme=theme,
            trigger_condition="no_reply",
            channel=platform.lower(),
            accelerate_on_open=True,
        )
        
        # Create a minimal context
        context = OutreachContext()
        
        return self.generate_follow_up(
            prospect_profile=prospect_profile,
            memory_summary=memory_summary,
            context=context,
            drip_step=drip_step,
        )


# --- CLI / Mock Simulation execution interface ---
def run_interactive_simulation():
    print("=" * 60)
    print("AI Outreach Swarm - Follow-up Agent Simulation")
    print("=" * 60)
    
    agent = FollowUpAgent()
    
    # Test compute_next_drip_step with different outreach types
    print("\n--- Testing compute_next_drip_step ---")
    
    contexts = [
        OutreachContext(outreach_type="LEAD_GEN", current_drip_step=0),
        OutreachContext(outreach_type="INVESTOR", current_drip_step=1),
        OutreachContext(outreach_type="RECRUITMENT", current_drip_step=2),
    ]
    
    engagement_with_open = [
        {"event": "open", "platform": "email", "timestamp": "2024-01-15"},
    ]
    
    for ctx in contexts:
        print(f"\n{ctx.outreach_type} (step {ctx.current_drip_step}):")
        
        # Without engagement
        step = agent.compute_next_drip_step(ctx, [])
        print(f"  No engagement: step={step.step_number}, days={step.days_after_previous}, theme={step.message_theme}")
        
        # With engagement (open detected)
        step_accel = agent.compute_next_drip_step(ctx, engagement_with_open)
        print(f"  With open:    step={step_accel.step_number}, days={step_accel.days_after_previous}, theme={step_accel.message_theme}")
    
    # Test message generation with themes
    print("\n--- Testing message generation by theme ---")
    
    test_themes = ["social_proof", "direct_ask", "resource_share", "breakup"]
    for theme in test_themes:
        drip_step = DripStep(
            step_number=2,
            days_after_previous=7,
            message_theme=theme,
            trigger_condition="no_reply",
            channel="email",
            accelerate_on_open=True,
        )
        context = OutreachContext(outreach_type="LEAD_GEN")
        message = agent.generate_follow_up(
            prospect_profile="CEO of MegaCorp",
            memory_summary="No replies yet.",
            context=context,
            drip_step=drip_step,
        )
        print(f"\n[{theme}]: \"{message[:100]}...\"")

if __name__ == "__main__":
    run_interactive_simulation()
