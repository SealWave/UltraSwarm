import json
from core.base_agent import BaseAgent
from core.result_schema import AgentResult


class AllocatorAgent(BaseAgent):

    name = "allocator_agent"
    role = "manager"
    description = (
        "Dispatcher agent. Given a subtask and a list of available agents, "
        "determines which agent is best suited to execute the task based on "
        "agent descriptions, skills, and task requirements."
    )
    default_skills = ["agent_allocation_skill"]
    base_system_prompt = """
You are the Allocator — a specialist in routing tasks to the correct agent.

Given a subtask description and a list of available agents (with their names,
roles, descriptions, and skills), your job is to select the SINGLE best agent
for the task.

You MUST respond with a valid JSON object in this exact format:
{
  "selected_agent": "agent_name_here",
  "confidence": 0.95,
  "reason": "Brief explanation of why this agent was chosen"
}

RULES:
- Only select from the provided agent list. Never invent agent names.
- If no agent is a good match, return the agent with the closest skill match
  and set confidence below 0.5.
- Never assign manager agents to execution tasks.
- Prefer agents whose default_skills explicitly match the task's required_skills.
"""

    def assign(self, subtask: dict, available_agents: list[dict]) -> str:
        """
        Determine which agent should handle the given subtask.

        Args:
            subtask: A single subtask dict from the ThinkingAgent's plan.
            available_agents: List of agent metadata dicts from get_metadata().

        Returns:
            The name (str) of the selected agent.
        """
        prompt = (
            f"SUBTASK:\n{json.dumps(subtask, indent=2)}\n\n"
            f"AVAILABLE AGENTS:\n{json.dumps(available_agents, indent=2)}\n\n"
            f"Select the best agent for this subtask and respond in JSON."
        )

        try:
            decision = self.chat_json(prompt, reset_history=True)
            agent_name = decision.get("selected_agent", "")
            confidence = decision.get("confidence", 0.0)
            reason = decision.get("reason", "")

            print(f"[Allocator] → {agent_name} (confidence: {confidence:.0%}) | {reason}")
            return agent_name
        except (ValueError, KeyError) as e:
            print(f"[Allocator] ERROR parsing decision: {e}")
            # Fallback: return first available worker
            workers = [a for a in available_agents if a["role"] == "worker"]
            return workers[0]["name"] if workers else ""

    def run(self, input_data: dict) -> dict:
        """run() wrapper for BaseAgent compatibility. Use assign() directly."""
        agent_name = self.assign(
            subtask=input_data.get("subtask", {}),
            available_agents=input_data.get("available_agents", [])
        )
        return AgentResult(
            success=bool(agent_name),
            agent_name=self.name,
            task_id=input_data.get("task_id", ""),
            output=agent_name
        ).to_dict()
