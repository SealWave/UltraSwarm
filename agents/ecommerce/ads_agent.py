"""
agents/ads_agent.py
====================
PULSE — Paid Advertising Copy & Strategy Agent
Superpower: Creates high-converting ad copy for Google Ads, Meta (FB/IG),
TikTok Ads, Pinterest — all informed by live SEO + competitor intelligence.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import make_client
from tools.browser import google_search, fetch_page
from tools.output_manager import save_output
from agents.seo_agent import SEOAgent
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()
console = Console()

ADS_SYSTEM_PROMPT = """
You are PULSE — Elite Paid Advertising & Conversion Copy Agent.

Your identity: You are a performance marketer who has managed $10M+ in ad spend
across Google, Meta, TikTok, and Pinterest. You write copy that stops the scroll,
triggers emotion, and drives action. You think in click-through rates, ROAS,
and cost-per-acquisition. Every word you write earns its place.

Data Format Note:
━━━━━━━━━━━━━━━━
Web research data is provided as an AI-friendly Accessibility Tree Snapshot from a live browser.
It uses markers like [button "Name"] or [link "Name"] to represent elements.
Use this rich structural data to understand competitor ad angles and search results.

Emoji Policy:
━━━━━━━━━━━━
Do NOT use emojis under any circumstances in the ad headlines, primary texts, descriptions, callouts, or sitelinks. Emojis are strictly prohibited here.

Product Type Adaptation:
━━━━━━━━━━━━━━━━━━━━━━
Adapt all ad copy and strategies based on product type:
- SaaS / Subscription Products: Focus on solving specific workflow issues/pains, highlighting quick time-to-value, integrations, scalability, monthly/annual cost efficiency (e.g. ROI), and free trial offers. Headlines should be solution/value-oriented.
- Regular / Physical Products: Focus on visual aesthetics, sensory details, shipping speeds, unboxing experiences, material quality, and physical features. Headlines should be benefit/lifestyle-oriented.

Your Core Capabilities:
━━━━━━━━━━━━━━━━━━━━━━
1. GOOGLE ADS MASTERY
   - Responsive Search Ads (15 headlines x 30 chars, 4 descriptions x 90 chars)
   - Performance Max asset groups
   - Shopping ad titles and descriptions
   - Display ad copy variations
   - Ad extension copy (sitelinks, callouts, structured snippets, promotions)
   - Negative keyword recommendations
   - Bidding strategy recommendations

2. META ADS (FACEBOOK + INSTAGRAM) MASTERY
   - Primary text (125 chars hook + expansion)
   - Headline variations for split testing
   - Description text
   - Cold audience vs. warm retargeting copy differences
   - Story ad scripts (15-sec and 30-sec)
   - Carousel ad copy (per slide)
   - Collection ad copy
   - Audience targeting recommendations

3. TIKTOK ADS MASTERY
   - Hook lines (first 3 seconds — the critical window)
   - UGC-style scripts
   - Trending sound/format recommendations
   - Text overlay copy
   - Spark Ads angle recommendations

4. CONVERSION PSYCHOLOGY
   - Fear of missing out (FOMO) triggers
   - Social proof integration
   - Urgency and scarcity framing
   - Pain-point agitation -> solution reveal
   - Identity-based messaging ("people like you...")
   - Price anchoring and value framing
   - Objection handling in copy

5. A/B TESTING FRAMEWORKS
   - Generate 3-5 variations per ad element
   - Angle matrix (problem-focused, benefit-focused, social proof, curiosity, direct)
   - Test hypothesis for each variation
   - Predicted winner analysis

Output Standards:
━━━━━━━━━━━━━━━━
Every ad campaign output includes:
- Campaign objective recommendation
- Full ad copy for each platform requested
- 3 angle variations minimum
- Audience targeting brief
- Budget allocation recommendation
- KPI targets (CTR, CPC, ROAS estimates)
- A/B test priority order

Character counts are NON-NEGOTIABLE. Always stay within platform limits.
Copy must feel native to each platform — not copy-pasted across them.

