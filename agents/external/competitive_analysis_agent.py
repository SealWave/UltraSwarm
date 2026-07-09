"""
agents/external/competitive_analysis_agent.py
===============================================
Competitive Analysis Agent — adapted from 500-AI-Agents / 19-competitive-analysis-agent
Original: LangGraph (identify → analyze → report pipeline) + GPT-4o
This version: Gemini 2.5 Flash with three-turn pipeline + web search
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from tools.browser import google_search
from tools.output_manager import save_output
from tools.agent_skill_loader import load_skills_for_task, get_skill_loader
from rich.console import Console
from rich.panel import Panel

console = Console()

SYSTEM_PROMPT = """
You are a strategic market research analyst specializing in competitive intelligence.

You build comprehensive competitor analyses with actionable recommendations.
Your work combines public data research with strategic reasoning.

Pipeline:
1. Identify 5 main competitors
2. Profile each competitor (strengths, weaknesses, pricing, market)
3. Generate strategic recommendations and threat assessment

Output format:
{
  "company": "...",
  "industry": "...",
  "executive_summary": "3-sentence landscape overview",
  "competitors": [
    {
      "name": "...",
      "main_products": "...",
      "strengths": ["strength 1", "strength 2"],
      "weaknesses": ["weakness 1", "weakness 2"],
      "pricing_model": "...",
      "target_market": "...",
      "threat_level": "High | Medium | Low",
      "threat_reasoning": "..."
    }
  ],
  "market_gaps": ["gap 1", "gap 2", "gap 3"],
  "strategic_recommendations": [
    "action 1", "action 2", "action 3", "action 4", "action 5"
  ],
  "competitive_score": "X/10 — how competitive this market is"
}
"""


class CompetitiveAnalysisAgent:
    """
    Competitive Analysis Agent.
    Three-turn pipeline: identify competitors → profile each → strategic report.
    """

    name = "competitive_analysis_agent"
    role = "worker"
    description = (
        "Analyzes the competitive landscape for any company or product. "
        "Identifies top competitors, profiles strengths/weaknesses, finds market gaps, "
        "and generates strategic positioning recommendations. "
        "Best for: market research, business strategy, product positioning."
    )
    skill_id = "competitive_analysis_skill"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = make_client(SYSTEM_PROMPT, "COMPETITIVE-ANALYSIS")

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": [self.skill_id],
        }

    def analyze(self, company: str, industry: str = "") -> dict:
        """
        Run a full competitive analysis.

        Args:
            company: Company or product name to analyze.
            industry: Industry context (helps with competitor identification).

        Returns:
            Full competitive analysis dict.
        """
        console.print(f"\n[cyan]COMPETITIVE ANALYSIS:[/cyan] {company}")

        # Gather competitor data via web search
        queries = [
            f"{company} main competitors {industry} 2024",
            f"{company} vs competitors comparison strengths weaknesses",
            f"{industry} market leaders top companies 2024",
        ]
        raw_data = []
        for q in queries:
            results = google_search(q, max_results=5)
            for r in results:
                snippet = r.get("snippet", "")
                if snippet:
                    raw_data.append(f"Source: {r.get('url', '')}\n{snippet}")

        web_context = "\n\n".join(raw_data[:12])

        # Load skill guidance
        skills = load_skills_for_task(f"competitive analysis {company} {industry}", top_k=1)
        skill_block = ""
        if skills:
            loader = get_skill_loader()
            skill_block = loader.build_skill_prompt(skills)

        # Turn 1: Identify competitors
        id_prompt = (
            f"Company: {company}\nIndustry: {industry or 'general'}\n\n"
            f"Web context:\n{web_context[:3000]}\n\n"
            f"List exactly 5 main competitors for {company}. "
            f"Return ONLY a JSON array of company name strings."
        )
        competitors = self.client.ask_json(id_prompt)
        if not isinstance(competitors, list):
            competitors = [f"Competitor {i+1}" for i in range(5)]
        competitors = competitors[:5]

        console.print(f"[dim]Competitors identified: {', '.join(competitors)}[/dim]")

        # Turn 2: Profile each competitor
        profiles = []
        for comp in competitors:
            profile_prompt = (
                f"Profile {comp} as a competitor to {company} in {industry or 'their industry'}.\n\n"
                f"Return JSON with: name, main_products, strengths (list of 2), "
                f"weaknesses (list of 2), pricing_model, target_market, "
                f"threat_level (High/Medium/Low), threat_reasoning."
            )
            profile = self.client.ask_json(profile_prompt)
            if isinstance(profile, dict):
                profiles.append(profile)

        # Turn 3: Strategic report
        import json
        report_prompt = (
            f"Company: {company}\nIndustry: {industry or 'general'}\n\n"
            f"Competitor profiles:\n{json.dumps(profiles, indent=2)}\n\n"
            f"{skill_block}\n"
            f"Generate the complete competitive analysis report in the required JSON format. "
            f"Include: executive_summary, market_gaps (3 items), "
            f"strategic_recommendations (5 items), competitive_score."
        )
        result = self.client.ask_json(report_prompt)
        result["company"] = company
        result["industry"] = industry or "general"
        result["competitors"] = profiles  # Ensure profiles are included

        save_output("competitive_analysis_agent", f"competitive_{company[:30]}", result, "json")
        return result

    def run(self, input_data: dict) -> dict:
        """BaseAgent-compatible run() method."""
        task_id = input_data.get("task_id", "analysis_task")
        instruction = input_data.get("instruction", "")
        context_data = input_data.get("context", {})
        industry = context_data.get("industry", "")
        # Allow instruction to be "company: industry" format
        company = instruction
        if ":" in instruction and not industry:
            parts = instruction.split(":", 1)
            company = parts[0].strip()
            industry = parts[1].strip()

        try:
            result = self.analyze(company=company, industry=industry)
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": result,
                "error": None,
                "metadata": {"competitors_found": len(result.get("competitors", []))},
                "context_for_next": {"competitive_analysis": result},
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
            "[bold cyan]COMPETITIVE ANALYSIS AGENT[/bold cyan]\n"
            "[dim]Powered by Gemini 2.5 Flash + Web Search[/dim]",
            border_style="cyan"
        ))

        while True:
            company = input("\nCompany/product to analyze (or 'exit'): ").strip()
            if company.lower() in {"exit", "quit", "q"}:
                break
            industry = input("Industry (optional): ").strip()
            result = self.analyze(company, industry=industry)
            console.print(Panel(
                result.get("executive_summary", "Analysis complete."),
                title=f"Competitive Analysis: {company}",
                border_style="green"
            ))
            for i, comp in enumerate(result.get("competitors", []), 1):
                threat_color = {"High": "red", "Medium": "yellow", "Low": "green"}.get(
                    comp.get("threat_level", "Medium"), "white"
                )
                console.print(
                    f"  {i}. {comp.get('name', '?')} — "
                    f"[{threat_color}]{comp.get('threat_level', '?')} threat[/{threat_color}]"
                )
