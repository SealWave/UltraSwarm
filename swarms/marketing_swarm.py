"""
swarms/marketing_swarm.py
==========================
MARKETING SWARM
Pipeline: SEO → Ads → Social Media → Banner/Visuals
Creates a complete go-to-market campaign for a product.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.seo_agent import SEOAgent
from agents.ads_agent import AdsAgent
from agents.social_agent import SocialAgent
from agents.banner_agent import BannerAgent
from swarms.swarm_engine import SwarmResult, run_agent_step, print_swarm_header, print_swarm_summary
from tools.output_manager import save_output
from rich.console import Console

console = Console()


def run_marketing_swarm(product_name: str, product_description: str = "",
                        platforms: list = None) -> SwarmResult:
    """
    MARKETING SWARM
    ───────────────
    1. SEO Agent    → SEO brief (shared with all agents below)
    2. Ads Agent    → Google + Meta + TikTok ad campaigns
    3. Social Agent → Instagram + TikTok content + 30-day calendar
    4. Banner Agent → Visual briefs + AI image prompts

    Args:
        product_name: the product to market
        product_description: optional context
        platforms: list of platforms to focus on (default: all)
    """
    platforms = platforms or ["google", "meta", "tiktok", "instagram", "pinterest"]

    print_swarm_header(
        "MARKETING SWARM",
        "Creates a complete paid + organic marketing campaign",
        ["SERAPH (SEO)", "PULSE (Ads)", "VIBE (Social)", "CANVAS (Banners)"]
    )

    swarm = SwarmResult("Marketing Swarm")
    seo = SEOAgent()
    ads = AdsAgent()
    social = SocialAgent()
    banner = BannerAgent()

    # ── Step 1: SEO Foundation (shared by all) ─────────────────────────────
    console.print("\n[bold cyan]━━ STEP 1/4: SEO Foundation ━━[/bold cyan]")
    seo_brief = run_agent_step(
        "SERAPH: SEO Brief",
        seo.get_seo_brief,
        swarm,
        product_name
    )

    # ── Step 2: Paid Advertising ───────────────────────────────────────────
    console.print("\n[bold magenta]━━ STEP 2/4: Paid Advertising ━━[/bold magenta]")

    if "google" in platforms:
        run_agent_step(
            "PULSE: Google Ads Campaign",
            ads.create_google_ads,
            swarm,
            product_name,
            product_description
        )

    if "meta" in platforms:
        run_agent_step(
            "PULSE: Meta Ads Campaign",
            ads.create_meta_ads,
            swarm,
            product_name,
            product_description,
            "cold"
        )
        # Also create retargeting
        run_agent_step(
            "PULSE: Meta Retargeting Ads",
            ads.create_meta_ads,
            swarm,
            product_name,
            product_description,
            "warm"
        )

    if "tiktok" in platforms:
        run_agent_step(
            "PULSE: TikTok Ads",
            ads.create_tiktok_ads,
            swarm,
            product_name,
            product_description
        )

    # ── Step 3: Organic Social Media ──────────────────────────────────────
    console.print("\n[bold blue]━━ STEP 3/4: Social Media Content ━━[/bold blue]")

    if "instagram" in platforms:
        run_agent_step(
            "VIBE: Instagram Content Suite",
            social.create_instagram_content,
            swarm,
            product_name,
            "carousel"
        )

    if "tiktok" in platforms:
        run_agent_step(
            "VIBE: TikTok Video Scripts",
            social.create_tiktok_content,
            swarm,
            product_name,
            3
        )

    run_agent_step(
        "VIBE: 30-Day Content Calendar",
        social.create_content_calendar,
        swarm,
        "next month"
    )

    # ── Step 4: Visual Assets ──────────────────────────────────────────────
    console.print("\n[bold yellow]━━ STEP 4/4: Visual Assets ━━[/bold yellow]")

    run_agent_step(
        "CANVAS: Product Ad Creatives",
        banner.create_product_creative,
        swarm,
        product_name
    )

    run_agent_step(
        "CANVAS: Launch Promo Banner",
        banner.create_promo_banner,
        swarm,
        f"New Arrival — {product_name}",
        product_name
    )

    save_output("swarms", f"marketing_swarm_{product_name}", swarm.summary(), "json")
    print_swarm_summary(swarm)
    return swarm


if __name__ == "__main__":
    product = input("Product name: ").strip()
    desc = input("Description (optional): ").strip()
    run_marketing_swarm(product, desc)
