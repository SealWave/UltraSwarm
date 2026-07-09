"""
agents/fiverr/fiverr_manager_agent.py
=======================================
Fiverr_Manager — central orchestrator for the Fiverr automation sub-swarm.

Accepts a high-level user goal, decomposes it into an ordered list of
sub-tasks via the LLM, delegates each sub-task to the appropriate Fiverr
sub-agent, coordinates shared state, and returns a synthesised result.

Pattern: standalone class (same style as agents/external/web_research_agent.py),
NOT a subclass of BaseAgent. LLM access via core.make_client().

Usage:
    from agents.fiverr.fiverr_manager_agent import FiverrManager

    manager = FiverrManager()
    result = manager.run({"goal": "Create a lead-generation gig and notify me"})
"""

import json
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from rich.console import Console

from core import make_client
from agents.fiverr.shared.state import Shared_State

console = Console()

# ── System prompt ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are the Fiverr_Manager — the domain-level orchestrator for a Fiverr
freelance-account automation system.

Your responsibilities:
1. Receive a high-level goal from the user.
2. Decompose the goal into an ordered list of concrete sub-tasks, each
   mapped to one of the five Fiverr sub-agents available in your registry.
3. Delegate sub-tasks in order, passing shared context between steps.
4. Handle failures: retry non-critical tasks, halt on critical failures.
5. Return a clear summary of the final result.

Available sub-agent names (for task routing):
  - gig_creation_agent
  - scraping_lead_gen_agent
  - account_management_agent
  - inbox_communication_agent
  - notification_agent

