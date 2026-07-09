"""
agents/fiverr/gig_creation_agent.py
=====================================
Gig_Creation_Agent — marketplace research and Fiverr gig listing creation.

Responsibilities:
1. Use google_search() to identify in-demand Fiverr service categories from a
   fixed set (lead generation, web scraping, data entry, copywriting, chatbot
   building).
2. Rank categories by the count of distinct search result snippets that mention
   the category name, and select the top-ranked categories for gig creation.
3. Generate a fully-structured gig listing (title, description, tags, pricing
   tiers, FAQs) via the LLM and validate it against schema constraints.
4. Publish the listing via BrowserOperatorAgent.run_task(); if browser
   publication fails, return error status with the gig JSON preserved.
5. Save each gig listing to disk via tools/output_manager.save_output().
6. Return context_for_next containing gig_titles and gig_ids for downstream
   agents.

Pattern: standalone class (same style as FiverrManager and WebResearchAgent),
NOT a subclass of BaseAgent. LLM access via core.make_client().

Usage:
    from agents.fiverr.gig_creation_agent import GigCreationAgent

    agent = GigCreationAgent()
    result = agent.run({"instruction": "Create gigs for top Fiverr categories"})
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from rich.console import Console

from core import make_client
from tools.browser import google_search
from tools.output_manager import save_output

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Service categories to research (requirement 3.1)
SERVICE_CATEGORIES = [
    "lead generation",
    "web scraping",
    "data entry",
    "copywriting",
    "chatbot building",
]

# System prompt for the LLM
_SYSTEM_PROMPT = """
You are an expert Fiverr gig strategist with deep knowledge of the freelance
marketplace. Your job is to craft highly optimised gig listings that attract
buyers and rank well in Fiverr search.

When asked to generate a gig listing you MUST return a JSON object with EXACTLY
these keys:

{
  "title": "<string, under 80 characters>",
  "description": "<string, 150-1200 words>",
  "tags": ["<tag1>", "<tag2>", "<tag3>", "<tag4>", "<tag5>", "..."],  // 5+ tags
  "pricing": {
    "basic":    {"price": <float USD, 5.00-500.00>, "delivery_days": <int 1-30>},
    "standard": {"price": <float USD, 5.00-500.00>, "delivery_days": <int 1-30>},
    "premium":  {"price": <float USD, 5.00-500.00>, "delivery_days": <int 1-30>}
  },
  "faqs": [
    {"question": "<string>", "answer": "<string>"},
    {"question": "<string>", "answer": "<string>"},
    {"question": "<string>", "answer": "<string>"}
  ]
}

Constraints:
- title: MUST be under 80 characters; keyword-rich and compelling.
- description: MUST be between 150 and 1200 words; professional tone.
- tags: MUST include 5 or more relevant lowercase strings.
- pricing.basic.price    >= 5.00 and <= 500.00
- pricing.standard.price >= pricing.basic.price
- pricing.premium.price  >= pricing.standard.price
- delivery_days: integer 1-30 for every tier.
- faqs: at least 3 entries with non-empty question and answer strings.

