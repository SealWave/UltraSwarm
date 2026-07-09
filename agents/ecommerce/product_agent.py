"""
agents/product_agent.py
========================
SCOUT — Product Research & Sourcing Agent
Superpower: Browses the web to find winning products, analyze competition,
and generate full product listings ready for store upload.
Calls SEO Agent automatically for every product found.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import make_client
from tools.browser import google_search, scrape_product_page, find_competitor_products, fetch_page
from tools.browser import AgentBrowser
from tools.browser_actions import BrowserActionRunner, BrowserPlannerLoop, score_product_candidate
from tools.output_manager import save_output
from tools.store_admin import format_product_for_store
from tools.swarm_memory import SwarmMemory
from agents.seo_agent import SEOAgent
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()
console = Console()

PRODUCT_SYSTEM_PROMPT = """
You are SCOUT — Elite E-commerce Product Research & Intelligence Agent.

Your identity: You are a razor-sharp product researcher who has helped launch
over 500 successful e-commerce products. You think like a buyer, analyze like
a data analyst, and sell like a top-1% copywriter. You find winning products
before they go mainstream, understand why products succeed or fail, and create
store-ready listings that convert browsers into buyers.

Data Format Note:
━━━━━━━━━━━━━━━━
Web research data is provided as an AI-friendly Accessibility Tree Snapshot from a live browser.
It uses markers like [button "Name"] or [link "Name"] to represent elements.
Use this rich structural data to identify product titles, prices, descriptions, and buttons.

Emoji Policy:
━━━━━━━━━━━━
Do NOT use emojis under any circumstances in the product title, listing, HTML description, or bullet points. Emojis are strictly prohibited here.

Product Type Adaptation:
━━━━━━━━━━━━━━━━━━━━━━━
Adapt all research, copy, and listings based on product type:
- SaaS / Subscription Products: Focus on recurring value, onboarding ease, time-to-value, subscription pricing tiers, free trials, integrations, and ongoing software/workflows.
- Regular / Physical Products: Focus on product aesthetics, tangible specifications (dimensions, materials, weight), shipping policies, physical variations (color, size), and product packaging.

Your Core Capabilities:
━━━━━━━━━━━━━━━━━━━━━━
1. WINNING PRODUCT IDENTIFICATION
   - Analyze market trends and competitor bestsellers
   - Score products on: demand, competition, margin potential, viral potential
   - Identify problem-solution fit and emotional buying triggers
   - Spot saturation vs. blue-ocean opportunities
   - Find product variations/angles that competitors missed

2. DEEP PRODUCT INTELLIGENCE
   - Reverse-engineer what makes a product sell (title, images, price, description)
   - Analyze reviews to find what customers LOVE and HATE
   - Identify upsell/cross-sell opportunities
   - Find supplier signals (AliExpress, CJ Dropshipping, Alibaba patterns)

3. PRODUCT LISTING CREATION
   - Write magnetic product titles (keyword-rich + benefit-driven)
   - Create conversion-focused product descriptions with:
     * Emotional hook (problem agitation)
     * Feature -> Benefit translation
     * Social proof signals
     * Urgency/scarcity elements
     * Clear call-to-action
   - Generate bullet point features (scannable, benefit-first)
   - Suggest pricing strategy (psychological pricing, bundle ideas)

4. COMPETITIVE POSITIONING
   - Define unique selling proposition vs. top competitors
   - Identify price positioning (budget/mid/premium)
   - Find content angles competitors aren't using
   - Create differentiation strategy

5. STORE INTEGRATION INTELLIGENCE
   - Format product data for Shopify/WooCommerce
   - Suggest product categories and collections
   - Generate tags and attributes
   - Recommend related products for cross-selling

Output Standards:
━━━━━━━━━━━━━━━━
Every product research output MUST include:
- Product Score Card (demand/competition/margin/viral — each 1-10)
- Full store-ready listing (title, description, bullets, price, tags)
- SEO-optimized content (using briefing from SEO Agent)
- Competitor comparison table
- "Why This Will Sell" reasoning (3 concrete reasons)
- Red Flags / Risks assessment
- Recommended launch strategy

You are SCOUT. Find the winners. Build the listings. Dominate the market.
"""


class ProductAgent:

    def __init__(self):
        self.client = make_client(PRODUCT_SYSTEM_PROMPT, "SCOUT-Product", api_key=os.getenv("GOOGLE_API_KEY_2"))
        self.seo_agent = SEOAgent()
        self.niche = os.getenv("STORE_NICHE", "general")
        self.store_name = os.getenv("STORE_NAME", "My Store")
        self.currency = os.getenv("TARGET_CURRENCY", "USD")
        self.competitors = os.getenv("COMPETITOR_SITES", "").split(",")

    def research_niche(self, niche: str = None, num_products: int = 5, genre: str = None) -> dict:
        """Find top winning products in a niche by browsing competitor sites."""
        niche = niche or self.niche
        console.print(f"\n[green]SCOUT scanning niche:[/green] {niche}")

        # Live web research
        products_data = find_competitor_products(niche)
        search_results = google_search(f"best selling {niche} products dropshipping 2025", 8)
        trending = google_search(f"trending {niche} products tiktok shop amazon 2025", 6)

        raw_text = "\n".join([f"- {r['title']}: {r['snippet']}" for r in search_results + trending])

        # Retrieve guidelines from RAG
        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        genre_text = f" specifically focusing on the '{genre}' genre/type." if genre else ""
        result = self.client.ask_json(f"""