You are PULSE. Make every impression count. Every click intentional. Every dollar earn its return.
"""


class AdsAgent:

    def __init__(self):
        self.client = make_client(ADS_SYSTEM_PROMPT, "PULSE-Ads", api_key=os.getenv("GOOGLE_API_KEY_3"))
        self.seo_agent = SEOAgent()
        self.store_name = os.getenv("STORE_NAME", "My Store")
        self.store_url = os.getenv("STORE_URL", "")
        self.audience = os.getenv("TARGET_AUDIENCE", "adults 18-45")
        self.country = os.getenv("TARGET_COUNTRY", "US")
        self.currency = os.getenv("TARGET_CURRENCY", "USD")

    def create_google_ads(self, product_name: str, product_description: str = "",
                          budget: str = "medium") -> dict:
        """Create complete Google Ads campaign assets."""
        console.print(f"\n[magenta]⚡ PULSE creating Google Ads:[/magenta] {product_name}")

        seo_brief = self.seo_agent.get_seo_brief(product_name)
        competitor_ads = google_search(f"{product_name} buy online site:google.com", 5)
        ad_intel = "\n".join([f"- {r['title']}: {r['snippet']}" for r in competitor_ads])

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create a complete Google Ads campaign for: "{product_name}"

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

SEO BRIEF (from SERAPH): {seo_brief}
Competitor ad intelligence: {ad_intel}
Store: {self.store_name} | URL: {self.store_url}
Target audience: {self.audience} | Country: {self.country}
Budget level: {budget}
Product context: {product_description or 'N/A'}

Return JSON:
{{
  "campaign_name": "...",
  "campaign_type": "Search + Shopping",
  "objective": "...",
  "responsive_search_ad": {{
    "headlines": [
      "headline 1 (max 30 chars)",
      "headline 2 (max 30 chars)",
      "headline 3 (max 30 chars)",
      "headline 4 (max 30 chars)",
      "headline 5 (max 30 chars)",
      "headline 6 (max 30 chars)",
      "headline 7 (max 30 chars)",
      "headline 8 (max 30 chars)",
      "headline 9 (max 30 chars)",
      "headline 10 (max 30 chars)"
    ],
    "descriptions": [
      "description 1 (max 90 chars)",
      "description 2 (max 90 chars)",
      "description 3 (max 90 chars)",
      "description 4 (max 90 chars)"
    ],
    "final_url": "{self.store_url}/products/...",
    "display_url_path": ["path1", "path2"]
  }},
  "ad_extensions": {{
    "sitelinks": [
      {{"title": "...", "description": "..."}},
      {{"title": "...", "description": "..."}},
      {{"title": "...", "description": "..."}},
      {{"title": "...", "description": "..."}}
    ],
    "callouts": ["callout1", "callout2", "callout3", "callout4"],
    "structured_snippets": {{"header": "Types", "values": ["type1", "type2", "type3"]}}
  }},
  "keywords": {{
    "exact_match": ["[keyword1]", "[keyword2]", "[keyword3]"],
    "phrase_match": ['"phrase 1"', '"phrase 2"', '"phrase 3"'],
    "broad_match_modifier": ["keyword1", "keyword2"],
    "negative_keywords": ["-negative1", "-negative2", "-negative3"]
  }},
  "budget_recommendation": {{
    "daily_budget": "...",
    "bidding_strategy": "Target ROAS | Maximize Conversions | Manual CPC",
    "target_cpa": "...",
    "target_roas": "..."
  }},
  "shopping_title": "shopping-optimized product title",
  "angle_variations": [
    {{"angle": "problem-focused", "headline": "...", "description": "..."}},
    {{"angle": "benefit-focused", "headline": "...", "description": "..."}},
    {{"angle": "social-proof", "headline": "...", "description": "..."}}
  ],
  "kpi_targets": {{"ctr": "X%", "cpc": "$X", "roas": "Xx"}}
}}
""")
        save_output("ads_agent", f"google_{product_name}", result, "json")
        return result

    def create_meta_ads(self, product_name: str, product_description: str = "",
                        campaign_type: str = "cold") -> dict:
        """Create Facebook/Instagram ad copy suite."""
        console.print(f"\n[magenta]PULSE creating Meta Ads:[/magenta] {product_name}")

        seo_brief = self.seo_agent.get_seo_brief(product_name)

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create a complete Meta (Facebook + Instagram) ad campaign for: "{product_name}"

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

SEO BRIEF: {seo_brief}
Store: {self.store_name}
Target audience: {self.audience}
Campaign type: {campaign_type} (cold audience OR warm retargeting)
Product context: {product_description or 'infer from product name'}

