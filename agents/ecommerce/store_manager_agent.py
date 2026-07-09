"""
agents/store_manager_agent.py
==============================
FORGE — Store Operations & Product Management Agent
Superpower: Directly creates products on Shopify/WooCommerce,
manages inventory strategy, pricing, and store optimization.
Uses output from other agents to push live to the store.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import make_client
from tools.browser import AgentBrowser
from tools.browser_actions import BrowserActionRunner, BrowserPlannerLoop
from tools.store_admin import ShopifyAdmin, WooCommerceAdmin, format_product_for_store, normalize_product_for_handoff, validate_product_for_upload
from tools.output_manager import save_output, load_latest
from tools.swarm_memory import SwarmMemory
from agents.seo_agent import SEOAgent
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()
console = Console()

STORE_MANAGER_SYSTEM_PROMPT = """
You are FORGE — E-commerce Store Operations & Growth Manager Agent.

Your identity: You are the operational brain of an e-commerce business. You have
managed stores generating $1M+ per month. You understand that a great product on
a poorly optimized store page is a failed product. You bridge the gap between
creative output and store performance — transforming agent-generated content into
live, revenue-generating store assets.

Emoji Policy:
━━━━━━━━━━━━
Do NOT use emojis under any circumstances in launch plans, checklists, email marketing copy, or page optimization briefs. Emojis are strictly prohibited here.

Product Type Adaptation:
━━━━━━━━━━━━━━━━━━━━━━
Adapt operational launch setup and settings based on product type:
- SaaS / Subscription Products: Focus on subscription billing setup (recurrences, payment gateways), free trial policies, integrations with other SaaS/APIs, customer portals, user dashboard links, digital terms of service, and SLA/support trust badges.
- Regular / Physical Products: Focus on inventory tracking settings, shipping zones and rates, physical variants (size, color, material), fulfillment configurations, physical product dimensions, and return/refund policy placement.

Your Core Capabilities:
━━━━━━━━━━━━━━━━━━━━━━
1. PRODUCT LAUNCH MANAGEMENT
   - Coordinate full product launch sequence (SEO -> Product -> Ads -> Social)
   - Create launch checklists with priority order
   - Manage product variants, options, and inventory settings
   - Set up pricing strategies (base, compare-at, bundle)
   - Configure product metadata and attributes

2. STORE OPTIMIZATION
   - Homepage layout recommendations
   - Navigation structure optimization
   - Collection/category organization strategy
   - Search functionality optimization
   - Mobile shopping experience improvements
   - Page speed recommendations
   - Trust signal placement (reviews, badges, guarantees)

3. CRO (CONVERSION RATE OPTIMIZATION)
   - Product page conversion checklist
   - Cart abandonment reduction strategies
   - Checkout optimization recommendations
   - Upsell/cross-sell placement strategy
   - Social proof integration (reviews, UGC, testimonials)
   - Urgency and scarcity implementation

4. INVENTORY & PRICING STRATEGY
   - Pricing psychology (charm pricing, anchoring, bundles)
   - Inventory management signals
   - Low stock urgency triggers
   - Bundle and kit strategy
   - Seasonal pricing recommendations

5. STORE HEALTH MONITORING
   - Identify underperforming products
   - Content freshness recommendations
   - Dead link and error identification
   - SEO audit of existing products
   - Competitor price monitoring strategy

6. EMAIL MARKETING INTEGRATION
   - Welcome sequence copy
   - Abandoned cart email copy
   - Post-purchase email sequence
   - Win-back campaign copy
   - Product launch announcement emails

Output Standards:
━━━━━━━━━━━━━━━━
Every store operation output includes:
- Priority ranking (do this FIRST, SECOND, THIRD)
- Platform-specific instructions (Shopify vs. WooCommerce)
- Expected impact on revenue/conversions
- Time to implement estimate
- Success metrics to track

