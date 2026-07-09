"""
agents/browser_operator_agent.py
================================
Simple browser operator agent.

This agent relays a user's plain-language browser task to the backend model,
then executes the model's next safe browser action through BrowserActionRunner.
"""

import os
import sys
from pathlib import Path
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from core import make_client
from tools.browser import AgentBrowser, google_search
from tools.browser_actions import BrowserActionRunner, BrowserPlannerLoop, normalize_url
from tools.output_manager import save_output
from tools.swarm_memory import SwarmMemory

load_dotenv()
console = Console()


BROWSER_OPERATOR_SYSTEM_PROMPT = """
You are BROWSE — a simple browser operator agent.

Your job is to turn the user's plain-language browser request into one safe
browser action at a time. You can search, inspect pages, click buttons, fill
forms, scroll, wait, extract useful page/product information, and stop when the
task is complete.

You MUST only use supported safe actions:
open, snapshot, find, fill, click, wait, scroll, press, extract_product_data,
note, finish.

Rules:
- Always use the current snapshot and user goal before choosing the next action.
- If you do not know a ref, use a hint based on visible labels, roles, text, or placeholders.
- After navigation, click, wait, or page changes, request a fresh snapshot.
- Do not ask to execute Python, JavaScript, shell commands, or unsupported browser actions.
- For passwords or stored secrets, use text_from memory paths instead of copying secret values.
- Finish when the requested browser task is complete or when you need user help.
"""


