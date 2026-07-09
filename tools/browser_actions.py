"""
tools/browser_actions.py
========================
Safe observe-plan-act browser automation primitives.

Agents may generate action dictionaries, but this runner only executes approved
browser operations. That gives agents flexible navigation without arbitrary code
execution.
"""

import re
from typing import Any

from tools.dom_finders import find_ref_in_snapshot
from tools.swarm_memory import SwarmMemory


SAFE_ACTIONS = {
    "open",
    "snapshot",
    "find",
    "fill",
    "click",
    "wait",
    "scroll",
    "press",
    "extract_product_data",
    "note",
    "finish",
}

SAFE_KEYS = {"Enter", "Tab", "Escape", "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"}
MAX_WAIT_MS = 5000
SNAPSHOT_PROMPT_CHARS = int(__import__("os").getenv("BROWSER_PLANNER_SNAPSHOT_CHARS", "1800"))


def extract_product_data_from_snapshot(snapshot: str) -> dict[str, Any]:
    """Extract common supplier product signals from accessibility snapshot text."""
    text = snapshot or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    product_name = ""
    for line in lines:
        if re.search(r"\[(h1|h2|h3|heading)", line, re.I):
            quoted = re.search(r'"([^"]{4,120})"', line)
            if quoted:
                product_name = quoted.group(1).strip()
                break

    if not product_name:
        quoted = re.search(r'"([^"]{4,120})"', text)
        product_name = quoted.group(1).strip() if quoted else ""

    price_match = re.search(r"(?:\$|USD\s*)\s*([0-9]+(?:\.[0-9]{1,2})?)", text, re.I)
    rating_match = re.search(r"([0-5](?:\.[0-9])?)\s*(?:stars?|/5|rating)", text, re.I)
    order_match = re.search(r"([0-9][0-9,\.]*)\s*(?:orders?|sold|buys?|purchases?)", text, re.I)
    review_match = re.search(r"([0-9][0-9,\.]*)\s*(?:reviews?|comments?)", text, re.I)

    return {
        "product_name": product_name,
        "price": price_match.group(1) if price_match else "",
        "rating": rating_match.group(1) if rating_match else "",
        "order_count": _parse_count(order_match.group(1)) if order_match else 0,
        "review_count": _parse_count(review_match.group(1)) if review_match else 0,
        "description": text[:1200],
        "raw_snapshot_excerpt": text[:2000],
    }


def score_product_candidate(candidate: dict[str, Any]) -> float:
    """Score product candidates by balanced demand signals, not rating alone."""
    rating = _safe_float(candidate.get("rating"))
    orders = int(candidate.get("order_count") or 0)
    reviews = int(candidate.get("review_count") or 0)
    price = _safe_float(candidate.get("price"))

    volume_score = min(10.0, (orders / 1000.0) * 5.0 + (reviews / 250.0) * 2.0)
    rating_score = max(0.0, min(10.0, (rating - 3.5) * 6.0)) if rating else 0.0
    margin_signal = 2.0 if 0 < price <= 30 else 1.0 if price <= 60 else 0.0
    return round(volume_score + rating_score + margin_signal, 2)