You are FORGE. Build the store. Convert the traffic. Grow the revenue.
"""


class StoreManagerAgent:

    def __init__(self):
        self.client = make_client(STORE_MANAGER_SYSTEM_PROMPT, "FORGE-StoreManager", api_key=os.getenv("GOOGLE_API_KEY_3"))
        self.seo_agent = SEOAgent()
        self.store_url = os.getenv("STORE_URL", "")
        self.store_name = os.getenv("STORE_NAME", "My Store")
        self.niche = os.getenv("STORE_NICHE", "general")
        self.platform = "shopify"  # or "woocommerce"

        # Optional: live admin connections
        self._shopify = None
        self._woo = None

    def _get_shopify(self) -> ShopifyAdmin:
        if not self._shopify:
            shop = os.getenv("SHOPIFY_SHOP_URL", "")
            token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
            if shop and token:
                self._shopify = ShopifyAdmin(shop, token)
        return self._shopify

    def _select_product_payload(self, data: dict) -> dict:
        """Pick the most upload-ready product object from an agent output."""
        if not isinstance(data, dict):
            return {}
        if isinstance(data.get("best_product"), dict):
            return data["best_product"]
        if isinstance(data.get("product"), dict):
            return data["product"]
        products = data.get("products")
        if isinstance(products, list) and products:
            top_pick = str(data.get("top_pick", "")).lower()
            for product in products:
                if isinstance(product, dict) and top_pick and str(product.get("product_name", "")).lower() == top_pick:
                    return product
            if isinstance(products[0], dict):
                return products[0]
        return data

    def plan_product_launch(self, product_name: str, product_data: dict = None) -> dict:
        """Generate a complete product launch plan."""
        console.print(f"\n[red]FORGE planning launch:[/red] {product_name}")

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create a complete product launch plan for: "{product_name}"
Store: {self.store_name} | Platform: {self.platform} | Niche: {self.niche}
Product data available: {bool(product_data)}

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

Return JSON:
{{
  "product_name": "{product_name}",
  "launch_timeline": {{
    "day_minus_7": "pre-launch tasks",
    "day_minus_3": "countdown preparation",
    "launch_day": "day of launch checklist",
    "day_plus_1_7": "post-launch optimization",
    "day_plus_30": "performance review"
  }},
  "store_page_checklist": [
    {{"task": "...", "priority": "critical|high|medium", "platform_steps": "...", "expected_impact": "..."}},
    {{"task": "...", "priority": "...", "platform_steps": "...", "expected_impact": "..."}},
    {{"task": "...", "priority": "...", "platform_steps": "...", "expected_impact": "..."}},
    {{"task": "...", "priority": "...", "platform_steps": "...", "expected_impact": "..."}},
    {{"task": "...", "priority": "...", "platform_steps": "...", "expected_impact": "..."}}
  ],
  "pricing_strategy": {{
    "recommended_price": "...",
    "compare_at_price": "...",
    "psychological_reasoning": "...",
    "bundle_idea": "...",
    "introductory_offer": "..."
  }},
  "page_optimization": {{
    "hero_image_direction": "...",
    "description_structure": "how to structure the product page",
    "trust_signals_to_add": ["signal1", "signal2", "signal3"],
    "upsell_placement": "...",
    "cross_sell_placement": "..."
  }},
  "email_sequence": {{
    "launch_announcement": "subject line + first line",
    "day_3_followup": "subject line + first line",
    "urgency_email": "subject line + first line"
  }},
  "kpis_to_track": ["kpi1", "kpi2", "kpi3", "kpi4"],
  "success_definition": "what metrics indicate a successful launch at 30 days"
}}
""")
        save_output("store_manager", f"launch_plan_{product_name}", result, "json")
        return result

    def optimize_store(self) -> dict:
        """Audit and optimize the entire store."""
        console.print(f"\n[red]FORGE auditing store:[/red] {self.store_url}")

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create a complete store optimization roadmap for:
Store: {self.store_name} | URL: {self.store_url}
Platform: {self.platform} | Niche: {self.niche}

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

