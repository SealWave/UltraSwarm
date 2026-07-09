"""
agents/external/email_drafting_agent.py
=========================================
Email Drafting Agent — adapted from 500-AI-Agents / 05-email-drafting-agent
Original: CrewAI (analyst + writer crew) + GPT-4o-mini
This version: Gemini 2.5 Flash with a two-turn pipeline (analyze then write)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from tools.output_manager import save_output
from tools.agent_skill_loader import load_skills_for_task, get_skill_loader
from rich.console import Console
from rich.panel import Panel

console = Console()

SYSTEM_PROMPT = """
You are a professional email composition specialist.

You write clear, concise, and effective professional emails that get responses.
You adapt tone precisely to the recipient and situation.

Capabilities:
- Context analysis: extract purpose, key message, and call-to-action
- Tone adaptation: professional, friendly, formal, assertive, empathetic
- Recipient-aware language: clients, executives, vendors, team members
- Concise output: body under 200 words unless explicitly asked for more

Output format for drafting:
{
  "subject": "Subject line under 60 chars",
  "greeting": "Dear/Hi [Name/Title],",
  "body": "Full email body text",
  "closing": "Best regards, / Sincerely,",
  "signature_placeholder": "[Your Name] | [Title] | [Contact]",
  "tone_used": "professional | friendly | formal | assertive | empathetic",
  "word_count": 150
}

Rules:
- Subject line must be specific and action-oriented.
- Body must end with one clear call-to-action.
- Never open with "I hope this email finds you well."
- No invented facts about the recipient or company.
"""


class EmailDraftingAgent:
    """
    Email Drafting Agent.
    Two-turn pipeline: analyze context → draft email.
    """

    name = "email_drafting_agent"
    role = "worker"
    description = (
        "Drafts professional emails of any type: follow-ups, outreach, proposals, "
        "confirmations, announcements, apologies. Adapts tone to recipient. "
        "Best for: any task where the output is a ready-to-send email."
    )
    skill_id = "email_drafting_skill"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = make_client(SYSTEM_PROMPT, "EMAIL-DRAFT")

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": [self.skill_id],
        }

    def draft_email(
        self,
        context: str,
        tone: str = "professional",
        recipient: str = "the recipient",
        additional_context: dict = None,
    ) -> dict:
        """
        Draft a professional email.

        Args:
            context: What the email is about / the situation.
            tone: Target tone (professional, friendly, formal, assertive, empathetic).
            recipient: Description of who the email is to.
            additional_context: Optional extra info dict (previous emails, product details, etc.)

        Returns:
            dict with subject, greeting, body, closing, signature_placeholder, tone_used, word_count.
        """
        console.print(f"\n[cyan]EMAIL DRAFTING:[/cyan] {context[:60]}...")

        # Load skill for enriched output guidance
        skills = load_skills_for_task(f"draft email {context}", top_k=1)
        skill_block = ""
        if skills:
            loader = get_skill_loader()
            skill_block = loader.build_skill_prompt(skills)

        extra = ""
        if additional_context:
            import json
            extra = f"\n\nAdditional context:\n{json.dumps(additional_context, indent=2)}"

        # Turn 1: Analyze
        analysis_prompt = (
            f"Analyze this email requirement:\n\n"
            f"Context: {context}\n"
            f"Recipient: {recipient}\n"
            f"Desired tone: {tone}\n"
            f"{extra}\n\n"
            f"Extract: purpose, key points to cover, suggested subject line, call-to-action.\n"
            f"Return a JSON object with keys: purpose, key_points, subject_suggestion, cta."
        )
        analysis = self.client.ask_json(analysis_prompt)

        # Turn 2: Draft
        draft_prompt = (
            f"Using this analysis, draft the complete email:\n\n"
            f"Analysis: {analysis}\n"
            f"Original context: {context}\n"
            f"Recipient: {recipient}\n"
            f"Tone: {tone}\n"
            f"{skill_block}\n\n"
            f"Return the complete email as a JSON object with: "
            f"subject, greeting, body, closing, signature_placeholder, tone_used, word_count."
        )
        result = self.client.ask_json(draft_prompt)

        save_output("email_drafting_agent", f"email_{context[:30]}", result, "json")
        return result

    def run(self, input_data: dict) -> dict:
        """BaseAgent-compatible run() method."""
        task_id = input_data.get("task_id", "email_task")
        instruction = input_data.get("instruction", "")
        context_data = input_data.get("context", {})
        tone = context_data.get("tone", "professional")
        recipient = context_data.get("recipient", "the recipient")

        try:
            result = self.draft_email(
                context=instruction,
                tone=tone,
                recipient=recipient,
                additional_context=context_data if context_data else None,
            )
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": result,
                "error": None,
                "metadata": {},
                "context_for_next": {"drafted_email": result},
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

    def run_interactive(self):
        """Standalone interactive mode."""
        console.print(Panel(
            "[bold cyan]EMAIL DRAFTING AGENT[/bold cyan]\n"
            "[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="cyan"
        ))

        while True:
            context = input("\nEmail context/purpose (or 'exit'): ").strip()
            if context.lower() in {"exit", "quit", "q"}:
                break
            tone = input("Tone [professional]: ").strip() or "professional"
            recipient = input("Recipient [the recipient]: ").strip() or "the recipient"
            result = self.draft_email(context, tone=tone, recipient=recipient)
            formatted = (
                f"Subject: {result.get('subject', '')}\n\n"
                f"{result.get('greeting', '')}\n\n"
                f"{result.get('body', '')}\n\n"
                f"{result.get('closing', '')}\n"
                f"{result.get('signature_placeholder', '')}"
            )
            console.print(Panel(formatted, title="Drafted Email", border_style="green"))
