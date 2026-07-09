"""
agents/external/multi_agent_debate_agent.py
=============================================
Multi-Agent Debate System — adapted from 500-AI-Agents / 20-multi-agent-debate
Original: LangChain + GPT-4o
This version: Gemini 2.5 Flash with FOR/AGAINST/JUDGE three-turn pipeline
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

SYSTEM_PROMPT_FOR = """
You are a skilled debater constructing the strongest possible FOR / PRO argument.

Your job: build the most compelling case in favor of the position.
Steel-man your arguments — use the strongest evidence and reasoning available.
Be thorough but concise: 3 key arguments with supporting points.

Return JSON:
{
  "stance": "FOR",
  "opening_statement": "1-2 sentence compelling opening",
  "key_arguments": [
    {"argument": "...", "supporting_evidence": "...", "strength": "high|medium"},
    {"argument": "...", "supporting_evidence": "...", "strength": "high|medium"},
    {"argument": "...", "supporting_evidence": "...", "strength": "high|medium"}
  ],
  "closing_statement": "1-2 sentence closing"
}
"""

SYSTEM_PROMPT_AGAINST = """
You are a skilled debater constructing the strongest possible AGAINST / CON argument.

Your job: build the most compelling case against the position.
Steel-man your arguments — anticipate and refute the strongest FOR arguments.
Be thorough but concise: 3 key counterarguments.

Return JSON:
{
  "stance": "AGAINST",
  "opening_statement": "1-2 sentence compelling opening",
  "key_arguments": [
    {"argument": "...", "supporting_evidence": "...", "strength": "high|medium"},
    {"argument": "...", "supporting_evidence": "...", "strength": "high|medium"},
    {"argument": "...", "supporting_evidence": "...", "strength": "high|medium"}
  ],
  "closing_statement": "1-2 sentence closing"
}
"""

SYSTEM_PROMPT_JUDGE = """
You are an impartial debate judge scoring both sides of an argument.

You evaluate arguments on:
1. Logical coherence (0-10)
2. Quality of evidence (0-10)
3. Argument strength (0-10)
4. Consistency (0-10)

You are neutral — no personal bias. You score based purely on the strength of arguments presented.

Return JSON:
{
  "score_for": 7.5,
  "score_against": 8.0,
  "evaluation_for": "What FOR argued well and where it was weak",
  "evaluation_against": "What AGAINST argued well and where it was weak",
  "winner": "FOR | AGAINST | Draw",
  "winning_reasoning": "Why this side won or why it's a draw",
  "recommendation": "Balanced takeaway for someone making a decision",
  "nuance": "What both sides got right that should be considered together"
}
"""


class MultiAgentDebateAgent:
    """
    Multi-Agent Debate System.
    Runs a structured FOR / AGAINST debate with a neutral judge scoring.
    """

    name = "multi_agent_debate_agent"
    role = "worker"
    description = (
        "Runs a structured two-sided debate on any topic, decision, or strategy. "
        "Generates the strongest FOR and AGAINST arguments, then scores both sides. "
        "Best for: decision support, devil's advocate analysis, idea stress-testing, "
        "pros/cons evaluation, multi-perspective research."
    )
    skill_id = "multi_agent_debate_skill"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.for_client = make_client(SYSTEM_PROMPT_FOR, "DEBATE-FOR")
        self.against_client = make_client(SYSTEM_PROMPT_AGAINST, "DEBATE-AGAINST")
        self.judge_client = make_client(SYSTEM_PROMPT_JUDGE, "DEBATE-JUDGE")

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": [self.skill_id],
        }

    def debate(self, topic: str) -> dict:
        """
        Run a full structured debate on a topic.

        Args:
            topic: The topic, statement, or decision to debate.
                   Examples:
                   - "Should we expand into the European market?"
                   - "Is Python better than JavaScript for backend development?"
                   - "We should raise our product prices by 20%"

        Returns:
            Full debate result with FOR, AGAINST, and judge verdict.
        """
        console.print(f"\n[cyan]DEBATE:[/cyan] {topic}")

        # Load skill guidance
        skills = load_skills_for_task(f"debate analysis {topic}", top_k=1)
        skill_block = ""
        if skills:
            loader = get_skill_loader()
            skill_block = loader.build_skill_prompt(skills)

        topic_prompt = f"Debate topic / statement: {topic}\n\n{skill_block}"

        # Turn 1: FOR arguments
        console.print("[dim]Building FOR arguments...[/dim]")
        for_result = self.for_client.ask_json(
            f"{topic_prompt}\n\nConstruct the strongest possible FOR/PRO argument."
        )

        # Turn 2: AGAINST arguments (receives FOR arguments to rebut)
        import json
        console.print("[dim]Building AGAINST arguments...[/dim]")
        against_result = self.against_client.ask_json(
            f"{topic_prompt}\n\n"
            f"FOR position has argued:\n{json.dumps(for_result, indent=2)}\n\n"
            f"Construct the strongest possible AGAINST/CON argument, anticipating and rebutting these points."
        )

        # Turn 3: Judge verdict
        console.print("[dim]Judge evaluating...[/dim]")
        judge_result = self.judge_client.ask_json(
            f"Topic: {topic}\n\n"
            f"FOR POSITION:\n{json.dumps(for_result, indent=2)}\n\n"
            f"AGAINST POSITION:\n{json.dumps(against_result, indent=2)}\n\n"
            f"Score and evaluate both sides impartially."
        )

        result = {
            "topic": topic,
            "for_position": for_result,
            "against_position": against_result,
            "verdict": judge_result,
        }

        save_output("multi_agent_debate", f"debate_{topic[:30]}", result, "json")
        return result

    def run(self, input_data: dict) -> dict:
        """BaseAgent-compatible run() method."""
        task_id = input_data.get("task_id", "debate_task")
        instruction = input_data.get("instruction", "")

        try:
            result = self.debate(instruction)
            verdict = result.get("verdict", {})
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": result,
                "error": None,
                "metadata": {
                    "winner": verdict.get("winner", "?"),
                    "score_for": verdict.get("score_for", 0),
                    "score_against": verdict.get("score_against", 0),
                },
                "context_for_next": {"debate_result": result, "recommendation": verdict.get("recommendation")},
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
            "[bold cyan]MULTI-AGENT DEBATE SYSTEM[/bold cyan]\n"
            "[dim]FOR vs AGAINST — Powered by Gemini 2.5 Flash[/dim]",
            border_style="cyan"
        ))

        while True:
            topic = input("\nDebate topic or statement (or 'exit'): ").strip()
            if topic.lower() in {"exit", "quit", "q"}:
                break
            result = self.debate(topic)
            verdict = result.get("verdict", {})
            winner = verdict.get("winner", "?")
            winner_color = "green" if winner == "FOR" else ("red" if winner == "AGAINST" else "yellow")

            console.print(Panel(
                f"FOR score: {verdict.get('score_for', '?')}/10\n"
                f"AGAINST score: {verdict.get('score_against', '?')}/10\n\n"
                f"Winner: [{winner_color}]{winner}[/{winner_color}]\n"
                f"Reasoning: {verdict.get('winning_reasoning', '')}\n\n"
                f"Recommendation: {verdict.get('recommendation', '')}",
                title=f"Debate Verdict: {topic[:50]}",
                border_style=winner_color
            ))
