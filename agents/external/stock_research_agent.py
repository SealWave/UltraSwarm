"""
agents/external/stock_research_agent.py
=========================================
Stock Research Agent — adapted from 500-AI-Agents / 11-stock-research-agent
Original: LangChain + yfinance + GPT-4o-mini
This version: Gemini 2.5 Flash + web search for financial data
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
You are a financial research analyst specializing in equity research.

You analyze stocks and companies using publicly available data.
You build structured investment analyses with bull/bear cases and risk factors.

IMPORTANT DISCLAIMER: Always include this in every analysis:
"This is AI-generated research for informational purposes only.
 It is NOT professional financial advice. Consult a licensed advisor before investing."

Output format:
{
  "ticker": "SYMBOL",
  "company_name": "Full Company Name",
  "sector": "...",
  "fundamentals": {
    "pe_ratio": "...",
    "eps": "...",
    "revenue_growth_yoy": "...",
    "debt_to_equity": "...",
    "profit_margin": "...",
    "market_cap": "..."
  },
  "recent_news": ["news item 1", "news item 2"],
  "investment_thesis": {
    "bull_case": "...",
    "bear_case": "...",
    "key_catalysts": ["catalyst 1", "catalyst 2"],
    "risk_factors": ["risk 1", "risk 2", "risk 3"]
  },
  "recommendation": "Buy | Hold | Sell | Avoid",
  "confidence": "High | Medium | Low",
  "price_target_narrative": "...",
  "disclaimer": "This is AI-generated research for informational purposes only..."
}
"""


class StockResearchAgent:
    """
    Stock Research Agent.
    Analyzes stocks using web search + Gemini reasoning.
    """

    name = "stock_research_agent"
    role = "worker"
    description = (
        "Analyzes stocks and companies: financial fundamentals, investment thesis, "
        "bull/bear case, risk factors, recommendation. "
        "Best for: investment research, financial analysis, company evaluation."
    )
    skill_id = "stock_research_skill"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = make_client(SYSTEM_PROMPT, "STOCK-RESEARCH")

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": [self.skill_id],
        }

    def analyze_stock(self, ticker_or_company: str) -> dict:
        """
        Perform a stock research analysis.

        Args:
            ticker_or_company: Ticker symbol (e.g. "AAPL") or company name.

        Returns:
            Structured analysis dict.
        """
        console.print(f"\n[cyan]STOCK RESEARCH:[/cyan] {ticker_or_company}")

        # Gather financial data via web search
        queries = [
            f"{ticker_or_company} stock analysis fundamentals PE ratio 2024",
            f"{ticker_or_company} earnings revenue growth recent news",
            f"{ticker_or_company} investment risks bull bear case",
        ]

        raw_data = []
        for q in queries:
            results = google_search(q, max_results=5)
            for r in results:
                snippet = r.get("snippet", "")
                if snippet:
                    raw_data.append(f"Source: {r.get('url', '')}\n{snippet}")

        combined = "\n\n".join(raw_data[:15])

        # Load skill for guidance
        skills = load_skills_for_task(f"stock analysis {ticker_or_company}", top_k=1)
        skill_block = ""
        if skills:
            loader = get_skill_loader()
            skill_block = loader.build_skill_prompt(skills)

        prompt = (
            f"Analyze {ticker_or_company} as an investment.\n\n"
            f"Web data gathered:\n{combined}\n\n"
            f"{skill_block}\n"
            f"Build a complete investment analysis in the required JSON format."
        )

        result = self.client.ask_json(prompt)
        save_output("stock_research_agent", f"stock_{ticker_or_company}", result, "json")
        return result

    def run(self, input_data: dict) -> dict:
        """BaseAgent-compatible run() method."""
        task_id = input_data.get("task_id", "stock_task")
        instruction = input_data.get("instruction", "")
        # Extract ticker from instruction
        ticker = instruction.strip()

        try:
            result = self.analyze_stock(ticker)
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": result,
                "error": None,
                "metadata": {},
                "context_for_next": {"stock_analysis": result},
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
            "[bold cyan]STOCK RESEARCH AGENT[/bold cyan]\n"
            "[dim]Powered by Gemini 2.5 Flash | NOT financial advice[/dim]",
            border_style="cyan"
        ))

        while True:
            ticker = input("\nTicker or company name (or 'exit'): ").strip()
            if ticker.lower() in {"exit", "quit", "q"}:
                break
            result = self.analyze_stock(ticker)
            console.print(Panel(
                f"Recommendation: {result.get('recommendation', 'N/A')}\n"
                f"Confidence: {result.get('confidence', 'N/A')}\n\n"
                f"Bull: {result.get('investment_thesis', {}).get('bull_case', 'N/A')}\n\n"
                f"Bear: {result.get('investment_thesis', {}).get('bear_case', 'N/A')}\n\n"
                f"[dim]{result.get('disclaimer', '')}[/dim]",
                title=f"Analysis: {ticker}",
                border_style="green"
            ))
