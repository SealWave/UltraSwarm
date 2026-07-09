"""
agents/fiverr/account_management_agent.py
==========================================
Account_Management_Agent — gig performance monitoring, deadline tracking,
and account health assessment.

Responsibilities:
1. Use BrowserOperatorAgent.run_task() to navigate the Fiverr analytics
   dashboard and extract views, clicks, orders, and avg_review_score for
   each active gig.
2. Check active order deadlines and flag any order within 24 hours.
3. Assess overall account health against defined thresholds and return
   "healthy", "at_risk", or "critical" status with recommendations.
4. Save the performance report via tools/output_manager.save_output().

Pattern: standalone class (same style as GigCreationAgent), NOT a subclass
of BaseAgent. LLM access via core.make_client().

Usage:
    from agents.fiverr.account_management_agent import AccountManagementAgent

    agent = AccountManagementAgent()
    result = agent.run({"instruction": "Check account performance"})
"""

import os
import sys
import json
import traceback
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from rich.console import Console

from core import make_client
from tools.output_manager import save_output

console = Console()

# ---------------------------------------------------------------------------
# Account health thresholds
# ---------------------------------------------------------------------------
THRESHOLD_REVIEW_SCORE = 4.5     # avg_review_score >= 4.5
THRESHOLD_RESPONSE_RATE = 90.0   # response_rate >= 90 (percent)
THRESHOLD_LATE_DELIVERY = 5.0    # late_delivery_rate <= 5 (percent)

# Deadline warning window in hours
DEADLINE_WARNING_HOURS = 24

# ---------------------------------------------------------------------------
# System prompt for LLM — used for parsing browser results and generating
# recommendations.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """
You are an expert Fiverr account manager. You analyse gig performance data,
order deadlines, and account-level metrics to produce clear, actionable insights
that help sellers maintain a top-rated account.

