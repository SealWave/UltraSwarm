"""
swarms/product_swarm.py
========================
PRODUCT RESEARCH SWARM
Pipeline: SEO → Product Research → Store Manager
Finds winning products, optimizes them, and prepares for store upload.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.seo_agent import SEOAgent
from agents.product_agent import ProductAgent
from agents.store_manager_agent import StoreManagerAgent
from swarms.swarm_engine import SwarmResult, run_agent_step, print_swarm_header, print_swarm_summary
from tools.output_manager import save_output
from rich.console import Console
from rich.panel import Panel

console = Console()


def run_product_swarm(topic: str, competitor_url: str = None, auto_push: bool = False) -> SwarmResult:
    """
    PRODUCT RESEARCH SWARM
    ──────────────────────
    1. SEO Agent   → keyword intelligence + competitor SEO
    2. Product Agent → winning product identification + full listing
    3. Store Manager → launch plan + (optional) push to store

    Args:
        topic: product keyword or niche to research
        competitor_url: optional competitor URL to analyze
        auto_push: if True and store API configured, push product to store
    """
    print_swarm_header(
        "PRODUCT RESEARCH SWARM",
        "Finds winning products, creates SEO-optimized listings, prepares for launch",
        ["SERAPH (SEO)", "SCOUT (Product)", "FORGE (Store Manager)"]
    )

    swarm = SwarmResult("Product Research Swarm")
    seo = SEOAgent()
    product = ProductAgent()
    store = StoreManagerAgent()

    # ── Step 1: SEO Intelligence ───────────────────────────────────────────
    console.print("\n[bold cyan]━━ STEP 1/3: SEO Intelligence ━━[/bold cyan]")
    seo_report = run_agent_step(
        "SERAPH: Keyword Research",
        seo.research_keyword,
        swarm,
        topic
    )

    # ── Step 2: Product Research ───────────────────────────────────────────
    console.print("\n[bold green]━━ STEP 2/3: Product Research ━━[/bold green]")

    # 2a. Niche research
    niche_data = run_agent_step(
        "SCOUT: Niche Research",
        product.research_niche,
        swarm,
        topic
    )

    # 2b. Competitor analysis (if URL provided)
    if competitor_url:
        run_agent_step(
            "SCOUT: Competitor Analysis",
            product.analyze_competitor_products,
            swarm,
            competitor_url
        )

    # 2c. Full listing for top product
    top_product = topic
    if niche_data and isinstance(niche_data, dict):
        top_product = niche_data.get("top_pick", topic)

    listing = run_agent_step(
        f"SCOUT: Product Listing — {top_product}",
        product.create_product_listing,
        swarm,
        top_product,
        competitor_url
    )

    # ── Step 3: Store Launch Plan ──────────────────────────────────────────
    console.print("\n[bold red]━━ STEP 3/3: Store Preparation ━━[/bold red]")

    launch_plan = run_agent_step(
        "FORGE: Launch Plan",
        store.plan_product_launch,
        swarm,
        top_product,
        listing
    )

    if auto_push and listing:
        run_agent_step(
            "FORGE: Push to Store",
            store.push_product_to_store,
            swarm,
            listing
        )

    # Save swarm summary
    save_output("swarms", "product_swarm_summary", swarm.summary(), "json")
    print_swarm_summary(swarm)
    return swarm


if __name__ == "__main__":
    topic = input("Enter product/niche to research: ").strip()
    competitor = input("Competitor URL (optional, press Enter to skip): ").strip()
    run_product_swarm(topic, competitor or None)
