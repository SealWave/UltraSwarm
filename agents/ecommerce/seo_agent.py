"""
agents/seo_agent.py
===================
SEO Agent — The Intelligence Core
Used standalone AND as a dependency by: Product, Ads, Social, Banner agents.
Superpower: Live web research + keyword intelligence + competitor analysis.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import make_client
from tools.browser import google_search, fetch_page, get_seo_data
from tools.output_manager import save_output
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()
console = Console()

SEO_SYSTEM_PROMPT = """
You are SERAPH — Senior E-commerce SEO Intelligence Agent.

Your identity: You are a world-class SEO strategist with 15+ years of e-commerce
experience. You think like Google's algorithm, feel like a conversion copywriter,
and reason like a data scientist. You do not guess — you research, analyze, and
synthesize intelligence into actionable strategy.

Data Format Note:
━━━━━━━━━━━━━━━━
Web research data is provided as an AI-friendly Accessibility Tree Snapshot from a live browser.
It uses markers like [button "Name"] or [link "Name"] to represent elements.
Use this rich structural data to understand page layout, content hierarchy, and intent.

Emoji Policy:
━━━━━━━━━━━━
Do NOT use emojis under any circumstances in metadata, title tags, meta descriptions, or on-page recommendations. Emojis are strictly prohibited here.

Product Type Adaptation:
━━━━━━━━━━━━━━━━━━━━━━━
Adapt all SEO plans and keywords based on product type:
- SaaS / Subscription Products: Focus on informational & commercial keywords (comparison, reviews, features, integrations, guides), search intent surrounding solutions to workflows, high-intent transactional words ("buy", "pricing", "sign up"), and onboarding/retention signals.
- Regular / Physical Products: Focus on transactional product keywords (buy, shop, discounts, reviews), physical attributes (size, material, durability), search intent surrounding aesthetics, packaging, shipping, and comparison with other physical alternatives.

Your Core Capabilities:
━━━━━━━━━━━━━━━━━━━━━━
1. KEYWORD INTELLIGENCE
   - Identify primary, secondary, and long-tail keywords
   - Analyze search intent (informational, navigational, transactional, commercial)
   - Map keywords to funnel stages (awareness -> consideration -> purchase)
   - Identify keyword difficulty vs. opportunity score
   - Find semantic keyword clusters (LSI keywords)

2. COMPETITOR ANALYSIS
   - Reverse-engineer competitor ranking strategies
   - Identify content gaps and blue-ocean opportunities
   - Analyze competitor product naming, descriptions, and metadata
   - Find weaknesses to exploit in their SEO structure

3. ON-PAGE OPTIMIZATION
   - Generate SEO-optimized title tags (50-60 chars), meta descriptions (150-160 chars)
   - Create header hierarchies (H1 -> H6) with strategic keyword placement
   - Write product descriptions with semantic richness and buyer intent signals
   - Optimize image alt texts, URL slugs, and schema markup recommendations

4. CONTENT STRATEGY
   - Identify blog topics that drive organic traffic to product pages
   - Create internal linking strategies
   - Design pillar-cluster content architecture
   - Write SEO briefs for content agents

5. TECHNICAL SEO SIGNALS
   - Page speed recommendations
   - Mobile optimization guidance
   - Core Web Vitals improvement strategies
   - Structured data / rich snippet opportunities

Output Standards:
━━━━━━━━━━━━━━━━
- Always provide PRIMARY keyword + 5 secondary + 10 long-tail variations
- Always include search volume estimates (low/medium/high/very-high)
- Always give competitor gap analysis when URLs are provided
- Format outputs as structured reports with clear sections
- Include confidence scores for all recommendations
- Provide "Quick Win" vs "Long-term" classification for every action item

When called by other agents, provide a compact SEO_BRIEF containing:
- Top 3 keywords to target
- Recommended title format
- 3 semantic keyword clusters
- Top 2 competitor insights
- One critical on-page optimization action

You are SERAPH. Be precise. Be strategic. Be ruthless about ranking.
"""


class SEOAgent:

    def __init__(self):
        self.client = make_client(SEO_SYSTEM_PROMPT, "SERAPH-SEO", api_key=os.getenv("GOOGLE_API_KEY"))
        self.store_url = os.getenv("STORE_URL", "")
        self.niche = os.getenv("STORE_NICHE", "general")
        self.primary_kw = os.getenv("PRIMARY_KEYWORD", "")
        self.competitors = os.getenv("COMPETITOR_SITES", "").split(",")

    def research_keyword(self, keyword: str) -> dict:
        """Full keyword + competitor research for a given keyword."""
        console.print(f"\n[cyan]SERAPH researching:[/cyan] {keyword}")

        # Live research
        seo_data = get_seo_data(keyword, self.store_url)
        serp_text = "\n".join([
            f"- {r['title']}: {r['snippet']}" for r in seo_data["serp_results"][:8]
        ])
        community_text = "\n".join([
            f"- {r['title']}: {r['snippet']}" for r in seo_data["community_discussions"][:5]
        ])

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        prompt = f"""
Conduct a deep SEO analysis for the keyword: "{keyword}"

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

LIVE SERP DATA (current top results):
{serp_text}

COMMUNITY DISCUSSIONS (Reddit/Quora):
{community_text}

Store niche: {self.niche}
Store URL: {self.store_url}
Competitors: {', '.join(self.competitors)}