Return ONLY valid JSON. No markdown, no preamble.
"""

# Schema hint for ask_json
_GIG_SCHEMA_HINT = """
{
  "title": "string (under 80 chars)",
  "description": "string (150-1200 words)",
  "tags": ["string", "..."],
  "pricing": {
    "basic":    {"price": 5.0, "delivery_days": 3},
    "standard": {"price": 20.0, "delivery_days": 5},
    "premium":  {"price": 50.0, "delivery_days": 10}
  },
  "faqs": [
    {"question": "string", "answer": "string"}
  ]
}
"""


class GigCreationAgent:
    """
    Fiverr Gig Creation Agent.

    Researches the Fiverr marketplace for in-demand AI-serviceable categories,
    generates optimised gig listings via LLM, publishes them via browser
    automation, and returns structured output for downstream agents.

    Compatible with the FiverrManager agent registry interface.
    """

    name = "gig_creation_agent"
    role = "worker"
    description = (
        "Researches in-demand Fiverr service categories via web search, "
        "generates optimised gig listings (title, description, tags, pricing "
        "tiers, FAQs) using the LLM, publishes gigs via browser automation, "
        "and returns structured results with context for downstream agents."
    )
    skills = ["gig_creation_skill", "marketplace_research_skill"]

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self.client = make_client(_SYSTEM_PROMPT, "GIG-CREATION")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_metadata(self) -> dict:
        """Return agent metadata compatible with the FiverrManager registry.

        Returns
        -------
        dict
            Keys: name, role, description, skills.
        """
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": self.skills,
        }

    def run(self, input_data: dict) -> dict:
        """Main entry-point for the Gig Creation Agent.

        Performs marketplace research, generates gig listings, attempts browser
        publication, saves outputs, and returns a structured result dict.

        Parameters
        ----------
        input_data : dict
            Accepted keys:
            - ``"instruction"`` (str): task description (used for context).
            - ``"context"`` (dict): optional shared state from FiverrManager,
              may contain ``agent_registry``.
            - ``"task_id"`` (str): optional task identifier for logging.

        Returns
        -------
        dict
            AgentResult-compatible dict with keys:
            ``status``, ``message``, ``data``, ``context_for_next``.
            On browser failure: ``status="error"`` with gig JSON in
            ``data["gig_json"]``.
        """
        task_id = input_data.get("task_id", "gig_creation_task")
        instruction = input_data.get("instruction", "Create optimised Fiverr gig listings")
        context = input_data.get("context", {})

        console.print(
            f"[bold green][GigCreationAgent][/bold green] "
            f"Starting task {task_id}: {instruction}"
        )

        try:
            return self._run_pipeline(task_id, instruction, context)
        except Exception as exc:
            tb = traceback.format_exc()
            console.print(
                f"[bold green][GigCreationAgent][/bold green] "
                f"[red]Unhandled exception: {exc}[/red]"
            )
            return {
                "status": "error",
                "message": f"GigCreationAgent encountered an unexpected error: {exc}",
                "data": {"traceback": tb},
                "context_for_next": {"gig_titles": [], "gig_ids": []},
            }

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(self, task_id: str, instruction: str, context: dict) -> dict:
        """Execute the full gig creation pipeline.

        Steps
        -----
        1. Research marketplace — rank categories by snippet mentions.
        2. Generate gig listing for the top-ranked category.
        3. Validate the listing against schema constraints.
        4. Attempt browser publication via BrowserOperatorAgent.
        5. Save output to disk.
        6. Return structured result with context_for_next.
        """
        # ── Step 1: Marketplace research ───────────────────────────────
        console.print(
            "[bold green][GigCreationAgent][/bold green] "
            "Researching marketplace for in-demand service categories…"
        )
        ranked_categories = self._rank_categories()

        if not ranked_categories:
            return {
                "status": "error",
                "message": "Marketplace research returned no usable categories.",
                "data": {},
                "context_for_next": {"gig_titles": [], "gig_ids": []},
            }

        console.print(
            f"[bold green][GigCreationAgent][/bold green] "
            f"Category ranking: {ranked_categories}"
        )

        # Select top category (at minimum 3 must be identified; we process the
        # top-ranked one for this run as gigs are created incrementally).
        top_category = ranked_categories[0][0]
        top_count = ranked_categories[0][1]
        console.print(
            f"[bold green][GigCreationAgent][/bold green] "
            f"Selected top category: '{top_category}' "
            f"(snippet mentions: {top_count})"
        )

        # ── Step 2: Generate gig listing ───────────────────────────────
        console.print(
            f"[bold green][GigCreationAgent][/bold green] "
            f"Generating gig listing for: {top_category}"
        )
        gig_data = self._generate_gig(top_category, ranked_categories, context)
        if gig_data is None:
            return {
                "status": "error",
                "message": (
                    "Gig listing generation failed: LLM did not return a "
                    "valid structured listing."
                ),
                "data": {},
                "context_for_next": {"gig_titles": [], "gig_ids": []},
            }

        # ── Step 3: Validate listing ────────────────────────────────────
        validation_errors = self._validate_gig(gig_data)
        if validation_errors:
            console.print(
                f"[bold green][GigCreationAgent][/bold green] "
                f"[yellow]Validation issues — attempting repair: "
                f"{validation_errors}[/yellow]"
            )
            gig_data = self._repair_gig(gig_data, validation_errors, top_category)
            # Re-validate after repair
            remaining_errors = self._validate_gig(gig_data)
            if remaining_errors:
                console.print(
                    f"[bold green][GigCreationAgent][/bold green] "
                    f"[yellow]Repair incomplete; proceeding with best effort. "
                    f"Remaining issues: {remaining_errors}[/yellow]"
                )

        console.print(
            f"[bold green][GigCreationAgent][/bold green] "
            f"Gig listing generated: \"{gig_data.get('title', '(no title)')}\" "
        )

        # ── Step 4: Save output (req 3.7) ──────────────────────────────
        try:
            save_output("gig_creation_agent", "gig_listing", gig_data, "json")
        except Exception as save_exc:
            console.print(
                f"[bold green][GigCreationAgent][/bold green] "
                f"[yellow]Warning: could not save gig listing: {save_exc}[/yellow]"
            )

        # ── Step 5: Browser publication (req 3.5, 3.6) ─────────────────
        gig_title = gig_data.get("title", "Fiverr Gig")
        gig_id, publish_success, publish_message = self._publish_gig(gig_data)

        if not publish_success:
            # req 3.6: return error with gig JSON preserved in data
            console.print(
                f"[bold green][GigCreationAgent][/bold green] "
                f"[red]Browser publication failed: {publish_message}[/red]"
            )
            return {
                "status": "error",
                "message": "Browser automation failed. Gig JSON preserved for manual publish.",
                "data": {"gig_json": gig_data},
                "context_for_next": {
                    "gig_titles": [gig_title],
                    "gig_ids": [gig_id],  # "pending_publication"
                },
            }

        # ── Step 6: Return success result ──────────────────────────────
        console.print(
            f"[bold green][GigCreationAgent][/bold green] "
            f"Gig published successfully — id: {gig_id}"
        )
        return {
            "status": "success",
            "message": (
                f"Gig listing '{gig_title}' created and published successfully "
                f"for the '{top_category}' service category. "
                f"Gig ID: {gig_id}."
            ),
            "data": {
                "gig": gig_data,
                "gig_id": gig_id,
                "category": top_category,
                "ranked_categories": ranked_categories,
            },
            "context_for_next": {
                "gig_titles": [gig_title],
                "gig_ids": [gig_id],
            },
        }

    # ------------------------------------------------------------------
    # Marketplace research
    # ------------------------------------------------------------------

    def _rank_categories(self) -> list[tuple[str, int]]:
        """Research all service categories and rank by snippet mention count.

        For each category in SERVICE_CATEGORIES, runs a google_search() query
        and counts how many result snippets contain the category name
        (case-insensitive). Returns categories sorted descending by count.

        Returns
        -------
        list[tuple[str, int]]
            Ordered list of (category_name, mention_count) tuples.
            At least the top-3 usable categories are guaranteed if search
            returns any results.
        """
        scores: dict[str, int] = {}

        for category in SERVICE_CATEGORIES:
            query = f"fiverr {category} gig demand 2024"
            console.print(
                f"[bold green][GigCreationAgent][/bold green] "
                f"Searching: {query}"
            )
            try:
                results = google_search(query)
            except Exception as exc:
                console.print(
                    f"[bold green][GigCreationAgent][/bold green] "
                    f"[yellow]Search failed for '{category}': {exc}[/yellow]"
                )
                results = []

            # Count distinct snippets mentioning the category name (req 3.2)
            count = 0
            for result in results:
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                combined_text = f"{title} {snippet}".lower()
                if category.lower() in combined_text:
                    count += 1

            scores[category] = count
            console.print(
                f"[bold green][GigCreationAgent][/bold green] "
                f"  '{category}' — {count} snippet mention(s)"
            )

        # Sort descending by mention count
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    # ------------------------------------------------------------------
    # Gig listing generation
    # ------------------------------------------------------------------

    def _generate_gig(
        self,
        top_category: str,
        ranked_categories: list[tuple[str, int]],
        context: dict,
    ) -> dict | None:
        """Generate a complete gig listing for *top_category* using the LLM.

        Parameters
        ----------
        top_category : str
            Primary service category for the gig.
        ranked_categories : list[tuple[str, int]]
            Full ranking for context.
        context : dict
            Shared state context from FiverrManager (may contain agent_registry).

        Returns
        -------
        dict or None
            Parsed gig dict with keys title, description, tags, pricing, faqs.
            Returns None if the LLM response cannot be parsed.
        """
        # Build context summary from agent_registry if available
        agent_registry = context.get("agent_registry", {})
        registry_note = ""
        if agent_registry:
            downstream_names = [
                name for name in agent_registry
                if name != self.name
            ]
            if downstream_names:
                registry_note = (
                    f"\nDownstream agents that will consume this output: "
                    f"{', '.join(downstream_names)}. "
                    f"Ensure gig_titles and gig_ids are clear and usable."
                )

        other_categories = [cat for cat, _ in ranked_categories[1:4]]
        category_context = (
            f"Other high-demand categories for cross-promotion: "
            f"{', '.join(other_categories)}."
            if other_categories
            else ""
        )

        prompt = (
            f"Create a complete, professional Fiverr gig listing for the service "
            f"category: **{top_category}**.\n\n"
            f"{category_context}\n"
            f"{registry_note}\n\n"
            f"Requirements:\n"
            f"- Title: under 80 characters, keyword-rich, compelling\n"
            f"- Description: 150-1200 words, professional, buyer-focused\n"
            f"- Tags: 5 or more relevant lowercase strings\n"
            f"- Pricing: basic ($5-$50), standard ($20-$150), premium ($50-$500)\n"
            f"  Each tier must have 'price' (float) and 'delivery_days' (int 1-30)\n"
            f"- FAQs: at least 3 entries (question + answer)\n\n"
            f"Return ONLY the JSON object matching the schema.\n"
            f"Schema hint:\n{_GIG_SCHEMA_HINT}"
        )

        raw = self.client.ask_json(prompt)

        if not isinstance(raw, dict):
            console.print(
                "[bold green][GigCreationAgent][/bold green] "
                "[red]LLM returned non-dict response for gig generation.[/red]"
            )
            return None

        if "parse_error" in raw:
            console.print(
                "[bold green][GigCreationAgent][/bold green] "
                "[red]LLM JSON parse error during gig generation.[/red]"
            )
            return None

        # Confirm required top-level keys are present
        required_keys = {"title", "description", "tags", "pricing", "faqs"}
        if not required_keys.issubset(raw.keys()):
            missing = required_keys - raw.keys()
            console.print(
                f"[bold green][GigCreationAgent][/bold green] "
                f"[yellow]LLM response missing keys: {missing}[/yellow]"
            )
            # Return what we have and let validation/repair fix it
        return raw

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_gig(self, gig: dict) -> list[str]:
        """Validate *gig* against the schema constraints from requirement 3.3/3.4.

        Returns
        -------
        list[str]
            List of human-readable error strings. Empty list means valid.
        """
        errors: list[str] = []

        # --- title ---
        title = gig.get("title", "")
        if not isinstance(title, str) or not title.strip():
            errors.append("title is missing or empty")
        elif len(title) >= 80:
            errors.append(f"title is {len(title)} chars (must be under 80)")

        # --- description ---
        description = gig.get("description", "")
        if not isinstance(description, str) or not description.strip():
            errors.append("description is missing or empty")
        else:
            word_count = len(description.split())
            if word_count < 150:
                errors.append(
                    f"description has {word_count} words (minimum 150)"
                )
            elif word_count > 1200:
                errors.append(
                    f"description has {word_count} words (maximum 1200)"
                )

        # --- tags ---
        tags = gig.get("tags", [])
        if not isinstance(tags, list):
            errors.append("tags must be a list")
        elif len(tags) < 5:
            errors.append(f"tags has {len(tags)} entries (minimum 5)")

        # --- pricing ---
        pricing = gig.get("pricing", {})
        if not isinstance(pricing, dict):
            errors.append("pricing must be a dict")
        else:
            for tier in ("basic", "standard", "premium"):
                tier_data = pricing.get(tier, {})
                if not isinstance(tier_data, dict):
                    errors.append(f"pricing.{tier} must be a dict")
                    continue
                price = tier_data.get("price")
                try:
                    price_f = float(price)
                    if price_f < 5.0 or price_f > 500.0:
                        errors.append(
                            f"pricing.{tier}.price={price_f} out of range $5-$500"
                        )
                except (TypeError, ValueError):
                    errors.append(f"pricing.{tier}.price is not a valid number")
                days = tier_data.get("delivery_days")
                try:
                    days_i = int(days)
                    if days_i < 1 or days_i > 30:
                        errors.append(
                            f"pricing.{tier}.delivery_days={days_i} out of range 1-30"
                        )
                except (TypeError, ValueError):
                    errors.append(f"pricing.{tier}.delivery_days is not a valid integer")

        # --- faqs ---
        faqs = gig.get("faqs", [])
        if not isinstance(faqs, list):
            errors.append("faqs must be a list")
        elif len(faqs) < 3:
            errors.append(f"faqs has {len(faqs)} entries (minimum 3)")
        else:
            for i, faq in enumerate(faqs):
                if not isinstance(faq, dict):
                    errors.append(f"faqs[{i}] must be a dict")
                    continue
                if not faq.get("question", "").strip():
                    errors.append(f"faqs[{i}].question is empty")
                if not faq.get("answer", "").strip():
                    errors.append(f"faqs[{i}].answer is empty")

        return errors

    # ------------------------------------------------------------------
    # Repair
    # ------------------------------------------------------------------

    def _repair_gig(
        self,
        gig: dict,
        errors: list[str],
        category: str,
    ) -> dict:
        """Ask the LLM to fix *errors* in *gig* and return a corrected dict.

        Parameters
        ----------
        gig : dict
            The partially-valid gig dict to repair.
        errors : list[str]
            Validation error messages.
        category : str
            The service category, used in the repair prompt for context.

        Returns
        -------
        dict
            The repaired gig dict (may still have issues if the LLM fails).
        """
        error_list = "\n".join(f"- {e}" for e in errors)
        prompt = (
            f"The following Fiverr gig listing for '{category}' has validation "
            f"errors. Fix them and return the complete corrected JSON.\n\n"
            f"Current listing:\n{gig}\n\n"
            f"Errors to fix:\n{error_list}\n\n"
            f"Return ONLY the corrected JSON object."
        )
        repaired = self.client.ask_json(prompt)
        if isinstance(repaired, dict) and "parse_error" not in repaired:
            return repaired
        # If repair fails, return original
        return gig

    # ------------------------------------------------------------------
    # Browser publication
    # ------------------------------------------------------------------

    def _publish_gig(self, gig_data: dict) -> tuple[str, bool, str]:
        """Attempt to publish *gig_data* to Fiverr via BrowserOperatorAgent.

        Parameters
        ----------
        gig_data : dict
            The validated gig listing dict.

        Returns
        -------
        tuple[str, bool, str]
            (gig_id, success, message)
            - gig_id: extracted or "pending_publication" on failure
            - success: True if BrowserOperatorAgent reports success
            - message: human-readable outcome description
        """
        title = gig_data.get("title", "Fiverr Gig")
        basic_price = gig_data.get("pricing", {}).get("basic", {}).get("price", 5.0)
        basic_days = gig_data.get("pricing", {}).get("basic", {}).get("delivery_days", 3)
        description_snippet = gig_data.get("description", "")[:200]
        tags_str = ", ".join(gig_data.get("tags", [])[:5])

        browser_task = (
            f"Navigate to the Fiverr seller dashboard at https://www.fiverr.com/users/seller "
            f"and create a new gig with the following details:\n"
            f"Title: {title}\n"
            f"Description (first 200 chars): {description_snippet}\n"
            f"Tags: {tags_str}\n"
            f"Basic package price: ${basic_price}, delivery: {basic_days} days\n"
            f"Submit the gig creation form and confirm publication."
        )

        try:
            from agents.browser_operator_agent import BrowserOperatorAgent
            browser_agent = BrowserOperatorAgent(save_outputs=False)
            result = browser_agent.run_task(
                prompt=browser_task,
                start_url="https://www.fiverr.com",
            )
            success = result.get("success", False)
            if success:
                # Try to extract a gig ID from the result summary/steps
                gig_id = self._extract_gig_id(result)
                return (gig_id, True, "Gig published successfully via browser automation.")
            else:
                summary_msg = ""
                summary = result.get("summary", {})
                if isinstance(summary, dict):
                    summary_msg = summary.get("message", "")
                elif isinstance(summary, str):
                    summary_msg = summary
                return (
                    "pending_publication",
                    False,
                    f"BrowserOperatorAgent returned success=False. {summary_msg}".strip(),
                )
        except Exception as exc:
            tb = traceback.format_exc()
            console.print(
                f"[bold green][GigCreationAgent][/bold green] "
                f"[red]Browser publication exception: {exc}[/red]"
            )
            return (
                "pending_publication",
                False,
                f"Browser automation raised an exception: {exc}",
            )

    def _extract_gig_id(self, browser_result: dict) -> str:
        """Attempt to extract a Fiverr gig ID from the BrowserOperatorAgent result.

        Falls back to "pending_publication" if no ID can be found.
        """
        import re

        # Check summary URL
        summary = browser_result.get("summary", {})
        if isinstance(summary, dict):
            current_url = summary.get("current_url", "")
            # Fiverr gig URLs typically contain /manage_gigs/<id> or /gigs/<slug>
            match = re.search(r"/manage_gigs/(\d+)", current_url)
            if match:
                return match.group(1)
            match = re.search(r"/gigs/([a-z0-9_-]+)", current_url)
            if match:
                return match.group(1)

        # Check steps for any URL containing a gig id
        for step in browser_result.get("steps", []):
            result_data = step.get("result", {})
            url = result_data.get("url", "")
            match = re.search(r"/manage_gigs/(\d+)", url)
            if match:
                return match.group(1)

        return "pending_publication"

    # ------------------------------------------------------------------
    # Standalone interactive mode
    # ------------------------------------------------------------------

    def run_interactive(self) -> None:
        """Run the agent interactively from the command line.

        Prompts the user for an instruction, executes the gig creation
        pipeline, and prints the result. Suitable for direct standalone use
        or when launched from ``main.py``.
        """
        from rich.panel import Panel

        console.print(Panel(
            "[bold green]GigCreationAgent — Interactive Mode[/bold green]\n"
            "[dim]Marketplace research → gig listing → browser publication[/dim]",
            border_style="green",
        ))

        while True:
            try:
                instruction = input(
                    "\nInstruction (or 'exit'): "
                ).strip()
                if instruction.lower() in {"exit", "quit", "q"}:
                    break
                if not instruction:
                    instruction = "Create optimised Fiverr gig listings for top categories"

                result = self.run({"instruction": instruction})
                console.print(Panel(
                    f"Status:  {result.get('status', 'unknown')}\n"
                    f"Message: {result.get('message', '')}\n"
                    f"Context: {result.get('context_for_next', {})}",
                    title="Gig Creation Result",
                    border_style="green",
                ))
            except KeyboardInterrupt:
                console.print("\n[dim]GigCreationAgent stopped.[/dim]")
                break


if __name__ == "__main__":
    GigCreationAgent().run_interactive()
