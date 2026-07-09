"""
swarms/full_launch_swarm.py
============================
FULL PRODUCT LAUNCH SWARM — The Nuclear Option
Runs ALL agents in optimal sequence for a complete product launch.
Pipeline: SEO → Product → Ads → Social → Banner → Store Manager

This is what you run when you want everything done at once.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from swarms.product_swarm import run_product_swarm
from swarms.marketing_swarm import run_marketing_swarm
from swarms.swarm_engine import SwarmResult, print_swarm_header, print_swarm_summary
from tools.output_manager import save_output
from rich.console import Console
from rich.panel import Panel

console = Console()


def run_full_launch_swarm(product_name: str, product_description: str = "",
                          competitor_url: str = None, auto_push: bool = False) -> dict:
    """
    FULL LAUNCH SWARM
    ─────────────────
    Phase 1 — Research & Listing (Product Swarm)
      SERAPH → SCOUT → FORGE

    Phase 2 — Go-To-Market (Marketing Swarm)
      SERAPH → PULSE → VIBE → CANVAS

    This is the master orchestrator. Run this once for a complete
    product launch package ready to deploy.
    """
    console.print(Panel(
        "[bold white]FULL PRODUCT LAUNCH SWARM[/bold white]\n\n"
        f"Product: [cyan]{product_name}[/cyan]\n"
        "Agents: SERAPH + SCOUT + FORGE + PULSE + VIBE + CANVAS\n"
        "Phases: Research -> Listing -> Ads -> Social -> Visuals -> Store",
        border_style="bright_white",
        title="ECOM SWARM — FULL LAUNCH"
    ))

    results = {}

    # ── PHASE 1: Product Research & Listing ───────────────────────────────
    console.print("\n\n[bold white]====== PHASE 1: PRODUCT RESEARCH ======[/bold white]")
    product_swarm = run_product_swarm(
        topic=product_name,
        competitor_url=competitor_url,
        auto_push=False  # Push after marketing is ready
    )
    results["product_phase"] = product_swarm.summary()

    # ── PHASE 2: Marketing Campaign ───────────────────────────────────────
    console.print("\n\n[bold white]====== PHASE 2: MARKETING CAMPAIGN ======[/bold white]")
    marketing_swarm = run_marketing_swarm(
        product_name=product_name,
        product_description=product_description
    )
    results["marketing_phase"] = marketing_swarm.summary()

    # ── FINAL SUMMARY ─────────────────────────────────────────────────────
    total_agents = (
        len(product_swarm.results) +
        len(marketing_swarm.results)
    )
    total_errors = (
        len(product_swarm.errors) +
        len(marketing_swarm.errors)
    )

    console.print(Panel(
        f"[bold green]FULL LAUNCH SWARM COMPLETE[/bold green]\n\n"
        f"Product: {product_name}\n"
        f"Total agents completed: {total_agents}\n"
        f"Total errors: {total_errors}\n\n"
        f"[yellow]What was created:[/yellow]\n"
        f"  SEO keyword strategy & competitor analysis\n"
        f"  Full product listing (title, description, tags, pricing)\n"
        f"  Product launch plan\n"
        f"  Google Ads campaign (RSA + extensions + keywords)\n"
        f"  Meta Ads (cold + retargeting, carousel, stories)\n"
        f"  TikTok ads & organic video scripts\n"
        f"  Instagram content suite + stories sequence\n"
        f"  30-day social media content calendar\n"
        f"  Banner & ad creative briefs + AI image prompts\n\n"
        f"[dim]All outputs saved to ./outputs/[/dim]",
        border_style="green",
        title="LAUNCH PACKAGE READY"
    ))

    save_output("swarms", f"full_launch_{product_name}", results, "json")
    return results


if __name__ == "__main__":
    product = input("Product name: ").strip()
    desc = input("Description (optional): ").strip()
    competitor = input("Competitor URL (optional): ").strip()
    run_full_launch_swarm(product, desc, competitor or None)
