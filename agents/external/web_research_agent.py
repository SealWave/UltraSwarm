"""
agents/external/web_research_agent.py
=======================================
Web Research Agent — adapted from 500-AI-Agents / 01-web-research-agent
Original: LangGraph + Tavily + GPT-4o-mini
This version: Gemini 2.5 Flash + browser tools from tools/browser.py

Capability: Searches the web for a topic and synthesizes a structured
research report with summary, key findings, and cited sources.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from tools.browser import google_search, fetch_page
from tools.output_manager import save_output
from tools.agent_skill_loader import load_skills_for_task
from rich.console import Console
from rich.panel import Panel

console = Console()

SYSTEM_PROMPT = """
You are a world-class web research analyst.

Your job:
1. Receive a research query or topic.
2. Synthesize information into a clear, structured research report.
3. Every claim you make must be tied to a source.
4. If information is uncertain, say so — never hallucinate facts.

OUTPUT: Always return a JSON object with these keys:
{
  "summary": "200-400 word prose synthesis",
  "key_findings": ["finding 1", "finding 2", "..."],
  "sources": [{"title": "...", "url": "..."}],
  "search_queries_used": ["query 1", "query 2"],
  "confidence": "high | medium | low"
}
"""


class WebResearchAgent:
    """
    Web Research Agent.
    Searches the web for a query and returns a structured research report.
    Compatible with the EcomerseSwarm agent registry.
    """

    name = "web_research_agent"
    role = "helper"
    description = (
        "Searches the web for any topic and synthesizes findings into a structured "
        "research report with summary, key facts, and cited sources. "
        "Best for: fact-finding, background research, current events, competitor lookups."
    )
    skill_id = "web_research_skill"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = make_client(SYSTEM_PROMPT, "WEB-RESEARCH")

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": [self.skill_id],
        }

    def research(self, query: str, depth: str = "deep", max_searches: int = 3) -> dict:
        """
        Perform a web search and return a structured research report.

        Args:
            query: Research question or topic.
            depth: "shallow" (snippets only) | "deep" (reads full pages).
            max_searches: Number of search queries to run (1-5).

        Returns:
            dict with summary, key_findings, sources, search_queries_used, confidence.
        """
        console.print(f"\n[cyan]WEB RESEARCH:[/cyan] {query}")

        # Generate diverse search queries
        query_prompt = (
            f"Research topic: {query}\n\n"
            f"Generate {max_searches} diverse, targeted Google search queries that cover "
            f"different angles of this topic. Return ONLY a JSON array of strings."
        )
        try:
            queries = self.client.ask_json(query_prompt)
            if not isinstance(queries, list):
                queries = [query]
        except Exception:
            queries = [query]
        queries = queries[:max_searches]

        # Execute searches and collect content
        raw_content = []
        sources = []
        for q in queries:
            results = google_search(q, max_results=5)
            for r in results:
                sources.append({"title": r.get("title", ""), "url": r.get("url", "")})
                if depth == "deep":
                    page = fetch_page(r.get("url", ""))
                    if isinstance(page, dict):
                        text = page.get("text", "") or page.get("content", "")
                    else:
                        text = str(page) if page else ""
                    if text:
                        raw_content.append(f"SOURCE: {r.get('url', '')}\n{text[:3000]}")
                else:
                    snippet = r.get("snippet", "")
                    if snippet:
                        raw_content.append(f"SOURCE: {r.get('url', '')}\n{snippet}")

        combined = "\n\n---\n\n".join(raw_content)
        if len(combined) > 10000:
            combined = combined[:10000] + "\n\n[Content truncated for length]"

        # Load skill context for enriched output
        skills = load_skills_for_task(query, top_k=1)
        skill_block = ""
        if skills:
            from tools.agent_skill_loader import get_skill_loader
            loader = get_skill_loader()
            skill_block = f"\nAdditional guidance:\n{loader.build_skill_prompt(skills)}\n"

        synthesis_prompt = (
            f"Research query: {query}\n\n"
            f"Web content gathered:\n\n{combined}\n\n"
            f"Queries used: {queries}\n"
            f"{skill_block}"
            f"Synthesize this into a structured JSON research report."
        )

        result = self.client.ask_json(synthesis_prompt)
        result["search_queries_used"] = queries
        result["sources"] = sources[:10]  # Cap to 10 sources

        save_output("web_research_agent", f"research_{query[:40]}", result, "json")
        return result

    def run(self, input_data: dict) -> dict:
        """
        BaseAgent-compatible run() method for Orchestrator integration.

        Args:
            input_data: {
                "task_id": str,
                "instruction": str,  # research query
                "context": dict,
                "depth": str,        # optional: "shallow" | "deep"
            }
        """
        from core.result_schema import ExecutionResult
        task_id = input_data.get("task_id", "research_task")
        instruction = input_data.get("instruction", "")
        depth = input_data.get("depth", "deep")

        try:
            result = self.research(instruction, depth=depth)
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": result,
                "error": None,
                "metadata": {},
                "context_for_next": {"research_results": result},
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
            "[bold cyan]WEB RESEARCH AGENT[/bold cyan]\n"
            "[dim]Powered by Gemini 2.5 Flash + Web Search[/dim]",
            border_style="cyan"
        ))

        while True:
            query = input("\nResearch query (or 'exit'): ").strip()
            if query.lower() in {"exit", "quit", "q"}:
                break
            depth = input("Depth — shallow/deep [deep]: ").strip() or "deep"
            result = self.research(query, depth=depth)
            console.print(Panel(
                result.get("summary", str(result)),
                title=f"Research: {query[:50]}",
                border_style="green"
            ))
            console.print(f"\n[dim]Key findings:[/dim]")
            for kf in result.get("key_findings", []):
                console.print(f"  • {kf}")