Deliver a full SEO Intelligence Report with:
1. Keyword Analysis (primary, secondary x5, long-tail x10, search intent, volume estimates)
2. SERP Landscape Analysis (who dominates, why, what's their angle)
3. Content Gaps & Opportunities (what's missing from current results)
4. On-Page Optimization Blueprint (title tags, meta, H1-H3 structure, URL slug)
5. Competitor Weaknesses to Exploit
6. Quick Wins (implement in 1 week) vs Long-term Plays (1-3 months)
7. SEO_BRIEF (compact version for other agents to use)
"""
        result = self.client.ask(prompt)
        save_output("seo_agent", f"keyword_{keyword}", result)
        return {"keyword": keyword, "report": result, "raw_data": seo_data}

    def analyze_product_seo(self, product_name: str, product_description: str = "") -> dict:
        """Optimize SEO for a specific product listing."""
        console.print(f"\n[cyan]SERAPH analyzing product:[/cyan] {product_name}")

        search_results = google_search(f"{product_name} buy online review", 8)
        serp_text = "\n".join([f"- {r['title']}: {r['snippet']}" for r in search_results])

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Perform product SEO optimization for: "{product_name}"

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

Product description provided: {product_description or 'None - generate from product name'}

SERP landscape:
{serp_text}

Store niche: {self.niche}

Return JSON with:
{{
  "seo_title": "optimized title tag 50-60 chars",
  "meta_description": "compelling meta 150-160 chars with CTA",
  "h1": "product page H1",
  "h2_tags": ["h2 one", "h2 two", "h2 three"],
  "url_slug": "seo-friendly-slug",
  "primary_keyword": "main keyword",
  "secondary_keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"],
  "long_tail_keywords": ["long kw1", "long kw2", "long kw3", "long kw4", "long kw5"],
  "image_alt_texts": ["alt1", "alt2", "alt3"],
  "schema_type": "Product",
  "content_recommendations": "paragraph of on-page content advice",
  "quick_wins": ["action1", "action2", "action3"],
  "seo_score_estimate": "X/100",
  "competitor_gap": "what competitors are missing that we can own"
}}
""")
        save_output("seo_agent", f"product_{product_name}", result, "json")
        return result

    def get_seo_brief(self, topic: str) -> dict:
        """
        Compact SEO brief for other agents.
        Called by: Product Agent, Ads Agent, Social Agent, Banner Agent.
        """
        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Generate a compact SEO_BRIEF for: "{topic}"
Niche: {self.niche}

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

Return JSON with:
{{
  "primary_keyword": "...",
  "secondary_keywords": ["kw1", "kw2", "kw3"],
  "long_tail": ["lt1", "lt2", "lt3"],
  "search_intent": "transactional|informational|commercial",
  "recommended_title_format": "...",
  "semantic_clusters": ["cluster1", "cluster2", "cluster3"],
  "power_words": ["word1", "word2", "word3"],
  "avoid_keywords": ["bad kw1", "bad kw2"],
  "competitor_insight": "one key insight",
  "cta_language": "Buy Now|Shop Now|Get Yours|etc"
}}
""")
        return result

    def competitor_deep_dive(self, competitor_url: str) -> dict:
        """Scrape and analyze a competitor's SEO strategy."""
        console.print(f"\n[cyan]SERAPH analyzing competitor:[/cyan] {competitor_url}")
        page = fetch_page(competitor_url)

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask(f"""
Analyze this competitor's SEO strategy based on their page content:

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

URL: {competitor_url}
Title: {page.get('title', 'N/A')}
Content snapshot:
{page.get('text', '')[:3000]}

Links found: {len(page.get('links', []))}

Provide:
1. Their apparent keyword strategy
2. Content structure analysis
3. Their strengths we must match
4. Their WEAKNESSES we can exploit
5. 5 specific actions to outrank them
6. Estimated keyword targets they're going after
""")
        save_output("seo_agent", f"competitor_{competitor_url[:30]}", result)
        return {"competitor": competitor_url, "analysis": result}

    def run_interactive(self):
        """Interactive CLI mode for standalone use."""
        console.print(Panel(
            "[bold cyan]SERAPH — SEO Intelligence Agent[/bold cyan]\n"
            "[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="cyan"
        ))

        while True:
            console.print("\n[yellow]Options:[/yellow]")
            console.print("  1. Keyword research")
            console.print("  2. Analyze product SEO")
            console.print("  3. Competitor deep dive")
            console.print("  4. Get SEO brief (for another agent)")
            console.print("  5. Exit")

            choice = input("\nChoice: ").strip()

            if choice == "1":
                kw = input("Enter keyword: ").strip()
                result = self.research_keyword(kw)
                console.print(Panel(result["report"], title=f"SEO Report: {kw}", border_style="green"))

            elif choice == "2":
                name = input("Product name: ").strip()
                desc = input("Description (optional, press Enter to skip): ").strip()
                result = self.analyze_product_seo(name, desc)
                console.print(Panel(str(result), title="Product SEO", border_style="green"))

            elif choice == "3":
                url = input("Competitor URL: ").strip()
                result = self.competitor_deep_dive(url)
                console.print(Panel(result["analysis"], title="Competitor Analysis", border_style="red"))

            elif choice == "4":
                topic = input("Topic/product: ").strip()
                brief = self.get_seo_brief(topic)
                console.print(Panel(str(brief), title="SEO Brief", border_style="blue"))

            elif choice == "5":
                break


# ── Standalone entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = SEOAgent()
    agent.run_interactive()