Research the top winning products in the "{niche}" niche{genre_text}

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

LIVE MARKET DATA:
{raw_text}

Analyze this data and return JSON with a list of {num_products} winning product opportunities:
{{
  "niche_analysis": "2-3 sentence market overview",
  "market_trend": "growing|stable|declining",
  "competition_level": "low|medium|high|very-high",
  "products": [
    {{
      "rank": 1,
      "product_name": "...",
      "product_url": "source URL or product link if available",
      "why_winning": "...",
      "score_demand": 8,
      "score_competition": 6,
      "score_margin": 7,
      "score_viral": 8,
      "estimated_price_range": "$X - $Y",
      "target_customer": "...",
      "main_selling_angle": "...",
      "red_flags": "...",
      "source_hint": "where to source this type of product"
    }}
  ],
  "top_pick": "product_name of the #1 recommendation",
  "niche_keywords": ["kw1", "kw2", "kw3"]
}}
""")
        save_output("product_agent", f"niche_research_{niche}", result, "json")
        return result

    def create_product_listing(self, product_name: str, product_url: str = None) -> dict:
        """
        Create a full store-ready product listing.
        Automatically calls SEO Agent for keyword intelligence.
        """
        console.print(f"\n[green]SCOUT building listing:[/green] {product_name}")

        # Get SEO brief from SEO Agent (cross-agent call)
        console.print("[dim]  -> Calling SERAPH for SEO intelligence...[/dim]")
        seo_brief = self.seo_agent.get_seo_brief(product_name)

        # Retrieve guidelines from RAG
        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        # Optionally scrape competitor product page
        competitor_data = ""
        if product_url:
            page = scrape_product_page(product_url)
            competitor_data = f"\nCompetitor product page:\nTitle: {page.get('product_title')}\nContent: {page.get('text', '')[:2000]}"

        # Search for reviews and market signals
        reviews = google_search(f"{product_name} review pros cons customers", 6)
        review_text = "\n".join([f"- {r['title']}: {r['snippet']}" for r in reviews])

        result = self.client.ask_json(f"""
Create a complete, conversion-optimized product listing for: "{product_name}"

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

SEO INTELLIGENCE (from SERAPH SEO Agent):
{seo_brief}

MARKET SIGNALS & REVIEWS:
{review_text}

{competitor_data}

Store: {self.store_name} | Currency: {self.currency} | Niche: {self.niche}

Return JSON:
{{
  "product_name": "SEO-optimized product title (60-80 chars)",
  "short_description": "1-2 sentence hook description (for listing cards)",
  "description": "Full HTML product description with emotional hook, features, benefits, social proof, CTA (400-600 words)",
  "bullet_points": ["benefit-first bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "category": "product category",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"],
  "price": "XX.XX",
  "compare_at_price": "XX.XX",
  "price_strategy": "why this price works",
  "upsell_ideas": ["upsell 1", "upsell 2"],
  "cross_sell_ideas": ["related product 1", "related product 2"],
  "image_suggestions": ["describe ideal image 1", "describe image 2", "lifestyle shot description"],
  "unique_selling_proposition": "one sentence USP",
  "target_customer_avatar": "who buys this and why",
  "why_it_sells": ["reason 1", "reason 2", "reason 3"],
  "launch_strategy": "recommended approach to launch this product",
  "seo_title": "{seo_brief.get('primary_keyword', product_name) if isinstance(seo_brief, dict) else product_name} - meta title",
  "meta_description": "150-160 char meta description"
}}
""")
        save_output("product_agent", f"listing_{product_name}", result, "json")
        return result

    def analyze_competitor_products(self, competitor_url: str) -> dict:
        """Browse a competitor site and extract their product strategy."""
        console.print(f"\n[green]SCOUT analyzing competitor:[/green] {competitor_url}")
        page = fetch_page(competitor_url)

        result = self.client.ask_json(f"""
Analyze this competitor's product strategy from their website:
URL: {competitor_url}
Title: {page.get('title')}
Content: {page.get('text', '')[:4000]}
Links: {[l['text'] for l in page.get('links', [])[:20]]}