When asked to parse analytics data from a browser result, return ONLY valid JSON.
When asked for recommendations, return a JSON array of concise string items.
No markdown, no preamble.
"""


class AccountManagementAgent:
    """
    Fiverr Account Management Agent.

    Monitors gig performance metrics, order deadlines, and overall account
    health. Returns structured output for the FiverrManager and downstream
    agents (e.g. NotificationAgent for deadline alerts).

    Compatible with the FiverrManager agent registry interface.
    """

    name = "account_management_agent"
    role = "worker"
    description = (
        "Monitors Fiverr gig performance metrics (views, clicks, orders, "
        "review scores) via browser automation, flags orders within 24 hours "
        "of their deadline, assesses overall account health against defined "
        "thresholds, and saves a performance report to disk."
    )
    skills = ["account_management_skill", "analytics_monitoring_skill"]

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self.client = make_client(_SYSTEM_PROMPT, "ACCOUNT-MGMT")

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
        """Main entry-point for the Account Management Agent.

        Parameters
        ----------
        input_data : dict
            Accepted keys:
            - ``"instruction"`` (str): task description (used for context).
            - ``"context"`` (dict): optional shared state from FiverrManager,
              may contain ``agent_registry`` and ``open_orders``.
            - ``"task_id"`` (str): optional task identifier for logging.

        Returns
        -------
        dict
            AgentResult-compatible dict with keys:
            ``status``, ``message``, ``data``, ``context_for_next``.
            On browser failure: ``status="error"`` without metric fields.
        """
        task_id = input_data.get("task_id", "account_management_task")
        instruction = input_data.get(
            "instruction", "Check Fiverr account performance and order deadlines"
        )
        context = input_data.get("context", {})

        console.print(
            f"[bold blue][AccountManagementAgent][/bold blue] "
            f"Starting task {task_id}: {instruction}"
        )

        try:
            return self._run_pipeline(task_id, instruction, context)
        except Exception as exc:
            tb = traceback.format_exc()
            console.print(
                f"[bold blue][AccountManagementAgent][/bold blue] "
                f"[red]Unhandled exception: {exc}[/red]"
            )
            return {
                "status": "error",
                "message": (
                    f"AccountManagementAgent encountered an unexpected error: {exc}"
                ),
                "data": {"traceback": tb},
                "context_for_next": {},
            }

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(self, task_id: str, instruction: str, context: dict) -> dict:
        """Execute the full account management pipeline.

        Steps
        -----
        1. Navigate the Fiverr analytics dashboard via BrowserOperatorAgent
           and extract gig metrics
        2. Check active order deadlines
        3. Assess account health and build recommendations
        4. Save performance report
        5. Return structured result.
        """
        # ── Step 1: Navigate analytics dashboard ───────────────────────
        console.print(
            "[bold blue][AccountManagementAgent][/bold blue] "
            "Navigating Fiverr analytics dashboard via browser…"
        )
        browser_result = self._fetch_dashboard_data()

        # return error if browser fails
        if browser_result is None:
            return {
                "status": "error",
                "message": (
                    "BrowserOperatorAgent failed to navigate the Fiverr "
                    "analytics dashboard. No metrics collected."
                ),
                "data": {},
                "context_for_next": {},
            }

        # ── Step 2: Parse gig metrics from browser result ───────────────
        gig_metrics = self._parse_gig_metrics(browser_result)
        console.print(
            f"[bold blue][AccountManagementAgent][/bold blue] "
            f"Extracted metrics for {len(gig_metrics)} active gig(s)."
        )

        # ── Step 3: Check order deadlines ───────────────────────────────
        open_orders = context.get("open_orders", [])
        if not isinstance(open_orders, list):
            open_orders = []

        deadline_warnings = self._check_deadlines(open_orders, browser_result)
        console.print(
            f"[bold blue][AccountManagementAgent][/bold blue] "
            f"Deadline warnings: {len(deadline_warnings)}"
        )

        # ── Step 4: Assess account health ───────────────────────────────
        account_metrics = self._parse_account_metrics(browser_result, gig_metrics)
        account_health, recommendations = self._assess_health(account_metrics)
        console.print(
            f"[bold blue][AccountManagementAgent][/bold blue] "
            f"Account health: {account_health}"
        )

        # ── Step 5: Assemble data payload ───────────────────────────────
        data: dict = {
            "gig_metrics": gig_metrics,
            "deadline_warnings": deadline_warnings,
            "account_health": account_health,
            "account_metrics": account_metrics,
        }
        if recommendations:
            data["recommendations"] = recommendations

        # ── Step 6: Save performance report  ───────────────────
        report_data = {
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        try:
            save_output(
                "account_management_agent",
                "performance_report",
                report_data,
                "json",
            )
            console.print(
                "[bold blue][AccountManagementAgent][/bold blue] "
                "Performance report saved."
            )
        except Exception as save_exc:
            console.print(
                f"[bold blue][AccountManagementAgent][/bold blue] "
                f"[yellow]Warning: could not save report: {save_exc}[/yellow]"
            )

        # ── Step 7: Build context_for_next ──────────────────────────────
        context_for_next: dict = {}
        if deadline_warnings:
            context_for_next["new_events"] = [
                {
                    "event_type": "deadline_warning",
                    "message": w["order_id"],
                    "timestamp": w["deadline_timestamp"],
                }
                for w in deadline_warnings
            ]

        # ── Step 8: Build human-readable message ────────────────────────
        gig_count = len(gig_metrics)
        warn_count = len(deadline_warnings)
        message_parts = [
            f"Performance check complete. "
            f"{gig_count} active gig(s) monitored.",
        ]
        if warn_count:
            message_parts.append(
                f"{warn_count} order(s) due within {DEADLINE_WARNING_HOURS} hours."
            )
        message_parts.append(f"Account health: {account_health}.")
        if recommendations:
            message_parts.append(
                f"{len(recommendations)} recommendation(s) generated."
            )

        return {
            "status": "success",
            "message": " ".join(message_parts),
            "data": data,
            "context_for_next": context_for_next,
        }

    # ------------------------------------------------------------------
    # Browser automation
    # ------------------------------------------------------------------

    def _fetch_dashboard_data(self) -> dict | None:
        """Navigate Fiverr analytics dashboard and return raw browser result.

        Returns
        -------
        dict or None
            BrowserOperatorAgent result dict on success, None on failure
            (exception raised or success==False).
        """
        browser_task = (
            "Navigate to the Fiverr seller analytics dashboard at "
            "https://www.fiverr.com/users/seller/analytics "
            "and extract the following data for every gig with status 'Active':\n"
            "- gig title\n"
            "- views (integer)\n"
            "- clicks (integer)\n"
            "- orders (integer)\n"
            "- average review score (float)\n\n"
            "Also extract the following account-level metrics:\n"
            "- response rate (percentage)\n"
            "- late delivery rate (percentage)\n"
            "- overall average review score\n\n"
            "Then navigate to the active orders page at "
            "https://www.fiverr.com/users/seller/manage_orders "
            "and extract for every active order:\n"
            "- order_id (string)\n"
            "- deadline (ISO-8601 UTC timestamp)\n\n"
            "Return all extracted data as a structured JSON summary in the "
            "page notes before finishing."
        )
        try:
            from agents.browser_operator_agent import BrowserOperatorAgent
            browser_agent = BrowserOperatorAgent(save_outputs=False)
            result = browser_agent.run_task(
                prompt=browser_task,
                start_url="https://www.fiverr.com",
            )
            if not result.get("success", False):
                summary_msg = ""
                summary = result.get("summary", {})
                if isinstance(summary, dict):
                    summary_msg = summary.get("message", "")
                elif isinstance(summary, str):
                    summary_msg = summary
                console.print(
                    f"[bold blue][AccountManagementAgent][/bold blue] "
                    f"[red]BrowserOperatorAgent returned success=False. "
                    f"{summary_msg}[/red]"
                )
                return None
            return result
        except Exception as exc:
            console.print(
                f"[bold blue][AccountManagementAgent][/bold blue] "
                f"[red]Browser exception: {exc}[/red]"
            )
            return None

    # ------------------------------------------------------------------
    # Metric parsing
    # ------------------------------------------------------------------

    def _parse_gig_metrics(self, browser_result: dict) -> dict:
        """Extract per-gig metrics from the browser result.

        Uses the LLM to parse whatever structured text was captured by the
        browser operator, falling back to an empty dict if parsing fails.

        Returns
        -------
        dict
            Keys are gig titles (str); values are dicts with:
            ``views`` (int), ``clicks`` (int), ``orders`` (int),
            ``avg_review_score`` (float).
        """
        raw_text = self._extract_text_from_result(browser_result)
        if not raw_text:
            return {}

        prompt = (
            "From the following Fiverr analytics page text, extract gig metrics "
            "for every gig with status 'Active'.\n\n"
            "Return a JSON object where each key is the exact gig title string, "
            "and each value is an object with these keys:\n"
            "  views: integer\n"
            "  clicks: integer\n"
            "  orders: integer\n"
            "  avg_review_score: float\n\n"
            "If a field is not found, use 0 for integers and 0.0 for floats.\n"
            "Return ONLY the JSON object.\n\n"
            f"Page text:\n{raw_text[:4000]}"
        )
        parsed = self.client.ask_json(prompt)
        if not isinstance(parsed, dict) or "parse_error" in parsed:
            console.print(
                "[bold blue][AccountManagementAgent][/bold blue] "
                "[yellow]LLM could not parse gig metrics; using empty dict.[/yellow]"
            )
            return {}

        # Normalise types
        normalised: dict = {}
        for title, metrics in parsed.items():
            if not isinstance(metrics, dict):
                continue
            normalised[str(title)] = {
                "views": int(metrics.get("views", 0) or 0),
                "clicks": int(metrics.get("clicks", 0) or 0),
                "orders": int(metrics.get("orders", 0) or 0),
                "avg_review_score": float(metrics.get("avg_review_score", 0.0) or 0.0),
            }
        return normalised

    def _parse_account_metrics(
        self, browser_result: dict, gig_metrics: dict
    ) -> dict:
        """Extract account-level health metrics from the browser result.

        Falls back to computing avg_review_score from gig_metrics when the
        account-level value is not found in the browser text.

        Returns
        -------
        dict
            Keys: ``avg_review_score`` (float), ``response_rate`` (float),
            ``late_delivery_rate`` (float).
        """
        raw_text = self._extract_text_from_result(browser_result)

        prompt = (
            "From the following Fiverr analytics page text, extract these "
            "account-level metrics:\n"
            "  avg_review_score: float (overall average across all gigs)\n"
            "  response_rate: float (percentage, 0-100)\n"
            "  late_delivery_rate: float (percentage, 0-100)\n\n"
            "Return ONLY a JSON object with those three keys. "
            "Use 0.0 for any metric not found.\n\n"
            f"Page text:\n{raw_text[:4000]}"
        )
        defaults = {
            "avg_review_score": 0.0,
            "response_rate": 0.0,
            "late_delivery_rate": 0.0,
        }
        if raw_text:
            parsed = self.client.ask_json(prompt)
            if isinstance(parsed, dict) and "parse_error" not in parsed:
                defaults["avg_review_score"] = float(
                    parsed.get("avg_review_score", 0.0) or 0.0
                )
                defaults["response_rate"] = float(
                    parsed.get("response_rate", 0.0) or 0.0
                )
                defaults["late_delivery_rate"] = float(
                    parsed.get("late_delivery_rate", 0.0) or 0.0
                )

        # If account-level score is 0 but we have gig data, compute it
        if defaults["avg_review_score"] == 0.0 and gig_metrics:
            scores = [
                m["avg_review_score"]
                for m in gig_metrics.values()
                if m.get("avg_review_score", 0.0) > 0.0
            ]
            if scores:
                defaults["avg_review_score"] = round(
                    sum(scores) / len(scores), 2
                )
        return defaults

    # ------------------------------------------------------------------
    # Deadline checking
    # ------------------------------------------------------------------

    def _check_deadlines(
        self, open_orders: list, browser_result: dict
    ) -> list:
        """Check each active order for an imminent deadline.

        Merges orders from ``open_orders`` (Shared_State) with any orders
        parsed from the browser result. Flags orders whose deadline is
        within DEADLINE_WARNING_HOURS hours of now.

        Returns
        -------
        list[dict]
            Each dict has ``order_id`` (str) and ``deadline_timestamp``
            (UTC ISO-8601 str). Empty list when no orders are due soon

        """
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc + timedelta(hours=DEADLINE_WARNING_HOURS)

        # Try to parse additional orders from browser result
        browser_orders = self._parse_orders_from_result(browser_result)

        # Merge: browser orders may contain fresher data
        all_orders: dict[str, str] = {}  # order_id -> deadline_timestamp

        for order in open_orders:
            if not isinstance(order, dict):
                continue
            oid = str(order.get("order_id", "")).strip()
            ts = str(order.get("deadline_timestamp", "")).strip()
            if oid and ts:
                all_orders[oid] = ts

        for order in browser_orders:
            oid = str(order.get("order_id", "")).strip()
            ts = str(order.get("deadline_timestamp", "")).strip()
            if oid and ts:
                all_orders[oid] = ts  # browser data wins on conflict

        warnings = []
        for order_id, deadline_str in all_orders.items():
            try:
                # Parse ISO-8601; handle both Z and +00:00 suffixes
                deadline_dt = datetime.fromisoformat(
                    deadline_str.replace("Z", "+00:00")
                )
                if deadline_dt.tzinfo is None:
                    deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
                if deadline_dt <= cutoff:
                    warnings.append(
                        {
                            "order_id": order_id,
                            "deadline_timestamp": deadline_dt.astimezone(
                                timezone.utc
                            ).isoformat(),
                        }
                    )
            except (ValueError, TypeError):
                # Unparseable timestamp — skip
                console.print(
                    f"[bold blue][AccountManagementAgent][/bold blue] "
                    f"[yellow]Could not parse deadline for order "
                    f"{order_id}: {deadline_str!r}[/yellow]"
                )
        return warnings

    def _parse_orders_from_result(self, browser_result: dict) -> list:
        """Parse active order data from the browser result using the LLM.

        Returns
        -------
        list[dict]
            Each dict has ``order_id`` (str) and ``deadline_timestamp``
            (UTC ISO-8601 str). Empty list if parsing fails.
        """
        raw_text = self._extract_text_from_result(browser_result)
        if not raw_text:
            return []

        prompt = (
            "From the following Fiverr page text, extract all active orders.\n"
            "Return a JSON array where each item has:\n"
            "  order_id: string\n"
            "  deadline_timestamp: UTC ISO-8601 string\n\n"
            "Return ONLY the JSON array. Use an empty array [] if no orders found.\n\n"
            f"Page text:\n{raw_text[:4000]}"
        )
        parsed = self.client.ask_json(prompt)
        if isinstance(parsed, list):
            return parsed
        # ask_json may return a dict wrapping the array
        if isinstance(parsed, dict) and "parse_error" not in parsed:
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        return []

    # ------------------------------------------------------------------
    # Account health assessment
    # ------------------------------------------------------------------

    def _assess_health(self, metrics: dict) -> tuple[str, list]:
        """Determine account health status and build recommendations.

        Thresholds :
        - avg_review_score >= 4.5
        - response_rate >= 90 (%)
        - late_delivery_rate <= 5 (%)

        Returns
        -------
        tuple[str, list]
            (health_status, recommendations)
            health_status: "healthy", "at_risk", or "critical"
            recommendations: list of strings (non-empty when at_risk/critical)
        """
        review_score = metrics.get("avg_review_score", 0.0)
        response_rate = metrics.get("response_rate", 0.0)
        late_delivery = metrics.get("late_delivery_rate", 0.0)

        missed: list[str] = []
        if review_score < THRESHOLD_REVIEW_SCORE:
            missed.append(
                f"avg_review_score {review_score:.2f} < {THRESHOLD_REVIEW_SCORE}"
            )
        if response_rate < THRESHOLD_RESPONSE_RATE:
            missed.append(
                f"response_rate {response_rate:.1f}% < {THRESHOLD_RESPONSE_RATE}%"
            )
        if late_delivery > THRESHOLD_LATE_DELIVERY:
            missed.append(
                f"late_delivery_rate {late_delivery:.1f}% > {THRESHOLD_LATE_DELIVERY}%"
            )

        missed_count = len(missed)
        if missed_count == 0:
            health = "healthy"
        elif missed_count == 1:
            health = "at_risk"
        else:
            health = "critical"

        recommendations: list[str] = []
        if health in ("at_risk", "critical"):
            recommendations = self._build_recommendations(
                missed, review_score, response_rate, late_delivery
            )
            # Ensure non-empty per
            if not recommendations:
                recommendations = [
                    "Review account metrics and address the flagged threshold(s) "
                    f"to improve account standing: {'; '.join(missed)}"
                ]

        return health, recommendations

    def _build_recommendations(
        self,
        missed: list[str],
        review_score: float,
        response_rate: float,
        late_delivery: float,
    ) -> list[str]:
        """Generate LLM-powered recommendations for missed thresholds.

        Falls back to rule-based recommendations if the LLM call fails.
        """
        prompt = (
            "A Fiverr seller's account has the following issues:\n"
            + "\n".join(f"- {m}" for m in missed)
            + "\n\nGenerate 3-5 concise, actionable recommendations to address "
            "these issues and improve the seller's account standing. "
            "Return ONLY a JSON array of strings. "
            "Each string should be a single recommendation under 100 characters."
        )
        parsed = self.client.ask_json(prompt)
        if isinstance(parsed, list) and all(isinstance(r, str) for r in parsed):
            return [r.strip() for r in parsed if r.strip()]

        # Rule-based fallback
        recs: list[str] = []
        if review_score < THRESHOLD_REVIEW_SCORE:
            recs.append(
                "Request polite feedback from recent buyers to boost review score."
            )
            recs.append(
                "Review delivered work quality and address recurring buyer complaints."
            )
        if response_rate < THRESHOLD_RESPONSE_RATE:
            recs.append(
                "Enable Fiverr notifications and respond to all inbox messages within 1 hour."
            )
            recs.append(
                "Set up an auto-reply message to acknowledge new buyer inquiries quickly."
            )
        if late_delivery > THRESHOLD_LATE_DELIVERY:
            recs.append(
                "Review active orders immediately and request delivery extensions when needed."
            )
            recs.append(
                "Reduce order intake or extend gig delivery times to prevent late deliveries."
            )
        return recs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_text_from_result(self, browser_result: dict) -> str:
        """Flatten the browser result into a single text block for LLM parsing.

        Collects the summary message, step notes, and any extracted content
        captured by the browser operator loop.
        """
        if not isinstance(browser_result, dict):
            return ""

        parts: list[str] = []

        # Summary message
        summary = browser_result.get("summary", {})
        if isinstance(summary, dict):
            msg = summary.get("message", "")
            if msg:
                parts.append(msg)
        elif isinstance(summary, str):
            parts.append(summary)

        # Step results (note / extract_product_data / snapshot actions carry text)
        for step in browser_result.get("steps", []):
            if not isinstance(step, dict):
                continue
            result_data = step.get("result", {})
            if not isinstance(result_data, dict):
                continue
            for key in ("text", "notes", "content", "data", "details"):
                value = result_data.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value)
                elif isinstance(value, dict):
                    parts.append(json.dumps(value))
                elif isinstance(value, list):
                    parts.append(json.dumps(value))

        # Top-level swarm memory notes
        memory = browser_result.get("swarm_memory", {})
        if isinstance(memory, dict):
            notes = memory.get("notes", "")
            if isinstance(notes, str) and notes.strip():
                parts.append(notes)

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Standalone interactive mode
    # ------------------------------------------------------------------

    def run_interactive(self) -> None:
        """Run the agent interactively from the command line.

        Prompts the user for an instruction, executes the account management
        pipeline, and prints the result. Suitable for direct standalone use
        or when launched from ``main.py``.
        """
        from rich.panel import Panel

        console.print(Panel(
            "[bold blue]AccountManagementAgent — Interactive Mode[/bold blue]\n"
            "[dim]Analytics → deadline check → health assessment[/dim]",
            border_style="blue",
        ))

        while True:
            try:
                instruction = input(
                    "\nInstruction (or 'exit'): "
                ).strip()
                if instruction.lower() in {"exit", "quit", "q"}:
                    break
                if not instruction:
                    instruction = (
                        "Check Fiverr account performance and order deadlines"
                    )

                result = self.run({"instruction": instruction})
                data = result.get("data", {})
                console.print(Panel(
                    f"Status:         {result.get('status', 'unknown')}\n"
                    f"Message:        {result.get('message', '')}\n"
                    f"Account health: {data.get('account_health', 'n/a')}\n"
                    f"Gigs monitored: {len(data.get('gig_metrics', {}))}\n"
                    f"Deadline warns: {len(data.get('deadline_warnings', []))}\n"
                    f"Recommendations:{len(data.get('recommendations', []))}",
                    title="Account Management Result",
                    border_style="blue",
                ))
            except KeyboardInterrupt:
                console.print("\n[dim]AccountManagementAgent stopped.[/dim]")
                break


if __name__ == "__main__":
    AccountManagementAgent().run_interactive()