Return JSON:
{{
  "overall_health_score": "X/100",
  "critical_fixes": [
    {{"issue": "...", "impact": "...", "fix": "...", "time_estimate": "X hours"}}
  ],
  "high_impact_improvements": [
    {{"area": "...", "improvement": "...", "expected_lift": "+X% conversion", "priority": 1}}
  ],
  "homepage_recommendations": ["rec1", "rec2", "rec3"],
  "product_page_template": "recommended structure for product pages",
  "navigation_structure": {{
    "main_menu": ["menu item 1", "menu item 2", "menu item 3"],
    "footer_links": ["footer 1", "footer 2", "footer 3"]
  }},
  "trust_signals_checklist": [
    {{"signal": "...", "placement": "...", "status": "required|recommended"}}
  ],
  "cro_quick_wins": ["win1", "win2", "win3", "win4", "win5"],
  "30_day_roadmap": [
    {{"week": 1, "focus": "...", "tasks": ["...", "...", "..."]}},
    {{"week": 2, "focus": "...", "tasks": ["...", "...", "..."]}},
    {{"week": 3, "focus": "...", "tasks": ["...", "...", "..."]}},
    {{"week": 4, "focus": "...", "tasks": ["...", "...", "..."]}}
  ]
}}
""")
        save_output("store_manager", "store_audit", result, "json")
        return result

    def push_product_to_store(self, product_data: dict) -> dict:
        """
        Push a product to Shopify or WooCommerce.
        Formats agent output into store API format or falls back to browser automation.
        """
        product_data = normalize_product_for_handoff(product_data)
        valid, missing = validate_product_for_upload(product_data)
        if not valid:
            return {"success": False, "error": "missing_required_product_fields", "missing": missing}

        console.print(f"\n[red]FORGE pushing to store:[/red] {product_data.get('product_name', 'product')}")

        shopify = self._get_shopify()
        if shopify:
            formatted = format_product_for_store(product_data, "shopify")
            result = shopify.create_product(formatted)
            console.print(f"[green]Product pushed to Shopify![/green]")
            save_output("store_manager", "pushed_product", result, "json")
            return result
        else:
            # Fallback to browser automation
            from tools.store_admin import create_product_via_browser
            console.print("[yellow]No store API configured. Attempting browser admin login & automation...[/yellow]")
            result = create_product_via_browser(product_data)
            if result.get("success"):
                console.print(f"[green]Product pushed successfully via browser automation![/green]")
                save_output("store_manager", "pushed_product_browser", result, "json")
                return result
            else:
                console.print(f"[red]Browser automation failed: {result.get('error')}. Saving formatted product data.[/red]")
                formatted = format_product_for_store(product_data, self.platform)
                save_output("store_manager", "formatted_product", formatted, "json")
                return formatted

    def push_product_to_custom_admin(self, product_data: dict, admin_url: str = None, max_steps: int = None) -> dict:
        """
        Add a product through a custom admin UI using the observe-plan-act browser loop.

        This is for non-Shopify/non-WooCommerce admin pages where fields may be
        ordered differently or use custom labels.
        """
        product_data = normalize_product_for_handoff(product_data)
        valid, missing = validate_product_for_upload(product_data)
        if not valid:
            return {"success": False, "error": "missing_required_product_fields", "missing": missing}

        admin_url = admin_url or os.getenv("STORE_ADMIN_URL", "")
        max_steps = max_steps or int(os.getenv("CUSTOM_ADMIN_MAX_STEPS", "12"))
        username = os.getenv("STORE_ADMIN_USER", "")
        password = os.getenv("STORE_ADMIN_PASS", "")
        if not admin_url:
            return {"success": False, "error": "STORE_ADMIN_URL is not configured"}

        console.print(f"\n[red]FORGE opening custom admin:[/red] {admin_url}")
        memory = SwarmMemory({
            "goal": "Add product to custom ecommerce admin page",
            "product": product_data,
            "admin_url": admin_url,
            "admin_credentials": {
                "username": username,
                "password_available": bool(password),
            },
            "field_hints": {
                "title": ["product name", "title", "name"],
                "description": ["description", "body", "details"],
                "price": ["price", "regular price", "amount"],
                "category": ["category", "collection", "type"],
                "tags": ["tags", "keywords"],
                "save": ["save", "publish", "create", "submit"],
            },
        })

        runner = BrowserActionRunner(AgentBrowser)
        runner.run_step({"action": "open", "url": admin_url}, memory)

        if username and password:
            memory.set("admin_credentials.username_value", username)
            memory.set("admin_credentials.password_value", password)

        loop = BrowserPlannerLoop(self.client, runner, max_steps=max_steps)
        result = loop.run(
            goal=(
                "Log in if needed, then create a product in the custom admin page. "
                "Use the product data from memory. Find fields by labels, placeholders, "
                "roles, and nearby text. Confirm the page shows the product was saved."
            ),
            memory=memory,
        )

        output = {
            "success": result.get("success", False),
            "method": "custom_admin_browser_loop",
            "product_name": product_data.get("product_name"),
            "admin_url": admin_url,
            "browser_loop": result,
            "swarm_memory": memory.data,
        }
        save_output("store_manager", "custom_admin_upload", output, "json")
        return output

    def get_existing_products(self, admin_url: str = None, max_steps: int = None) -> list[str]:
        """
        Browse the store admin products page and return a list of existing product names.
        Uses FORGE's browser loop to snapshot the products listing page.
        """
        admin_url = admin_url or os.getenv("STORE_ADMIN_URL", "")
        max_steps = max_steps or int(os.getenv("CUSTOM_ADMIN_MAX_STEPS", "12"))
        username = os.getenv("STORE_ADMIN_USER", "")
        password = os.getenv("STORE_ADMIN_PASS", "")

        if not admin_url:
            console.print("[yellow]FORGE: No STORE_ADMIN_URL set — skipping existing product check.[/yellow]")
            return []

        console.print(f"\n[red]FORGE reading existing products from admin:[/red] {admin_url}")
        memory = SwarmMemory({
            "goal": "Read all existing product names from the store admin products list",
            "admin_url": admin_url,
            "admin_credentials": {"username": username, "password_available": bool(password)},
            "existing_product_names": [],
        })
        if username and password:
            memory.set("admin_credentials.username_value", username)
            memory.set("admin_credentials.password_value", password)

        runner = BrowserActionRunner(AgentBrowser)
        runner.run_step({"action": "open", "url": admin_url}, memory)

        loop = BrowserPlannerLoop(self.client, runner, max_steps=max_steps)
        loop.run(
            goal=(
                "Log in if needed. Navigate to the products list page. "
                "Extract all product names/titles visible on the page into memory key 'existing_product_names' using a note action. "
                "Format: {\"action\": \"note\", \"text\": \"PRODUCT_LIST: Product A, Product B, Product C\"}"
            ),
            memory=memory,
        )

        # Parse product names from notes
        names: list[str] = []
        for note in memory.get("browser_notes", []):
            if isinstance(note, str) and note.startswith("PRODUCT_LIST:"):
                raw = note.replace("PRODUCT_LIST:", "").strip()
                names = [n.strip() for n in raw.split(",") if n.strip()]
                break

        # Also check if memory has them directly
        direct = memory.get("existing_product_names", [])
        if isinstance(direct, list):
            names = list(set(names + [str(n) for n in direct if n]))

        console.print(f"[dim]FORGE found {len(names)} existing products.[/dim]")
        return names

    def scout_and_upload(self, niche: str = None, num_products: int = 5, genre: str = None) -> dict:
        """
        Full SCOUT → FORGE pipeline:
        1. FORGE reads existing products from admin.
        2. SCOUT researches the niche and creates full listings.
        3. New products (not already in store) are pushed to admin via browser automation.
        """
        from agents.product_agent import ProductAgent

        niche = niche or self.niche
        console.print(f"\n[bold red]FORGE + SCOUT pipeline starting[/bold red] | niche: {niche}")

        # Step 1: Read what's already in the store
        existing = self.get_existing_products()
        existing_lower = {name.lower() for name in existing}

        # Step 2: SCOUT finds products
        scout = ProductAgent()
        research = scout.research_niche(niche, num_products, genre)
        products = research.get("products", [])

        if not products:
            return {"success": False, "error": "SCOUT returned no products", "niche": niche}

        # Step 3: Filter to only new products
        new_products = [
            p for p in products
            if p.get("product_name", "").lower() not in existing_lower
        ]
        console.print(f"[dim]SCOUT found {len(products)} products. {len(new_products)} are new.[/dim]")

        if not new_products:
            return {"success": True, "message": "No new products to upload — all already exist in store.", "existing": existing}

        # Step 4: Create full listings + push each new product
        upload_results = []
        for candidate in new_products:
            product_name = candidate.get("product_name", "")
            console.print(f"\n[green]SCOUT building listing for:[/green] {product_name}")
            listing = scout.create_product_listing(product_name, candidate.get("product_url"))
            result = self.push_product_to_custom_admin(listing)
            upload_results.append({
                "product_name": product_name,
                "upload_result": result,
            })
            status = "[green]OK[/green]" if result.get("success") else "[red]FAILED[/red]"
            console.print(f"  -> Upload {status}: {product_name}")

        summary = {
            "niche": niche,
            "existing_products": existing,
            "new_products_found": len(new_products),
            "upload_results": upload_results,
            "success": True,
        }
        save_output("store_manager", f"scout_upload_{niche}", summary, "json")
        return summary

    def run_interactive(self):
        console.print(Panel(
            "[bold red]FORGE — Store Manager Agent[/bold red]\n[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="red"
        ))
        while True:
            console.print("\n[yellow]Options:[/yellow]")
            console.print("  1. Plan product launch")
            console.print("  2. Optimize store (full audit)")
            console.print("  3. Push product to store")
            console.print("  4. Push product to custom admin page")
            console.print("  5. Scout & auto-upload new products")
            console.print("  6. Exit")
            choice = input("\nChoice: ").strip()

            if choice == "1":
                name = input("Product name: ").strip()
                result = self.plan_product_launch(name)
                console.print(Panel(str(result), title="Launch Plan", border_style="red"))
            elif choice == "2":
                result = self.optimize_store()
                console.print(Panel(str(result), title="Store Audit", border_style="red"))
            elif choice == "3":
                latest = load_latest("product_agent")
                if latest:
                    import json
                    try:
                        data = json.loads(latest)
                        result = self.push_product_to_store(self._select_product_payload(data))
                        console.print(Panel(str(result), title="Product Pushed", border_style="green"))
                    except Exception:
                        console.print("[red]Could not load latest product data.[/red]")
                else:
                    console.print("[yellow]No product data found. Run Product Agent first.[/yellow]")
            elif choice == "4":
                latest = load_latest("product_agent")
                if latest:
                    import json
                    try:
                        data = json.loads(latest)
                        result = self.push_product_to_custom_admin(self._select_product_payload(data))
                        console.print(Panel(str(result), title="Custom Admin Upload", border_style="green"))
                    except Exception:
                        console.print("[red]Could not load latest product data.[/red]")
                else:
                    console.print("[yellow]No product data found. Run Product Agent first.[/yellow]")
            elif choice == "5":
                niche = input(f"Niche [{self.niche}]: ").strip() or self.niche
                num_input = input("Number of products to scout [5]: ").strip()
                num_products = int(num_input) if num_input.isdigit() else 5
                genre = input("Specific genre/type (optional): ").strip() or None
                result = self.scout_and_upload(niche, num_products, genre)
                console.print(Panel(str(result), title="Scout & Upload Result", border_style="green"))
            elif choice == "6":
                break


if __name__ == "__main__":
    agent = StoreManagerAgent()
    agent.run_interactive()