Return JSON:
{{
  "campaign_objective": "Conversions | Traffic | Catalog Sales",
  "primary_ads": [
    {{
      "angle": "Pain Point",
      "primary_text": "hook line (125 chars) + expansion paragraph",
      "headline": "headline (40 chars max)",
      "description": "news feed description (30 chars)",
      "cta_button": "Shop Now | Learn More | Get Offer",
      "creative_direction": "describe the ideal image/video for this ad"
    }},
    {{
      "angle": "Transformation/Result",
      "primary_text": "...",
      "headline": "...",
      "description": "...",
      "cta_button": "...",
      "creative_direction": "..."
    }},
    {{
      "angle": "Social Proof",
      "primary_text": "...",
      "headline": "...",
      "description": "...",
      "cta_button": "...",
      "creative_direction": "..."
    }}
  ],
  "story_ad_script": {{
    "duration": "15 seconds",
    "hook_0_3s": "what appears in first 3 seconds",
    "body_3_12s": "main message",
    "cta_12_15s": "closing call to action",
    "text_overlays": ["overlay 1", "overlay 2"]
  }},
  "carousel_ad": {{
    "intro_card": {{"headline": "...", "description": "..."}},
    "cards": [
      {{"card_num": 1, "headline": "...", "description": "...", "image_direction": "..."}},
      {{"card_num": 2, "headline": "...", "description": "...", "image_direction": "..."}},
      {{"card_num": 3, "headline": "...", "description": "...", "image_direction": "..."}}
    ]
  }},
  "retargeting_copy": {{
    "primary_text": "copy for people who visited but didn't buy",
    "headline": "...",
    "urgency_element": "what urgency/offer to add"
  }},
  "audience_targeting": {{
    "interests": ["interest1", "interest2", "interest3", "interest4", "interest5"],
    "demographics": "age range, gender, income if relevant",
    "behaviors": ["behavior1", "behavior2"],
    "lookalike_seed": "what custom audience to build lookalike from"
  }},
  "budget_split": {{"cold_traffic": "70%", "retargeting": "30%"}},
  "kpi_targets": {{"ctr": "X%", "cpc": "$X", "roas": "Xx", "cpp": "$X"}}
}}
""")
        save_output("ads_agent", f"meta_{product_name}", result, "json")
        return result

    def create_tiktok_ads(self, product_name: str, product_description: str = "") -> dict:
        """Create TikTok ad scripts and copy."""
        console.print(f"\n[magenta]PULSE creating TikTok Ads:[/magenta] {product_name}")

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create TikTok ad scripts for: "{product_name}"
Target audience: {self.audience}

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}
Product context: {product_description or 'infer from product name'}

Return JSON:
{{
  "ugc_scripts": [
    {{
      "style": "Problem → Solution",
      "hook_text": "first 3 seconds (make it scroll-stopping)",
      "script": "full 30-second script with stage directions",
      "text_overlays": ["text 1", "text 2", "text 3"],
      "trending_audio_type": "describe type of audio that fits"
    }},
    {{
      "style": "Before/After Transformation",
      "hook_text": "...",
      "script": "...",
      "text_overlays": ["...", "...", "..."],
      "trending_audio_type": "..."
    }},
    {{
      "style": "Unboxing/Reveal",
      "hook_text": "...",
      "script": "...",
      "text_overlays": ["...", "...", "..."],
      "trending_audio_type": "..."
    }}
  ],
  "spark_ad_brief": "what kind of organic creator content to boost",
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "audience_targeting": {{
    "interests": ["...", "...", "..."],
    "custom_audience": "...",
    "age_range": "..."
  }}
}}
""")
        save_output("ads_agent", f"tiktok_{product_name}", result, "json")
        return result

    def run_interactive(self):
        console.print(Panel(
            "[bold magenta]PULSE — Ads Agent[/bold magenta]\n[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="magenta"
        ))
        while True:
            console.print("\n[yellow]Options:[/yellow]")
            console.print("  1. Google Ads campaign")
            console.print("  2. Meta (Facebook/Instagram) Ads")
            console.print("  3. TikTok Ads")
            console.print("  4. Exit")
            choice = input("\nChoice: ").strip()

            if choice == "1":
                name = input("Product name: ").strip()
                desc = input("Description (optional): ").strip()
                result = self.create_google_ads(name, desc)
                console.print(Panel(str(result), title="Google Ads", border_style="blue"))
            elif choice == "2":
                name = input("Product name: ").strip()
                desc = input("Description (optional): ").strip()
                result = self.create_meta_ads(name, desc)
                console.print(Panel(str(result), title="Meta Ads", border_style="blue"))
            elif choice == "3":
                name = input("Product name: ").strip()
                desc = input("Description (optional): ").strip()
                result = self.create_tiktok_ads(name, desc)
                console.print(Panel(str(result), title="TikTok Ads", border_style="blue"))
            elif choice == "4":
                break


if __name__ == "__main__":
    agent = AdsAgent()
    agent.run_interactive()
