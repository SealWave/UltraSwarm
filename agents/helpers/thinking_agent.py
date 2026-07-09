import json
from core.base_agent import BaseAgent
from core.result_schema import AgentResult


class ThinkingAgent(BaseAgent):

    name = "thinking_agent"
    role = "helper"
    description = (
        "Cognitive decomposition agent. Receives a high-level user goal and "
        "breaks it into a structured, ordered JSON plan of subtasks. "
        "Each subtask specifies its instruction, required output, needed skills, "
        "and dependencies on other tasks."
    )
    default_skills = ["task_decomposition_skill"]
    base_system_prompt = """
You are the Thinking Agent — a world-class AI task planner.

Your ONLY job is to receive a user's goal and produce a detailed, structured
execution plan in JSON format. You do NOT execute tasks. You think.

Your plan must:
1. Break the goal into the minimum number of necessary subtasks (no redundancy).
2. Order subtasks so that dependencies are always satisfied before a task runs.
3. For each subtask, write a clear, self-contained instruction that another AI agent
   can execute without needing to ask questions.
4. Identify what skills each subtask requires.
5. Identify what data each task produces and what data it needs from earlier tasks.

OUTPUT FORMAT: You must ONLY respond with a valid JSON object.
No preamble, no explanation, no markdown fences.
The JSON must strictly follow the plan schema you have been given.

RULES:
- Never create more than 10 subtasks for a single goal.
- Never create circular dependencies.
- If the goal is very simple (e.g., "search for X"), one subtask is fine.
- Every instruction must be specific enough that a blind agent can execute it.
- Context keys must be snake_case strings.
"""

    def run(self, input_data: dict) -> dict:
        """
        Decompose a goal into a structured plan.

        Args:
            input_data: {
                "goal": str,       # The high-level user goal
                "context": dict,   # Optional pre-existing context
            }

        Returns:
            AgentResult with output = the plan dict, or error if parsing fails.
        """
        goal = input_data.get("goal", "")
        context = input_data.get("context", {})

        context_str = f"\n\nAvailable context keys: {list(context.keys())}" if context else ""
        prompt = (
            f"USER GOAL: {goal}{context_str}\n\n"
            f"Produce a complete execution plan in the required JSON format."
        )

        try:
            plan = self.chat_json(prompt, reset_history=True)
            self._validate_plan(plan)
            print(f"[ThinkingAgent] Plan produced: {len(plan['subtasks'])} subtasks")
            return AgentResult(
                success=True,
                agent_name=self.name,
                task_id="planning",
                output=plan
            ).to_dict()
        except (ValueError, KeyError, AssertionError) as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                task_id="planning",
                output=None,
                error=str(e)
            ).to_dict()

    def _validate_plan(self, plan: dict):
        """Basic structural validation of the generated plan."""
        assert "subtasks" in plan, "Plan missing 'subtasks' key"
        assert isinstance(plan["subtasks"], list), "'subtasks' must be a list"
        assert len(plan["subtasks"]) > 0, "Plan has no subtasks"
        for task in plan["subtasks"]:
            assert "task_id" in task, f"Subtask missing task_id: {task}"
            assert "instruction" in task, f"Subtask missing instruction: {task}"
            assert "suggested_skills" in task, f"Subtask missing suggested_skills: {task}"
