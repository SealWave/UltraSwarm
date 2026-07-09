"""
agents/external/customer_support_agent.py
============================================
Customer Support Agent — adapted from 500-AI-Agents / 13-customer-support-agent
Original: LangGraph + RAG (FAISS) + GPT-4o-mini
This version: Gemini 2.5 Flash + existing RAG manager
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from core.rag_manager import query_knowledge
from tools.output_manager import save_output
from tools.agent_skill_loader import load_skills_for_task, get_skill_loader
from rich.console import Console
from rich.panel import Panel

console = Console()

SYSTEM_PROMPT = """
You are a customer support specialist for an e-commerce store.

You handle customer inquiries with professionalism and empathy.
You classify intent, determine urgency, and draft clear responses.

Escalation triggers (always escalate if present):
- Legal threats or mentions of legal action
- Safety concerns
- Orders over $500 in dispute
- Repeated contacts (3+ times) about same issue

Output format:
{
  "intent": "shipping_inquiry | billing | return_request | technical | general | complaint",
  "urgency": "low | medium | high | escalate",
  "response": "The customer-facing reply text",
  "internal_notes": "Notes for the support team not shown to the customer",
  "escalate": false,
  "escalation_reason": null,
  "suggested_resolution": "What action needs to happen to fully resolve this"
}

Rules:
- Always acknowledge the customer's concern in the opening sentence.
- Never argue with or dismiss the customer's frustration.
- End every response with one clear next step.
- Keep responses under 150 words unless technical detail is required.
- Never promise a refund, replacement, or outcome you cannot confirm.
"""


class CustomerSupportAgent:
    """
    Customer Support Agent.
    Handles customer messages, classifies intent, drafts empathetic responses.
    """

    name = "customer_support_agent"
    role = "worker"
    description = (
        "Handles customer support inquiries: shipping, billing, returns, complaints, "
        "technical issues. Classifies intent and urgency. Drafts professional, empathetic "
        "responses. Flags escalations automatically. "
        "Best for: support ticket responses, help desk, FAQ drafting."
    )
    skill_id = "customer_support_skill"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = make_client(SYSTEM_PROMPT, "CUSTOMER-SUPPORT")

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": [self.skill_id],
        }

    def handle_message(
        self,
        customer_message: str,
        order_context: dict = None,
        store_policy: str = None,
    ) -> dict:
        """
        Handle a customer support message.

        Args:
            customer_message: The raw customer message or ticket text.
            order_context: Optional order details (order_id, product, date, status).
            store_policy: Optional policy text (return window, SLA, etc.).

        Returns:
            dict with intent, urgency, response, internal_notes, escalate, etc.
        """
        console.print(f"\n[cyan]CUSTOMER SUPPORT:[/cyan] {customer_message[:60]}...")

        # Pull relevant policy/knowledge from RAG
        rag_context = query_knowledge(customer_message)

        # Load skill guidance
        skills = load_skills_for_task(f"customer support {customer_message}", top_k=1)
        skill_block = ""
        if skills:
            loader = get_skill_loader()
            skill_block = loader.build_skill_prompt(skills)

        context_block = ""
        if order_context:
            import json
            context_block = f"\nOrder context:\n{json.dumps(order_context, indent=2)}\n"
        if store_policy:
            context_block += f"\nStore policy:\n{store_policy}\n"
        if rag_context:
            context_block += f"\nRelevant knowledge:\n{rag_context}\n"

        prompt = (
            f"Customer message:\n{customer_message}\n"
            f"{context_block}"
            f"{skill_block}\n"
            f"Classify and respond to this customer support message."
        )

        result = self.client.ask_json(prompt)
        save_output("customer_support_agent", "support_ticket", result, "json")

        if result.get("escalate"):
            console.print(f"[bold red]⚠ ESCALATION REQUIRED:[/bold red] {result.get('escalation_reason')}")

        return result

    def run(self, input_data: dict) -> dict:
        """BaseAgent-compatible run() method."""
        task_id = input_data.get("task_id", "support_task")
        instruction = input_data.get("instruction", "")
        context_data = input_data.get("context", {})
        order_ctx = context_data.get("order_context")
        policy = context_data.get("store_policy")

        try:
            result = self.handle_message(
                customer_message=instruction,
                order_context=order_ctx,
                store_policy=policy,
            )
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": result,
                "error": None,
                "metadata": {"escalated": result.get("escalate", False)},
                "context_for_next": {"support_response": result},
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
            "[bold cyan]CUSTOMER SUPPORT AGENT[/bold cyan]\n"
            "[dim]Powered by Gemini 2.5 Flash + RAG[/dim]",
            border_style="cyan"
        ))

        while True:
            msg = input("\nCustomer message (or 'exit'): ").strip()
            if msg.lower() in {"exit", "quit", "q"}:
                break
            result = self.handle_message(msg)
            urgency_color = {"escalate": "red", "high": "yellow", "medium": "blue", "low": "green"}.get(
                result.get("urgency", "low"), "white"
            )
            console.print(Panel(
                f"Intent: {result.get('intent', 'unknown')}\n"
                f"Urgency: [{urgency_color}]{result.get('urgency', 'low')}[/{urgency_color}]\n\n"
                f"Response:\n{result.get('response', '')}\n\n"
                f"[dim]Internal: {result.get('internal_notes', '')}[/dim]",
                title="Support Response",
                border_style=urgency_color
            ))