class BrowserActionRunner:
    """Execute validated browser action steps against an AgentBrowser-like object."""

    def __init__(self, browser: Any):
        self.browser = browser
        self.last_snapshot = ""
        self.refs: dict[str, str] = {}

    def run_step(self, step: dict[str, Any], memory: SwarmMemory | None = None) -> dict[str, Any]:
        if not isinstance(step, dict):
            return {"success": False, "error": "invalid_step"}

        action = str(step.get("action", "")).strip().lower()
        if action not in SAFE_ACTIONS:
            return {"success": False, "error": "action_not_allowed", "action": action}

        memory = memory or SwarmMemory()

        if action == "open":
            url = normalize_url(step.get("url", ""))
            if not url:
                return {"success": False, "error": "unsafe_url"}
            page = self.browser.fetch_page(url)
            self._remember_page(page, memory)
            return {"success": page.get("status") != "error", "action": action, "url": url}

        if action == "snapshot":
            page = self.browser.snapshot()
            self._remember_page(page, memory)
            return {"success": True, "action": action, "snapshot_excerpt": self.last_snapshot[:500]}

        if action == "find":
            ref = self._resolve_ref(step)
            if not ref:
                return {"success": False, "error": "ref_not_found", "hint": step.get("hint", "")}
            key = step.get("key") or step.get("hint") or ref
            self.refs[str(key)] = ref
            memory.set(f"browser_refs.{key}", ref)
            return {"success": True, "action": action, "ref": ref, "key": key}

        if action == "fill":
            ref = self._resolve_ref(step)
            if not ref:
                return {"success": False, "error": "ref_not_found", "hint": step.get("hint", "")}
            text = step.get("text")
            if text is None and step.get("text_from"):
                text = memory.get(str(step.get("text_from")), "")
            ok = self.browser.type_text(ref, str(text or ""))
            return {"success": bool(ok), "action": action, "ref": ref}

        if action == "click":
            ref = self._resolve_ref(step)
            if not ref:
                return {"success": False, "error": "ref_not_found", "hint": step.get("hint", "")}
            ok = self.browser.click(ref)
            return {"success": bool(ok), "action": action, "ref": ref}

        if action == "wait":
            ms = max(0, min(int(step.get("ms", 1000)), MAX_WAIT_MS))
            ok = self.browser.wait(ms)
            return {"success": bool(ok), "action": action, "ms": ms}

        if action == "scroll":
            direction = step.get("direction", "down")
            amount = int(step.get("amount", 500))
            ok = self.browser.scroll(direction, amount)
            return {"success": bool(ok), "action": action}

        if action == "press":
            key = str(step.get("key", "Enter"))
            if key not in SAFE_KEYS:
                return {"success": False, "error": "key_not_allowed", "key": key}
            ok = self.browser.press(key)
            return {"success": bool(ok), "action": action, "key": key}

        if action == "extract_product_data":
            product = extract_product_data_from_snapshot(self.last_snapshot)
            product["source_url"] = memory.get("browser_state.current_url", "")
            product["source_score"] = score_product_candidate(product)
            memory.append("product_candidates", product)
            return {"success": True, "action": action, "product": product}

        if action == "note":
            memory.append("browser_notes", step.get("text", ""))
            return {"success": True, "action": action}

        return {"success": True, "action": "finish", "finished": True}

    def _remember_page(self, page: dict[str, Any], memory: SwarmMemory) -> None:
        self.last_snapshot = page.get("text") or page.get("snapshot") or ""
        if page.get("url"):
            memory.set("browser_state.current_url", page.get("url"))
        memory.set("browser_state.last_snapshot", self.last_snapshot)

    def _resolve_ref(self, step: dict[str, Any]) -> str | None:
        explicit_ref = step.get("ref")
        if explicit_ref:
            return str(explicit_ref)
        ref_key = step.get("ref_key")
        if ref_key and str(ref_key) in self.refs:
            return self.refs[str(ref_key)]
        hint = step.get("hint")
        if hint:
            return find_ref_in_snapshot(self.last_snapshot, str(hint))
        return None


# How many consecutive identical action signatures trigger a stuck-warning.
_LOOP_DETECT_WINDOW = 3


def _action_signature(step: dict) -> str:
    """A short string that uniquely identifies the *intent* of an action.

    We intentionally ignore fields like 'ref' and 'text' that the local LLM
    may vary on each turn even though it is repeating the same logical action
    (e.g., opening the same URL over and over with different ref values).
    """
    action = step.get("action", "")
    # For navigation actions the unique key is the target URL.
    url = step.get("url", "")
    # For key-press actions the unique key is the key name.
    key = step.get("key", "")
    # For interaction actions (find/fill/click) include the hint but NOT the ref,
    # since refs are dynamic and the hint captures the intended target.
    hint = step.get("hint", "")
    return f"{action}|{url}|{key}|{hint}"