class BrowserOperatorAgent:
    """A simple prompt-to-browser agent using the safe browser planner loop."""

    def __init__(self, client=None, browser=None, max_steps: int = None, save_outputs: bool = True):
        self.client = client or make_client(
            BROWSER_OPERATOR_SYSTEM_PROMPT,
            "BROWSE-BrowserOperator",
            api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY"),
        )
        self.browser = browser or AgentBrowser
        self.max_steps = max_steps or int(os.getenv("BROWSER_OPERATOR_MAX_STEPS", "8"))
        self.save_outputs = save_outputs

    def run_task(self, prompt: str, start_url: str = "") -> dict:
        """Run a plain-language browser task through the observe-plan-act loop."""
        start_url = normalize_url(start_url) if start_url else ""
        constraints = self._extract_constraints(prompt)
        search_query = self._build_search_query(prompt) if not start_url else ""
        search_results = google_search(search_query) if search_query else []
        memory = SwarmMemory({
            "agent": "BROWSE",
            "user_prompt": prompt,
            "constraints": constraints,
            "start_url": start_url,
            "search_context": {
                "query": search_query,
                "results": search_results,
            } if search_results else {},
            "browser_state": {
                "current_url": "",
                "last_snapshot": "",
                "completed_steps": [],
            },
        })

        runner = BrowserActionRunner(self.browser)
        if search_query and not start_url:
            return self._run_search_task(prompt, search_query, search_results, memory, runner)
        elif start_url:
            runner.run_step({"action": "open", "url": start_url}, memory)

        loop = BrowserPlannerLoop(self.client, runner, max_steps=self.max_steps)
        result = loop.run(
            goal=(
                "Complete this user browser task exactly as requested, using safe browser actions. "
                f"User task: {prompt}"
            ),
            memory=memory,
        )

        cleaned_steps = [self._clean_step_record(step) for step in result.get("steps", [])]
        cleaned_memory = self._clean_memory(result.get("memory", memory.data))
        cleaned_summary = self._summarize_result(result, memory)

        output = {
            "success": result.get("success", False),
            "user_prompt": prompt,
            "summary": cleaned_summary,
            "steps": cleaned_steps,
            "swarm_memory": cleaned_memory,
        }
        if self.save_outputs:
            save_output("browser_operator", "browser_task", output, "json")
        return output

    def _run_search_task(self, prompt: str, search_query: str, search_results: list[dict], memory: SwarmMemory, runner: BrowserActionRunner) -> dict:
        memory.set("search_context.query", search_query)
        memory.set("search_context.results", search_results)
        constraints = memory.get("constraints", {})

        visited = []
        product_candidates = []
        steps = []
        command_log = []

        for result_item in search_results[:5]:
            url = result_item.get("url", "")
            if not url:
                continue
            command_log.append(f"open {url}")
            open_result = runner.run_step({"action": "open", "url": url}, memory)
            steps.append({"step": {"action": "open", "url": url}, "result": open_result})
            if not open_result.get("success"):
                continue

            command_log.append("snapshot")
            snapshot_result = runner.run_step({"action": "snapshot"}, memory)
            steps.append({"step": {"action": "snapshot"}, "result": snapshot_result})

            command_log.append("extract_product_data")
            extracted = runner.run_step({"action": "extract_product_data"}, memory)
            steps.append({"step": {"action": "extract_product_data"}, "result": extracted})
            product = extracted.get("product")
            if isinstance(product, dict):
                product["source_url"] = url
                product["source_score"] = product.get("source_score") or 0
                if not product.get("product_name"):
                    product["product_name"] = result_item.get("title", "")
                if not product.get("description"):
                    product["description"] = result_item.get("snippet", "")
                if not product.get("price"):
                    product["price"] = self._price_from_text(result_item.get("snippet", ""))
                product["matched_constraints"] = self._matched_constraints(constraints, product, result_item)
                product["meets_constraints"] = self._candidate_matches(constraints, product, result_item)
                if self._meaningful_products([product]) and product["meets_constraints"]:
                    product_candidates.append(product)
                    visited.append(url)

            if len(product_candidates) >= 3:
                break

        memory.set("browser_state.completed_steps", steps)
        if product_candidates:
            memory.set("product_candidates", product_candidates)
            self._write_command_log(command_log)
            output = {
                "success": True,
                "user_prompt": prompt,
                "summary": {
                    "status": "completed",
                    "message": "Task completed from DuckDuckGo search results.",
                    "current_url": memory.get("browser_state.current_url", ""),
                    "step_count": len(steps),
                    "last_action": steps[-1]["step"]["action"] if steps else "",
                    "last_error": "",
                    "retry_after_seconds": None,
                    "findings_count": len(product_candidates),
                    "top_finding": product_candidates[0],
                    "search_results_count": len(search_results),
                    "top_search_result": search_results[0] if search_results else None,
                    "visited_urls": visited,
                    "constraints": constraints,
                },
                "steps": [self._clean_step_record(step) for step in steps],
                "swarm_memory": self._clean_memory(memory.data),
                "product_candidates": product_candidates,
                "command_log_path": str(self._write_command_log(command_log)),
            }
        else:
            self._write_command_log(command_log)
            output = {
                "success": False,
                "user_prompt": prompt,
                "summary": {
                    "status": "stopped",
                    "message": "DuckDuckGo search returned results, but no usable product candidates were extracted.",
                    "current_url": memory.get("browser_state.current_url", ""),
                    "step_count": len(steps),
                    "last_action": steps[-1]["step"]["action"] if steps else "",
                    "last_error": "",
                    "retry_after_seconds": None,
                    "findings_count": 0,
                    "top_finding": None,
                    "search_results_count": len(search_results),
                    "top_search_result": search_results[0] if search_results else None,
                    "visited_urls": visited,
                    "constraints": constraints,
                },
                "steps": [self._clean_step_record(step) for step in steps],
                "swarm_memory": self._clean_memory(memory.data),
                "product_candidates": [],
                "command_log_path": str(self._write_command_log(command_log)),
            }

        if self.save_outputs:
            save_output("browser_operator", "browser_task", output, "json")
        return output

    def run_interactive(self):
        console.print(Panel(
            "[bold blue]BROWSE — Browser Operator Agent[/bold blue]\n[dim]Plain prompt in, safe browser actions out[/dim]",
            border_style="blue",
        ))
        while True:
            try:
                prompt = input("\nBrowser task (or 'exit'): ").strip()
                if prompt.lower() in {"exit", "quit", "q"}:
                    break
                start_url = input("Start URL (optional): ").strip()
                result = self.run_task(prompt, start_url)
                console.print(Panel(self._format_cli_result(result), title="Browser Task Result", border_style="blue"))
            except KeyboardInterrupt:
                console.print("\n[dim]Browser operator stopped.[/dim]")
                break

    def _summarize_result(self, result: dict, memory: SwarmMemory) -> dict:
        if result.get("success"):
            status = "completed"
            message = "Task completed."
        elif result.get("error") == "rate_limited":
            status = "rate_limited"
            retry = result.get("retry_after_seconds")
            message = f"Gemini rate limit reached. Retry after about {retry} seconds." if retry else "Gemini rate limit reached. Try again later."
        elif result.get("error") == "planner_error":
            status = "stopped"
            message = "Backend planner returned an error, so the browser loop stopped early."
        else:
            status = "stopped"
            message = result.get("error", "Task stopped before completion.")

        steps = result.get("steps", [])
        last_step = steps[-1] if steps else {}
        product_candidates = self._meaningful_products(memory.get("product_candidates", []))
        search_results = self._meaningful_search_results(memory.get("search_context.results", []))
        return {
            "status": status,
            "message": message,
            "current_url": memory.get("browser_state.current_url", ""),
            "step_count": len(steps),
            "last_action": last_step.get("step", {}).get("action", ""),
            "last_error": last_step.get("result", {}).get("details") or last_step.get("result", {}).get("error", ""),
            "retry_after_seconds": result.get("retry_after_seconds"),
            "findings_count": len(product_candidates),
            "top_finding": product_candidates[0] if product_candidates else None,
            "search_results_count": len(search_results),
            "top_search_result": search_results[0] if search_results else None,
        }

    def _format_cli_result(self, result: dict) -> str:
        summary = result.get("summary", {})
        candidates = result.get("product_candidates", [])
        lines = [
            f"Status: {summary.get('status', 'unknown')}",
            f"Message: {summary.get('message', '')}",
            f"Current URL: {summary.get('current_url', '')}",
            f"Steps used: {summary.get('step_count', 0)}",
        ]
        if candidates:
            lines.append("Top product candidates:")
            for idx, candidate in enumerate(candidates[:3], start=1):
                lines.append(
                    f"  {idx}. {candidate.get('product_name') or 'Unnamed'} | "
                    f"price: {candidate.get('price') or 'n/a'} | "
                    f"source: {candidate.get('source_url') or 'n/a'} | "
                    f"matches: {', '.join(candidate.get('matched_constraints', [])) or 'none'}"
                )
        if summary.get("last_error"):
            lines.append(f"Last error: {summary.get('last_error')}")
        if summary.get("retry_after_seconds"):
            lines.append(f"Retry after: {summary.get('retry_after_seconds')} seconds")
        if result.get("command_log_path"):
            lines.append(f"Command log: {result.get('command_log_path')}")
        return "\n".join(lines)

    def _clean_step_record(self, step_record: dict) -> dict:
        if not isinstance(step_record, dict):
            return step_record
        cleaned = {}
        for key in ("step", "result"):
            value = step_record.get(key)
            if isinstance(value, dict):
                cleaned[key] = self._clean_nested(value)
            elif value not in (None, "", [], {}):
                cleaned[key] = value
        return cleaned

    def _clean_memory(self, memory: dict) -> dict:
        cleaned = self._clean_nested(memory if isinstance(memory, dict) else {})
        browser_state = cleaned.get("browser_state")
        if isinstance(browser_state, dict):
            browser_state.pop("last_snapshot", None)
            browser_state["completed_steps"] = [
                self._clean_step_record(step)
                for step in browser_state.get("completed_steps", [])
                if isinstance(step, dict)
            ]
            browser_state["completed_steps"] = [
                step for step in browser_state["completed_steps"] if step
            ]
            errors = browser_state.get("errors")
            if isinstance(errors, list):
                browser_state["errors"] = [
                    self._clean_nested(error)
                    for error in errors
                    if isinstance(error, dict)
                ]
                browser_state["errors"] = [
                    error for error in browser_state["errors"] if error
                ]
        product_candidates = self._meaningful_products(cleaned.get("product_candidates", []))
        if product_candidates:
            cleaned["product_candidates"] = product_candidates
        else:
            cleaned.pop("product_candidates", None)
        search_context = cleaned.get("search_context")
        if isinstance(search_context, dict):
            search_results = self._meaningful_search_results(search_context.get("results", []))
            search_context["results"] = search_results
            if not search_context.get("query") and not search_results:
                cleaned.pop("search_context", None)
        return cleaned

    def _meaningful_products(self, products) -> list[dict]:
        meaningful = []
        if not isinstance(products, list):
            return meaningful
        for product in products:
            if not isinstance(product, dict):
                continue
            cleaned = self._clean_nested(product)
            if any(
                cleaned.get(field)
                for field in ("product_name", "price", "rating", "description", "source_url")
            ) or int(cleaned.get("order_count", 0) or 0) or int(cleaned.get("review_count", 0) or 0):
                meaningful.append(cleaned)
        return meaningful

    def _meaningful_search_results(self, results) -> list[dict]:
        if not isinstance(results, list):
            return []
        cleaned_results = []
        for item in results:
            if not isinstance(item, dict):
                continue
            cleaned = self._clean_nested(item)
            if cleaned.get("title") and cleaned.get("url"):
                cleaned_results.append(cleaned)
        return cleaned_results

    def _build_search_query(self, prompt: str) -> str:
        lowered = prompt.lower()
        product_signals = [
            "find me",
            "find",
            "looking for",
            "search for",
            "product",
            "laptop",
            "phone",
            "tablet",
            "under $",
            "less than",
            "cheap",
            "buy",
        ]
        if any(signal in lowered for signal in product_signals):
            return prompt.strip()
        return ""

    def _extract_constraints(self, prompt: str) -> dict:
        text = prompt.lower()
        constraints = {
            "keywords": [],
            "price_max": None,
            "price_min": None,
            "raw": prompt,
        }

        if match := re.search(r"(?:under|less than|below|maximum|max(?:imum)?)\s*\$?\s*(\d+(?:\.\d+)?)", text):
            constraints["price_max"] = float(match.group(1))
        if match := re.search(r"(?:at least|minimum|min(?:imum)?|over|above|more than)\s*\$?\s*(\d+(?:\.\d+)?)", text):
            constraints["price_min"] = float(match.group(1))

        cleaned = re.sub(r"(?:under|less than|below|maximum|max(?:imum)?|at least|minimum|min(?:imum)?|over|above|more than)\s*\$?\s*\d+(?:\.\d+)?", " ", text)
        cleaned = re.sub(r"[^\w\s$.-]", " ", cleaned)
        tokens = [token for token in cleaned.split() if len(token) > 2 and token not in {"find", "show", "give", "me", "the", "for", "with", "and", "that", "this", "they", "should", "cost", "under", "less", "then", "than"}]
        constraints["keywords"] = self._dedupe_preserve_order(tokens)
        return constraints

    def _candidate_matches(self, constraints: dict, product: dict, search_result: dict) -> bool:
        if not constraints:
            return True
        text = " ".join(
            str(part)
            for part in [
                product.get("product_name", ""),
                product.get("description", ""),
                product.get("price", ""),
                search_result.get("title", ""),
                search_result.get("snippet", ""),
            ]
        ).lower()

        price = self._safe_float(product.get("price"))
        if constraints.get("price_max") is not None and price and price > constraints["price_max"]:
            return False
        if constraints.get("price_min") is not None and price and price < constraints["price_min"]:
            return False

        keywords = constraints.get("keywords", [])
        if not keywords:
            return True

        matches = 0
        for keyword in keywords:
            if keyword.lower() in text:
                matches += 1
        threshold = 1 if len(keywords) <= 2 else max(2, len(keywords) // 3)
        return matches >= threshold

    def _matched_constraints(self, constraints: dict, product: dict, search_result: dict) -> list[str]:
        matched = []
        text = " ".join(
            str(part)
            for part in [
                product.get("product_name", ""),
                product.get("description", ""),
                search_result.get("title", ""),
                search_result.get("snippet", ""),
            ]
        ).lower()

        price = self._safe_float(product.get("price"))
        if constraints.get("price_max") is not None and price and price <= constraints["price_max"]:
            matched.append(f"price <= {constraints['price_max']}")
        if constraints.get("price_min") is not None and price and price >= constraints["price_min"]:
            matched.append(f"price >= {constraints['price_min']}")
        for keyword in constraints.get("keywords", []):
            if keyword.lower() in text:
                matched.append(keyword)
        return self._dedupe_preserve_order(matched)

    def _dedupe_preserve_order(self, items: list[str]) -> list[str]:
        seen = set()
        out = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    def _write_command_log(self, commands: list[str]) -> Path:
        target = Path("rag/browser_operator_commands.txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not commands:
            commands = ["open <duckduckgo search>", "snapshot", "extract_product_data"]
        target.write_text("\n".join(commands) + "\n", encoding="utf-8")
        return target

    def _price_from_text(self, text: str) -> str:
        match = re.search(r"(?:\$|USD\s*)\s*([0-9]+(?:\.[0-9]{1,2})?)", text or "", re.I)
        return match.group(1) if match else ""

    def _safe_float(self, value) -> float:
        try:
            return float(str(value).replace("$", "").strip())
        except Exception:
            return 0.0

    def _clean_nested(self, value):
        if isinstance(value, dict):
            cleaned = {}
            for key, item in value.items():
                cleaned_item = self._clean_nested(item)
                if cleaned_item in (None, "", [], {}):
                    continue
                if key == "source_score" and cleaned_item == 0:
                    continue
                cleaned[key] = cleaned_item
            return cleaned
        if isinstance(value, list):
            cleaned_list = []
            for item in value:
                cleaned_item = self._clean_nested(item)
                if cleaned_item in (None, "", [], {}):
                    continue
                cleaned_list.append(cleaned_item)
            return cleaned_list
        return value


if __name__ == "__main__":
    BrowserOperatorAgent().run_interactive()
