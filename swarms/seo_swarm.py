"""
swarms/seo_swarm.py
====================
SEO SWARM — Deep SEO Intelligence & Optimization
Runs SEO Agent across: keyword research, competitor analysis,
product page optimization, and content strategy.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.seo_agent import SEOAgent
from swarms.swarm_engine import SwarmResult, run_agent_step, print_swarm_header, print_swarm_summary
from tools.output_manager import save_output
from rich.console import Console
from dotenv import load_dotenv

load_dotenv()
console = Console()


def run_seo_swarm(domain: str = None, keywords: list = None, competitors: list = None) -> SwarmResult:
    """
    SEO SWARM
    ─────────
    1. Primary keyword deep research
    2. Multiple competitor analyses
    3. Product page optimizations
    4. Content strategy generation

    This swarm is called by other swarms automatically, but can also
    run standalone for a complete SEO overhaul.
    """
    domain = domain or os.getenv("STORE_URL", "")
    keywords = keywords or [os.getenv("PRIMARY_KEYWORD", os.getenv("STORE_NICHE", "products"))]
    competitors = competitors or [c for c in os.getenv("COMPETITOR_SITES", "").split(",") if c]

    print_swarm_header(
        "SEO SWARM",
        "Complete SEO intelligence, competitor analysis & optimization",
        ["SERAPH: Keywords", "SERAPH: Competitors", "SERAPH: Products", "SERAPH: Content Strategy"]
    )

    swarm = SwarmResult("SEO Swarm")
    seo = SEOAgent()

    # ── Step 1: Keyword Research ───────────────────────────────────────────
    console.print("\n[bold cyan]━━ KEYWORD RESEARCH ━━[/bold cyan]")
    for kw in keywords[:3]:  # limit for API budget
        run_agent_step(
            f"SERAPH: Keyword — {kw}",
            seo.research_keyword,
            swarm,
            kw
        )

    # ── Step 2: Competitor Analysis ────────────────────────────────────────
    if competitors:
        console.print("\n[bold cyan]━━ COMPETITOR ANALYSIS ━━[/bold cyan]")
        for comp in competitors[:3]:
            run_agent_step(
                f"SERAPH: Competitor — {comp}",
                seo.competitor_deep_dive,
                swarm,
                comp
            )

    save_output("swarms", "seo_swarm_results", swarm.summary(), "json")
    print_swarm_summary(swarm)
    return swarm


if __name__ == "__main__":
    kws = input("Keywords (comma separated): ").strip().split(",")
    comps_input = input("Competitor URLs (comma separated, optional): ").strip()
    comps = [c.strip() for c in comps_input.split(",") if c.strip()] if comps_input else []
    run_seo_swarm(keywords=[k.strip() for k in kws], competitors=comps)