class BrowserPlannerLoop:
    """Ask an AI client for one safe browser action at a time and execute it.

    Improvements over the baseline:
    - Anti-loop detection: tracks the last _LOOP_DETECT_WINDOW action signatures
      and injects a WARNING hint into the LLM prompt when repetition is detected.
    - Enhanced prompt: explicit finish / extract_product_data guidance so smaller
      local models can terminate correctly instead of looping on 'open'.
    """

    def __init__(self, client: Any, runner: BrowserActionRunner, max_steps: int = 20):
        self.client = client
        self.runner = runner
        self.max_steps = max_steps
        self._recent_signatures: list[str] = []  # rolling window for loop detection

    # ── public ────────────────────────────────────────────────────────────

    def run(self, goal: str, memory: SwarmMemory | None = None) -> dict[str, Any]:
        memory = memory or SwarmMemory({"goal": goal})
        steps = []
        self._recent_signatures.clear()

        for _ in range(self.max_steps):
            # Determine if the planner appears stuck before asking for the next step
            stuck_hint = self._stuck_hint()

            step = self._next_step(goal, memory, stuck_hint=stuck_hint)
            planner_error = _planner_error(step)
            if planner_error:
                error_type = "rate_limited" if step.get("rate_limited") else "planner_error"
                result = {"success": False, "error": error_type, "details": planner_error}
                if step.get("retry_after_seconds"):
                    result["retry_after_seconds"] = step.get("retry_after_seconds")
                steps.append({"step": {"action": "planner_error"}, "result": result})
                memory.append("browser_state.errors", result)
                return {
                    "success": False,
                    "error": error_type,
                    "retry_after_seconds": result.get("retry_after_seconds"),
                    "steps": steps,
                    "memory": memory.data,
                }

            # Track action signature for loop detection
            sig = _action_signature(step)
            self._recent_signatures.append(sig)
            if len(self._recent_signatures) > _LOOP_DETECT_WINDOW:
                self._recent_signatures.pop(0)

            result = self.runner.run_step(step, memory)
            steps.append({"step": step, "result": result})
            memory.append("browser_state.completed_steps", {"step": step, "result": result})

            if step.get("action") == "finish" or result.get("finished"):
                return {"success": True, "steps": steps, "memory": memory.data}
            if not result.get("success"):
                memory.append("browser_state.errors", result)

        return {"success": False, "error": "max_steps_reached", "steps": steps, "memory": memory.data}

    # ── private helpers ───────────────────────────────────────────────────

    def _stuck_hint(self) -> str:
        """Return a warning string when the last N actions are all identical."""
        if (
            len(self._recent_signatures) >= _LOOP_DETECT_WINDOW
            and len(set(self._recent_signatures)) == 1
        ):
            repeated = self._recent_signatures[0].split("|")[0]  # just the action name
            return (
                f"\n\n⚠️  WARNING: You have repeated the '{repeated}' action "
                f"{_LOOP_DETECT_WINDOW} times in a row without making progress. "
                "Do NOT repeat this action again. "
                "If you already have the page content in the snapshot, use "
                "'extract_product_data' to capture it, then 'finish'. "
                "If the page failed to load, use 'snapshot' to refresh the view. "
                "If the goal is already achieved, use 'finish' immediately."
            )
        return ""

    def _next_step(self, goal: str, memory: SwarmMemory, stuck_hint: str = "") -> dict[str, Any]:
        current_url = memory.get("browser_state.current_url", "")
        snapshot = memory.get("browser_state.last_snapshot", "")[:SNAPSHOT_PROMPT_CHARS]
        known_data = _redact_sensitive(memory.data)

        prompt = f"""You are controlling a browser through a safe action API.

Goal: {goal}

Current URL: {current_url}
Current snapshot (accessibility tree of the visible page):
{snapshot}

Known data collected so far:
{known_data}
{stuck_hint}

Decision rules — follow these IN ORDER:
1. If the GOAL is fully achieved based on the snapshot or known data → return {{"action": "finish"}}.
2. If the page snapshot already contains the product/information you need → return {{"action": "extract_product_data"}} to save it, then on the next step return {{"action": "finish"}}.
3. If you need to navigate to a URL you have NOT yet visited → return {{"action": "open", "url": "<url>"}}.
4. If you need to interact with a visible element (button, input) → use find / fill / click / press.
5. If you need to see the current page state → use {{"action": "snapshot"}}.
6. Only use 'open' on a URL you have NOT opened in this session. If you are already on the correct page, do NOT open it again.

Return EXACTLY ONE JSON object. Choose only from these actions:
open, snapshot, find, fill, click, wait, scroll, press, extract_product_data, note, finish.

For stored credentials/secrets use: "text_from": "dot.path.in.memory" — never copy secret values into "text".
Do not invent unsupported actions."""

        schema_hint = '{"action": "<action_name>", "url": "<url_if_open>", "ref": "<ref_if_needed>", "text": "<text_if_fill>"}'
        return self.client.ask_json(prompt, schema_hint=schema_hint)


def normalize_url(url: str) -> str:
    """Return a safe browser URL, adding https:// when the user omits a scheme."""
    if not isinstance(url, str):
        return ""
    cleaned = url.strip()
    if not cleaned:
        return ""
    if cleaned.startswith(("https://", "http://")):
        return cleaned
    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$", cleaned):
        return f"https://{cleaned}"
    return ""


def _planner_error(step: Any) -> str:
    if not isinstance(step, dict):
        return "planner returned a non-object response"
    if step.get("parse_error"):
        return str(step.get("raw_response", "planner response was not valid JSON"))[:1000]
    action = str(step.get("action", "")).strip().lower()
    if not action and step.get("raw_response"):
        return str(step.get("raw_response"))[:1000]
    return ""


def _parse_count(value: str) -> int:
    normalized = value.replace(",", "").strip().lower()
    if normalized.endswith("k"):
        return int(float(normalized[:-1]) * 1000)
    if normalized.endswith("m"):
        return int(float(normalized[:-1]) * 1000000)
    return int(float(normalized))


def _safe_float(value: Any) -> float:
    try:
        return float(str(value).replace("$", "").strip())
    except Exception:
        return 0.0


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(secret in lowered for secret in ("password", "token", "secret", "key")) and item:
                redacted[key] = "[stored: use text_from path]"
            else:
                redacted[key] = _redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    return value