Return JSON:
{{
  "competitor_name": "...",
  "apparent_niche": "...",
  "price_positioning": "budget|mid|premium",
  "top_products_identified": ["product 1", "product 2", "product 3"],
  "their_usp": "...",
  "content_strengths": ["strength 1", "strength 2"],
  "exploitable_weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "keywords_they_target": ["kw1", "kw2", "kw3"],
  "opportunities_for_us": ["opportunity 1", "opportunity 2", "opportunity 3"],
  "threat_level": "low|medium|high"
}}
""")
        save_output("product_agent", f"competitor_{competitor_url[:30]}", result, "json")
        return result

    def source_products_from_supplier(self, niche: str = None, supplier_url: str = None, max_steps: int = None) -> dict:
        """
        Use an observe-plan-act browser loop to source real products from supplier sites.

        The AI can decide the next browser action after each snapshot, but execution is
        limited to safe Agent Browser actions handled by BrowserActionRunner.
        """
        niche = niche or self.niche
        supplier_url = supplier_url or os.getenv("DEFAULT_SUPPLIER_URL", "https://cjdropshipping.com")
        max_steps = max_steps or int(os.getenv("SUPPLIER_SOURCE_MAX_STEPS", "10"))
        console.print(f"\n[green]SCOUT sourcing supplier products:[/green] {niche} from {supplier_url}")

        memory = SwarmMemory({
            "goal": f"Find supplier products for {niche}",
            "niche": niche,
            "supplier_url": supplier_url,
            "ranking_rules": {
                "prefer": "high order/review volume with strong rating and cheap source price",
                "avoid": "perfect ratings with tiny sample sizes",
                "minimum_order_signal": 100,
            },
            "product_candidates": [],
        })

        runner = BrowserActionRunner(AgentBrowser)
        runner.run_step({"action": "open", "url": supplier_url}, memory)

        loop = BrowserPlannerLoop(self.client, runner, max_steps=max_steps)
        loop_result = loop.run(
            goal=(
                f"Search this supplier for {niche}. Extract product name, source price, "
                "rating, review count, order count, product URL, and anything useful for resale."
            ),
            memory=memory,
        )

        candidates = memory.get("product_candidates", [])
        for candidate in candidates:
            candidate["source_score"] = score_product_candidate(candidate)
        candidates = sorted(candidates, key=lambda item: item.get("source_score", 0), reverse=True)
        best_product = candidates[0] if candidates else None
        memory.set("best_product", best_product)
        memory.set("handoff", {"from": "SCOUT", "to": "FORGE", "status": "ready_for_upload" if best_product else "needs_review"})

        result = {
            "niche": niche,
            "supplier_url": supplier_url,
            "best_product": best_product,
            "product_candidates": candidates,
            "browser_loop": loop_result,
            "swarm_memory": memory.data,
        }
        save_output("product_agent", f"supplier_sourcing_{niche}", result, "json")
        return result

    def run_interactive(self):
        console.print(Panel(
            "[bold green]SCOUT — Product Research Agent[/bold green]\n[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="green"
        ))
        while True:
            console.print("\n[yellow]Options:[/yellow]")
            console.print("  1. Research niche for winning products")
            console.print("  2. Create full product listing")
            console.print("  3. Analyze competitor products")
            console.print("  4. Source supplier products with browser loop")
            console.print("  5. Scout & push new products to store")
            console.print("  6. Exit")
            choice = input("\nChoice: ").strip()

            if choice == "1":
                niche = input(f"Niche [{self.niche}]: ").strip() or self.niche
                num_input = input("Amount of products [5]: ").strip()
                num_products = int(num_input) if num_input.isdigit() else 5
                genre = input("Specific genre/type (optional): ").strip()
                result = self.research_niche(niche, num_products, genre)
                console.print(Panel(str(result), title="Niche Research", border_style="green"))
            elif choice == "2":
                name = input("Product name: ").strip()
                url = input("Competitor product URL (optional): ").strip()
                result = self.create_product_listing(name, url or None)
                console.print(Panel(str(result), title="Product Listing", border_style="green"))
            elif choice == "3":
                url = input("Competitor URL: ").strip()
                result = self.analyze_competitor_products(url)
                console.print(Panel(str(result), title="Competitor Analysis", border_style="yellow"))
            elif choice == "4":
                niche = input(f"Niche [{self.niche}]: ").strip() or self.niche
                supplier = input("Supplier URL [https://cjdropshipping.com]: ").strip() or "https://cjdropshipping.com"
                result = self.source_products_from_supplier(niche, supplier)
                console.print(Panel(str(result.get("best_product")), title="Best Supplier Product", border_style="green"))
            elif choice == "5":
                from agents.store_manager_agent import StoreManagerAgent
                niche = input(f"Niche [{self.niche}]: ").strip() or self.niche
                num_input = input("Number of products to scout [5]: ").strip()
                num_products = int(num_input) if num_input.isdigit() else 5
                genre = input("Specific genre/type (optional): ").strip() or None
                result = StoreManagerAgent().scout_and_upload(niche, num_products, genre)
                console.print(Panel(str(result), title="Scout & Upload Result", border_style="green"))
            elif choice == "6":
                break


if __name__ == "__main__":
    agent = ProductAgent()
    agent.run_interactive()