CRITICAL RULES:
- Never skip the decomposition step.
- Always route to a named sub-agent from the list above.
- Keep instructions precise and self-contained per sub-task.
"""

# ── Sub-task decomposition schema hint ────────────────────────────────────
_SUBTASK_SCHEMA = """
[
  {
    "task_id": "task_1",
    "agent": "gig_creation_agent",
    "instruction": "Describe what the agent must do in one sentence.",
    "required_output": {"key": "expected value or structure"},
    "critical": true
  }
]
"""


class FiverrManager:
    """
    Central orchestrator for the Fiverr automation sub-swarm.

    Attributes
    ----------
    name : str
        Agent identifier used in registries and logs.
    role : str
        Role classification for the UltraSwarm registry.
    description : str
        Human-readable capability summary.
    skills : list[str]
        Skill IDs this agent provides.
    """

    name = "fiverr_manager"
    role = "manager"
    description = (
        "Domain-level orchestrator for all Fiverr automation. Accepts a user "
        "goal, decomposes it into sub-tasks, delegates to specialised Fiverr "
        "sub-agents (gig creation, scraping/lead-gen, account management, "
        "inbox communication, notifications), and returns a synthesised result."
    )
    skills = [
        "fiverr_orchestration_skill",
        "plan_review_skill",
    ]

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        # Unique session ID for this manager instance
        self.session_id: str = str(uuid.uuid4())

        # Centralised state store shared with all sub-agents
        self.shared_state: Shared_State = Shared_State(session_id=self.session_id)

        # LLM client (same factory used by every other agent in the system)
        self.client = make_client(SYSTEM_PROMPT, "FIVERR-MANAGER")

        console.print(
            f"[bold cyan][Fiverr_Manager][/bold cyan] "
            f"Session started — id={self.session_id}"
        )

        # Build the sub-agent registry (populates shared_state.agent_registry)
        # and _agent_instances (live objects used for delegation in _execute_plan)
        registry_result = self._build_agent_registry()
        if registry_result is not None:
            # _build_agent_registry returns an error dict on failure
            console.print(
                "[bold cyan][Fiverr_Manager][/bold cyan] "
                "[red]Agent registry build failed — see result for details.[/red]"
            )
            # Store the error so callers can inspect it; run() will surface it
            self._init_error: dict | None = registry_result
        else:
            self._init_error = None

        # Register with UltraSwarm top-level orchestrator if available
        try:
            from agents.managers.orchestrator_agent import OrchestratorAgent  # noqa: F401
            # The orchestrator discovers Fiverr agents via ALL_FIVERR_AGENTS in
            # agents/fiverr/__init__.py (task 4.5); no direct injection needed here.
            console.print(
                "[bold cyan][Fiverr_Manager][/bold cyan] "
                "UltraSwarm_Orchestrator detected — Fiverr agents are discoverable."
            )
        except ImportError:
            console.print(
                "[bold cyan][Fiverr_Manager][/bold cyan] "
                "[dim]UltraSwarm_Orchestrator not available — running standalone.[/dim]"
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_metadata(self) -> dict:
        """Return agent metadata compatible with the BaseAgent registry interface.

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
        """Main orchestration entry-point.

        Parameters
        ----------
        input_data : dict
            Must contain ``"goal"`` (non-empty string).  Optional keys:
            ``"context"`` (dict), ``"max_retries"`` (int, default 2).

        Returns
        -------
        dict
            AgentResult-compatible dict with keys:
            ``status``, ``message``, ``data``, ``metadata``.
        """
        # ── Propagate init errors immediately ──────────────────────────
        if self._init_error is not None:
            return self._init_error

        # ── Task 2.2 — Goal validation ──────────────────────────────────
        goal = input_data.get("goal", None)

        if goal is None:
            console.print(
                "[bold cyan][Fiverr_Manager][/bold cyan] "
                "[red]Rejected: 'goal' key missing from input_data.[/red]"
            )
            return {
                "status": "error",
                "message": (
                    "Invalid input: 'goal' key is missing from input_data. "
                    "Please provide a non-empty goal string, e.g. "
                    '{"goal": "Create a lead-generation gig"}.'
                ),
                "data": {},
                "metadata": {"session_id": self.session_id},
            }

        if not isinstance(goal, str) or not goal.strip():
            console.print(
                "[bold cyan][Fiverr_Manager][/bold cyan] "
                "[red]Rejected: 'goal' is empty or not a string.[/red]"
            )
            return {
                "status": "error",
                "message": (
                    "Invalid input: 'goal' must be a non-empty string. "
                    "Received: "
                    + repr(goal)
                ),
                "data": {},
                "metadata": {"session_id": self.session_id},
            }

        goal = goal.strip()
        console.print(
            f"[bold cyan][Fiverr_Manager][/bold cyan] "
            f"New goal received: {goal}"
        )

        # ── Task 2.3 — Sub-task decomposition ──────────────────────────
        sub_tasks = self._decompose_goal(goal)
        if sub_tasks is None:
            return {
                "status": "error",
                "message": (
                    "Sub-task decomposition failed: the LLM did not return a "
                    "valid plan. Please try rephrasing your goal."
                ),
                "data": {},
                "metadata": {
                    "session_id": self.session_id,
                    "change_log": self.shared_state.change_log,
                },
            }

        console.print(
            f"[bold cyan][Fiverr_Manager][/bold cyan] "
            f"Plan decomposed into {len(sub_tasks)} sub-task(s)."
        )

        # Store the decomposed plan in shared state (req 1.3 / 1.4)
        self.shared_state.set("current_plan", sub_tasks)

        # ── Stub: _execute_plan (tasks 2.4-2.9 will flesh this out) ────
        plan_result = self._execute_plan(sub_tasks, goal)
        return plan_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_agent_registry(self) -> dict | None:
        """Import all five Fiverr sub-agents, call get_metadata() on each,
        and store results in ``shared_state.agent_registry``.  Also populates
        ``self._agent_instances`` with live objects for delegation.

        Returns
        -------
        None
            On success.
        dict
            An error AgentResult dict if any sub-agent fails to register.
        """
        sub_agent_imports = [
            ("agents.fiverr.gig_creation_agent",     "GigCreationAgent"),
            ("agents.fiverr.scraping_lead_gen_agent", "ScrapingLeadGenAgent"),
            ("agents.fiverr.account_management_agent","AccountManagementAgent"),
            ("agents.fiverr.inbox_communication_agent","InboxCommunicationAgent"),
            ("agents.fiverr.notification_agent",      "NotificationAgent"),
        ]

        registry: dict = {}
        # Map agent name → live instance, used by _execute_plan for delegation.
        self._agent_instances: dict = {}

        for module_path, class_name in sub_agent_imports:
            try:
                import importlib
                module = importlib.import_module(module_path)
                agent_class = getattr(module, class_name)
                instance = agent_class()
                metadata = instance.get_metadata()
                registry[metadata["name"]] = metadata
                self._agent_instances[metadata["name"]] = instance
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"Registered sub-agent: {metadata['name']}"
                )
            except Exception as exc:
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"[red]Failed to register {class_name}: {exc}[/red]"
                )
                return {
                    "status": "error",
                    "message": (
                        f"Agent registry initialisation failed: "
                        f"{class_name} could not be loaded. "
                        f"Reason: {exc}"
                    ),
                    "data": {"failed_agent": class_name, "error": str(exc)},
                    "metadata": {"session_id": self.session_id},
                }

        # Persist registry in shared state
        self.shared_state.agent_registry = registry
        console.print(
            f"[bold cyan][Fiverr_Manager][/bold cyan] "
            f"Agent registry complete — {len(registry)} agent(s) registered."
        )
        return None  # success

    def _decompose_goal(self, goal: str) -> list | None:
        """Use the LLM to parse *goal* into an ordered list of sub-tasks.

        Each sub-task dict must have:
        - ``task_id``        (str)  — unique identifier, e.g. "task_1"
        - ``agent``          (str)  — target sub-agent name
        - ``instruction``    (str)  — what the agent must do
        - ``required_output``(dict|str) — expected output structure
        - ``critical``       (bool) — whether failure should halt execution

        Parameters
        ----------
        goal : str
            The user's high-level goal string.

        Returns
        -------
        list
            Ordered list of sub-task dicts.
        None
            If the LLM response could not be parsed or produced an invalid plan.
        """
        console.print(
            "[bold cyan][Fiverr_Manager][/bold cyan] "
            "Decomposing goal into sub-tasks…"
        )

        # Include the agent registry so the LLM knows which agents exist
        registry_summary = "\n".join(
            f"  - {name}: {meta.get('description', '')}"
            for name, meta in self.shared_state.agent_registry.items()
        ) or "  (no sub-agents registered yet)"

        prompt = (
            f"User goal: {goal}\n\n"
            f"Available Fiverr sub-agents:\n{registry_summary}\n\n"
            f"Decompose this goal into an ordered list of sub-tasks. "
            f"Each sub-task must be assigned to one of the sub-agents listed above. "
            f"Return ONLY a JSON array matching this schema:\n{_SUBTASK_SCHEMA}"
        )

        raw = self.client.ask_json(prompt)

        # ask_json returns a dict on parse failure, a list on success
        if isinstance(raw, list):
            sub_tasks = raw
        elif isinstance(raw, dict) and "parse_error" in raw:
            console.print(
                "[bold cyan][Fiverr_Manager][/bold cyan] "
                "[red]LLM returned unparseable JSON for sub-task decomposition.[/red]"
            )
            return None
        else:
            # ask_json might return a dict wrapping a list (e.g. {"tasks": [...]})
            # Try common wrapper keys before giving up
            for key in ("tasks", "subtasks", "sub_tasks", "plan"):
                if key in raw and isinstance(raw[key], list):
                    sub_tasks = raw[key]
                    break
            else:
                console.print(
                    "[bold cyan][Fiverr_Manager][/bold cyan] "
                    "[red]Unexpected decomposition structure from LLM.[/red]"
                )
                return None

        # Validate each sub-task has required fields
        required_fields = {"task_id", "instruction", "required_output", "critical"}
        validated: list = []
        for i, task in enumerate(sub_tasks):
            if not isinstance(task, dict):
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"[yellow]Warning: sub-task {i} is not a dict — skipping.[/yellow]"
                )
                continue
            missing = required_fields - task.keys()
            if missing:
                # Fill in safe defaults rather than discarding valid partial tasks
                if "task_id" not in task:
                    task["task_id"] = f"task_{i + 1}"
                if "instruction" not in task:
                    task["instruction"] = "(no instruction provided)"
                if "required_output" not in task:
                    task["required_output"] = {}
                if "critical" not in task:
                    task["critical"] = False
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"[yellow]Warning: sub-task {task['task_id']} had missing fields "
                    f"{missing!r} — defaults applied.[/yellow]"
                )
            validated.append(task)

        if not validated:
            console.print(
                "[bold cyan][Fiverr_Manager][/bold cyan] "
                "[red]Decomposition produced zero valid sub-tasks.[/red]"
            )
            return None

        console.print(
            f"[bold cyan][Fiverr_Manager][/bold cyan] "
            f"Decomposition complete — {len(validated)} sub-task(s) validated."
        )
        return validated

    def _execute_plan(self, sub_tasks: list, goal: str) -> dict:
        """Execute the decomposed plan by delegating each sub-task to the
        appropriate Fiverr sub-agent.

        Implements tasks 2.4-2.8:
        - Sub-agent delegation with shared-state coordination (2.4)
        - Retry logic for non-critical task failures — up to 2 retries (2.5)
        - Immediate halt on critical task failure (2.6)
        - JSONL audit logging per attempt to agent_workspace/ (2.7)
        - Rich console logging for all state transitions (2.8)

        Parameters
        ----------
        sub_tasks : list
            Validated, ordered sub-task dicts from ``_decompose_goal``.
        goal : str
            The original user goal, forwarded to ``_synthesize_output``.

        Returns
        -------
        dict
            AgentResult-compatible dict with keys:
            ``status``, ``message``, ``data``, ``metadata``.
        """
        # ── Task 2.7: prepare JSONL session log ────────────────────────
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "agent_workspace",
        )
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"fiverr_session_{self.session_id}.log")

        def _write_log_entry(agent_name: str, task_description: str, outcome: str,
                             extra: str | None = None) -> None:
            """Append one JSONL entry to the session log file."""
            entry: dict = {
                "timestamp": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "agent_name": agent_name,
                "task_description": task_description,
                "outcome": outcome,
            }
            if extra:
                entry["detail"] = extra
            try:
                with open(log_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry) + "\n")
            except OSError as log_err:
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"[yellow]Warning: could not write to session log: {log_err}[/yellow]"
                )

        max_retries = 2
        task_results: list = []
        halted_on_critical = False

        # ── Task 2.8: log goal receipt ──────────────────────────────────
        console.print(
            f"[bold cyan][Fiverr_Manager][/bold cyan] "
            f"Executing plan — {len(sub_tasks)} sub-task(s) for goal: {goal}"
        )

        for sub_task in sub_tasks:
            task_id = sub_task.get("task_id", "unknown")
            agent_name = sub_task.get("agent", "")
            instruction = sub_task.get("instruction", "(no instruction)")
            is_critical = bool(sub_task.get("critical", False))

            # ── Task 2.4: look up agent instance ───────────────────────
            if agent_name not in self._agent_instances:
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"[yellow]Warning: sub-agent '{agent_name}' not found in registry "
                    f"for task {task_id} — skipping.[/yellow]"
                )
                task_results.append({
                    "task_id": task_id,
                    "agent": agent_name,
                    "status": "skipped",
                    "message": f"Agent '{agent_name}' not available.",
                })
                _write_log_entry(agent_name, instruction, "error",
                                 f"Agent '{agent_name}' not found in registry — skipped.")
                continue

            agent = self._agent_instances[agent_name]

            # ── Task 2.8: log sub-task start / status → in_progress ────
            console.print(
                f"[bold cyan][Fiverr_Manager][/bold cyan] "
                f"Starting task {task_id} → {agent_name}: {instruction}"
            )
            console.print(
                f"[bold cyan][Fiverr_Manager][/bold cyan] "
                f"Status transition: {task_id} pending → in_progress"
            )

            # ── Task 2.4: build agent_input with shared-state context ──
            agent_input = {
                "task_id": task_id,
                "instruction": instruction,
                "required_output": sub_task.get("required_output", {}),
                "context": {
                    **self.shared_state.to_context_dict(),
                    "agent_registry": self.shared_state.agent_registry,
                },
            }

            # ── Tasks 2.5 / 2.6: execute with retry / critical logic ──
            last_result: dict = {}
            attempt = 0
            succeeded = False

            while attempt <= max_retries:
                try:
                    last_result = agent.run(agent_input)
                except Exception as exc:
                    tb_str = traceback.format_exc()
                    console.print(
                        f"[bold cyan][Fiverr_Manager][/bold cyan] "
                        f"[red]Exception in {agent_name} on task {task_id} "
                        f"(attempt {attempt + 1}): {exc}[/red]"
                    )
                    _write_log_entry(agent_name, instruction, "error", tb_str)
                    last_result = {
                        "status": "error",
                        "success": False,
                        "message": str(exc),
                        "data": {},
                        "context_for_next": {},
                    }

                # Normalise: both ExecutionResult-style (status key) and
                # AgentResult-style (success key) are accepted.
                result_status = last_result.get("status", "")
                result_success = last_result.get("success", result_status == "success")
                is_error = (result_status == "error") or (result_success is False)

                if not is_error:
                    succeeded = True
                    break

                # ── Task 2.7: log every non-exception failed attempt ────
                # (Exception attempts are already logged inside the except
                #  block above; this covers non-exception error results.)
                _write_log_entry(
                    agent_name,
                    instruction,
                    "error",
                    f"Attempt {attempt + 1}: "
                    + last_result.get("message", "(no message)"),
                )

                # ── Task 2.6: critical failure → halt immediately ───────
                if is_critical:
                    console.print(
                        f"[bold cyan][Fiverr_Manager][/bold cyan] "
                        f"[red]Critical task {task_id} ({agent_name}) failed — "
                        f"halting plan execution.[/red]"
                    )
                    console.print(
                        f"[bold cyan][Fiverr_Manager][/bold cyan] "
                        f"Status transition: {task_id} in_progress → failed (critical)"
                    )
                    task_results.append({
                        "task_id": task_id,
                        "agent": agent_name,
                        "status": "error",
                        "critical": True,
                        "result": last_result,
                    })
                    halted_on_critical = True
                    break  # exits retry loop; outer loop will break too

                # ── Task 2.5: non-critical — retry if attempts remain ──
                attempt += 1
                if attempt <= max_retries:
                    console.print(
                        f"[bold cyan][Fiverr_Manager][/bold cyan] "
                        f"Retry {attempt}/{max_retries} for {agent_name}"
                    )
                    console.print(
                        f"[bold cyan][Fiverr_Manager][/bold cyan] "
                        f"Status transition: {task_id} failed → retrying "
                        f"(attempt {attempt + 1})"
                    )
                else:
                    # Max retries exhausted — mark failed and continue
                    break

            # ── Outer break for critical halt ──────────────────────────
            if halted_on_critical:
                break

            # ── Record outcome ─────────────────────────────────────────
            if succeeded:
                outcome = "success"
                # ── Task 2.4: update Shared_State with context_for_next ─
                ctx_next = last_result.get("context_for_next", {})
                if ctx_next and isinstance(ctx_next, dict):
                    for k, v in ctx_next.items():
                        self.shared_state.set(k, v)

                # ── Task 2.8: log completion ────────────────────────────
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"Completed task {task_id} ({agent_name}): {instruction} "
                    f"— status: success"
                )
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"Status transition: {task_id} in_progress → success"
                )
            else:
                outcome = "error"
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"[yellow]Task {task_id} ({agent_name}): {instruction} "
                    f"— status: error (failed after "
                    f"{max_retries} retr{'y' if max_retries == 1 else 'ies'}) "
                    f"— continuing.[/yellow]"
                )
                console.print(
                    f"[bold cyan][Fiverr_Manager][/bold cyan] "
                    f"Status transition: {task_id} in_progress → failed"
                )

            # ── Task 2.7: log successful attempt outcome ───────────────
            # Error attempts (including retries) are logged individually
            # inside the retry loop above. Only the success case needs a
            # final entry here because the loop breaks on success before
            # the per-attempt error path is reached.
            if outcome == "success":
                _write_log_entry(agent_name, instruction, "success",
                                 last_result.get("message", ""))

            task_results.append({
                "task_id": task_id,
                "agent": agent_name,
                "status": outcome,
                "critical": is_critical,
                "result": last_result,
            })

        # ── Critical halt: return error immediately ────────────────────
        if halted_on_critical:
            critical_task = task_results[-1] if task_results else {}
            return {
                "status": "error",
                "message": (
                    f"Plan execution halted: critical task "
                    f"'{critical_task.get('task_id', 'unknown')}' "
                    f"({critical_task.get('agent', 'unknown')}) failed. "
                    f"Completed {len(task_results) - 1} of {len(sub_tasks)} "
                    f"sub-task(s). Shared_State has been preserved for replay."
                ),
                "data": {
                    "sub_tasks_completed": len(task_results) - 1,
                    "sub_tasks_total": len(sub_tasks),
                    "results": task_results,
                    "halted": True,
                },
                "metadata": {
                    "session_id": self.session_id,
                    "change_log": self.shared_state.change_log,
                    "log_path": log_path,
                },
            }

        # ── All sub-tasks executed — synthesize output (task 2.9 stub) ─
        return self._synthesize_output(goal, sub_tasks, task_results, log_path)

    def _synthesize_output(self, goal: str, sub_tasks: list,
                           task_results: list, log_path: str) -> dict:
        """Assemble the final AgentResult with an LLM-generated narrative summary.

        - ``data["results"]``      — raw sub-agent result dicts (req 1.11)
        - ``message``              — 50-200 word natural-language summary  (req 1.11)
        - ``metadata["change_log"]`` — Shared_State change log (req 9.3)
        - ``status``               — "success" / "partial" / "error"

        Parameters
        ----------
        goal : str
            The original user goal.
        sub_tasks : list
            All sub-tasks in the plan.
        task_results : list
            Execution results for each sub-task.
        log_path : str
            Path to the JSONL session log file.

        Returns
        -------
        dict
            AgentResult-compatible dict.
        """
        succeeded = sum(1 for r in task_results if r.get("status") == "success")
        failed    = sum(1 for r in task_results if r.get("status") == "error")
        skipped   = sum(1 for r in task_results if r.get("status") == "skipped")
        total     = len(sub_tasks)

        console.print(
            f"[bold cyan][Fiverr_Manager][/bold cyan] "
            f"Plan complete — {succeeded} succeeded, {failed} failed, "
            f"{skipped} skipped out of {total} sub-task(s)."
        )

        # ── Determine overall status ────────────────────────────────────
        if failed == 0 and skipped == 0:
            overall_status = "success"
        elif succeeded > 0:
            overall_status = "partial"
        else:
            overall_status = "error"

        # ── Build per-task outcome summary for the LLM prompt ──────────
        task_lines: list[str] = []
        for r in task_results:
            tid    = r.get("task_id", "?")
            agent  = r.get("agent", "unknown")
            status = r.get("status", "unknown")
            msg    = ""
            inner  = r.get("result", {})
            if isinstance(inner, dict):
                msg = inner.get("message", "")
            task_lines.append(
                f"  - {tid} ({agent}): {status}"
                + (f" — {msg}" if msg else "")
            )
        task_summary_text = "\n".join(task_lines) or "  (no sub-tasks executed)"

        # ── Request narrative summary from LLM ─────────────────────────
        console.print(
            "[bold cyan][Fiverr_Manager][/bold cyan] "
            "Generating natural-language summary via LLM…"
        )

        summary_prompt = (
            f"You are summarising the outcome of a Fiverr automation session.\n\n"
            f"Goal: {goal}\n\n"
            f"Overall status: {overall_status} "
            f"({succeeded}/{total} sub-tasks succeeded, "
            f"{failed} failed, {skipped} skipped)\n\n"
            f"Sub-task outcomes:\n{task_summary_text}\n\n"
            f"Write a clear, professional natural-language summary of what was "
            f"accomplished. Reference the goal and the outcome of each sub-task. "
            f"The summary MUST be between 50 and 200 words. "
            f"Do NOT use bullet points or markdown — plain prose only."
        )

        llm_summary: str = ""
        try:
            raw_summary = self.client.ask(summary_prompt)
            # Reject obvious error responses from the client wrapper
            if (
                raw_summary
                and not raw_summary.startswith("[")        # e.g. "[AgentName ERROR]:"
                and "ERROR" not in raw_summary[:30]
            ):
                llm_summary = raw_summary.strip()
        except Exception as llm_exc:
            console.print(
                f"[bold cyan][Fiverr_Manager][/bold cyan] "
                f"[yellow]LLM summary call raised an exception: {llm_exc} "
                f"— using fallback summary.[/yellow]"
            )

        # ── Validate / trim word count (50-200 words) ──────────────────
        if llm_summary:
            words = llm_summary.split()
            if len(words) < 50:
                # Too short — discard and fall back to built-in summary
                console.print(
                    "[bold cyan][Fiverr_Manager][/bold cyan] "
                    "[yellow]LLM summary too short (<50 words) — using fallback.[/yellow]"
                )
                llm_summary = ""
            elif len(words) > 200:
                # Too long — trim to exactly 200 words
                llm_summary = " ".join(words[:200])
                console.print(
                    "[bold cyan][Fiverr_Manager][/bold cyan] "
                    "[yellow]LLM summary trimmed to 200 words.[/yellow]"
                )

        # ── Fallback: deterministic summary when LLM output is unusable ─
        if not llm_summary:
            console.print(
                "[bold cyan][Fiverr_Manager][/bold cyan] "
                "Using fallback plain-text summary."
            )
            verb = "fully" if overall_status == "success" else "partially"
            per_task_parts = ", ".join(
                f"{r.get('task_id', '?')} ({r.get('agent', 'unknown')}) — "
                f"{r.get('status', 'unknown')}"
                for r in task_results
            ) or "no sub-tasks executed"
            llm_summary = (
                f"The Fiverr automation session for the goal \"{goal}\" has "
                f"{verb} completed. "
                f"Out of {total} planned sub-task(s), {succeeded} succeeded, "
                f"{failed} failed, and {skipped} were skipped. "
                f"Sub-task results: {per_task_parts}. "
                f"The overall session status is '{overall_status}'. "
                f"Shared state has been updated with all available context for "
                f"future sessions."
            )
            # Trim fallback to 200 words just in case
            words = llm_summary.split()
            if len(words) > 200:
                llm_summary = " ".join(words[:200])

        console.print(
            "[bold cyan][Fiverr_Manager][/bold cyan] "
            f"Summary ready ({len(llm_summary.split())} words)."
        )

        # ── Assemble and return the final AgentResult ───────────────────
        result = {
            "status": overall_status,
            "message": llm_summary,
            "data": {
                "sub_tasks_total": total,
                "sub_tasks_succeeded": succeeded,
                "sub_tasks_failed": failed,
                "sub_tasks_skipped": skipped,
                "results": task_results,           # raw sub-agent results (req 1.11)
            },
            "metadata": {
                "session_id": self.session_id,
                "change_log": self.shared_state.change_log,  # req 9.3
                "log_path": log_path,
            },
        }

        console.print(
            "[bold cyan][Fiverr_Manager][/bold cyan] Final synthesis complete."
        )

        return result

    # ------------------------------------------------------------------
    # Interactive mode (task 4.4 will fully implement this)
    # ------------------------------------------------------------------

    def run_interactive(self) -> None:  # pragma: no cover
        """Standalone interactive REPL for Fiverr Manager."""
        from rich.panel import Panel

        console.print(Panel(
            "[bold cyan]FIVERR MANAGER[/bold cyan]\n"
            "[dim]Powered by Gemini · UltraSwarm Fiverr Sub-Swarm[/dim]",
            border_style="cyan",
        ))

        while True:
            try:
                goal = input("\nEnter Fiverr goal (or 'exit'): ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Session ended.[/dim]")
                break

            if goal.lower() in {"exit", "quit", "q"}:
                console.print("[dim]Goodbye.[/dim]")
                break

            result = self.run({"goal": goal})
            status_color = "green" if result.get("status") == "success" else "red"
            console.print(Panel(
                result.get("message", str(result)),
                title=f"[{status_color}]{result.get('status', 'unknown')}[/{status_color}]",
                border_style=status_color,
            ))
