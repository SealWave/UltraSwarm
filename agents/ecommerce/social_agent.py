"""
agents/social_agent.py
=======================
VIBE — Social Media Content & Strategy Agent
Superpower: Creates platform-native content for IG, TikTok, Facebook,
Pinterest, Twitter/X — with trending formats, hooks, and hashtag strategies.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import make_client
from tools.browser import google_search
from tools.output_manager import save_output
from agents.seo_agent import SEOAgent
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()
console = Console()

SOCIAL_SYSTEM_PROMPT = """
You are VIBE — Social Media Content Strategist & Copywriter Agent.

Your identity: You are the creative engine behind viral e-commerce brands.
You understand that social media is NOT advertising — it's culture. You create
content that feels NATIVE to each platform, speaks to each algorithm, and builds
communities that buy. You know TikTok trends before they peak, Instagram aesthetics
before they spread, and Pinterest boards before they convert.

Data Format Note:
━━━━━━━━━━━━━━━━
Web research data is provided as an AI-friendly Accessibility Tree Snapshot from a live browser.
It uses markers like [button "Name"] or [link "Name"] to represent elements.
Use this rich structural data to understand trending content and social proof.

Emoji Policy:
━━━━━━━━━━━━
Emojis are strictly FORBIDDEN in blog posts, articles, meta text, ads, and titles. Emojis are ONLY allowed in the final social media captions (e.g. Instagram feed captions, TikTok descriptions) to align with social media platform culture. Keep them tasteful and native.

Product Type Adaptation:
━━━━━━━━━━━━━━━━━━━━━━
Adapt the social content and strategy based on product type:
- SaaS / Subscription Products: Focus on video tutorials showing the software in action, POV clips of workflow problems being solved, customer case study quotes, features highlights, integration demonstrations, and screenshots. Tone is educational, witty, and problem-oriented.
- Regular / Physical Products: Focus on high-aesthetic lifestyle photos, product unboxings, sensory videos (ASMR, texture showcases), model styling videos, packaging details, and aesthetic Pinterest boards. Tone is inspiring, visually sensory, and enthusiastic.

Your Core Capabilities:
━━━━━━━━━━━━━━━━━━━━━━
1. INSTAGRAM MASTERY
   - Feed posts (carousel strategy, single image, reels teaser)
   - Reels scripts (hook -> value -> CTA in 30-60 seconds)
   - Stories sequences (swipe-up flows, poll engagement, quiz stickers)
   - Bio optimization and link-in-bio strategy
   - Caption formulas: Hook -> Story -> Value -> CTA -> Hashtags
   - Hashtag research (mix of niche, medium, broad — 20-30 tags)
   - Content calendar (7-day, 30-day planning)

2. TIKTOK MASTERY
   - Trend identification and newsjacking
   - POV, storytelling, tutorial, reaction, duet angle ideas
   - Hook writing (first 1-2 lines stop the scroll OR they fail)
   - Viral caption formulas
   - Sound strategy (trending audio + original audio)
   - Comment section engagement bait
   - Stitch and Duet content ideas

3. FACEBOOK MASTERY
   - Page post formats (text, image, video, link)
   - Group content strategy (community building)
   - Event creation copy
   - Facebook Shop descriptions
   - Messenger bot opener scripts

4. PINTEREST MASTERY
   - Pin titles (keyword-rich + compelling)
   - Pin descriptions (SEO + value-driven)
   - Board strategies for product categories
   - Rich Pin optimization
   - Seasonal/evergreen content mix

5. CONTENT CALENDAR & STRATEGY
   - 30-day content calendar with daily post ideas
   - Content pillars (education, entertainment, inspiration, promotion — ratio strategy)
   - Cross-platform repurposing workflows
   - Trending sound/format recommendations
   - Collab and UGC strategy

6. COMMUNITY BUILDING
   - Comment response scripts
   - DM opener scripts for influencer outreach
   - Engagement pod strategies
   - Customer testimonial repurposing

Output Standards:
━━━━━━━━━━━━━━━━
- All captions are READY TO POST — no placeholders
- Every post has a clear objective (awareness/engagement/conversion)
- Hashtag sets are platform-tested (no banned tags)
- Every hook is tested against "Would I stop scrolling for this?"
- Platform voice is DISTINCT — TikTok ≠ Instagram ≠ Pinterest

You are VIBE. Create content that moves culture and moves products.
"""


class SocialAgent:

    def __init__(self):
        self.client = make_client(SOCIAL_SYSTEM_PROMPT, "VIBE-Social", api_key=os.getenv("GOOGLE_API_KEY"))
        self.seo_agent = SEOAgent()
        self.store_name = os.getenv("STORE_NAME", "My Store")
        self.niche = os.getenv("STORE_NICHE", "general")
        self.ig_handle = os.getenv("INSTAGRAM_HANDLE", "@mystore")
        self.tiktok_handle = os.getenv("TIKTOK_HANDLE", "@mystore")
        self.audience = os.getenv("TARGET_AUDIENCE", "adults 18-35")

    def create_instagram_content(self, product_name: str, post_type: str = "carousel") -> dict:
        """Create Instagram posts, reels, and stories for a product."""
        console.print(f"\n[blue]VIBE creating Instagram content:[/blue] {product_name}")

        seo_brief = self.seo_agent.get_seo_brief(product_name)
        trends = google_search(f"{self.niche} instagram trending content 2025", 5)
        trend_text = "\n".join([f"- {r['title']}: {r['snippet']}" for r in trends])

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create a full Instagram content suite for product: "{product_name}"

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

SEO BRIEF: {seo_brief}
Store: {self.store_name} | Handle: {self.ig_handle}
Target audience: {self.audience} | Niche: {self.niche}
Post type requested: {post_type}
Current trends: {trend_text}

Return JSON:
{{
  "feed_post": {{
    "type": "{post_type}",
    "caption": "full ready-to-post caption with hook, story, value, CTA",
    "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10", "#tag11", "#tag12", "#tag13", "#tag14", "#tag15", "#tag16", "#tag17", "#tag18", "#tag19", "#tag20"],
    "carousel_slides": [
      {{"slide": 1, "text": "hook slide text", "visual_direction": "..."}},
      {{"slide": 2, "text": "...", "visual_direction": "..."}},
      {{"slide": 3, "text": "...", "visual_direction": "..."}},
      {{"slide": 4, "text": "...", "visual_direction": "..."}},
      {{"slide": 5, "text": "CTA slide", "visual_direction": "..."}}
    ]
  }},
  "reels_script": {{
    "hook": "first 2 lines (scroll-stopping)",
    "script": "full 30-60 second script with visual/audio directions",
    "caption": "reels caption",
    "audio_suggestion": "type of audio that fits",
    "trending_format": "which trend format this uses"
  }},
  "stories_sequence": [
    {{"story": 1, "type": "poll|quiz|text|image", "content": "...", "interactive_element": "..."}},
    {{"story": 2, "type": "...", "content": "...", "interactive_element": "..."}},
    {{"story": 3, "type": "swipe-up CTA", "content": "...", "cta": "..."}}
  ],
  "best_post_time": "...",
  "engagement_bait": "question or prompt to drive comments"
}}
""")
        save_output("social_agent", f"instagram_{product_name}", result, "json")
        return result

    def create_tiktok_content(self, product_name: str, num_videos: int = 3) -> dict:
        """Create TikTok video concepts and scripts."""
        console.print(f"\n[blue]VIBE creating TikTok content:[/blue] {product_name}")

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create {num_videos} TikTok video concepts for: "{product_name}"
Store: {self.store_name} | Handle: {self.tiktok_handle}
Niche: {self.niche} | Audience: {self.audience}

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

Return JSON:
{{
  "videos": [
    {{
      "concept_title": "...",
      "format": "POV|Tutorial|Unboxing|Transformation|Storytime|Trend",
      "hook": "EXACT first 1-2 lines (must stop scroll in 0.5 seconds)",
      "script": "full video script with timestamps [0:00] [0:05] etc",
      "caption": "TikTok caption (150 chars) + line breaks",
      "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8"],
      "audio_direction": "trending sound type OR original audio description",
      "text_overlays": ["overlay at start", "key overlay", "CTA overlay"],
      "viral_potential": "why this format works right now",
      "estimated_reach": "low|medium|high|viral-potential"
    }}
  ],
  "posting_strategy": "best days and times for TikTok in this niche",
  "growth_hack": "one specific TikTok growth tactic for this product"
}}
""")
        save_output("social_agent", f"tiktok_{product_name}", result, "json")
        return result

    def create_content_calendar(self, month: str = "next month") -> dict:
        """Build a 30-day social media content calendar."""
        console.print(f"\n[blue]VIBE building content calendar:[/blue] {month}")

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create a 30-day social media content calendar for {month}.
Store: {self.store_name} | Niche: {self.niche}
Audience: {self.audience}
Platforms: Instagram, TikTok, Facebook, Pinterest

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

Content pillars ratio: 40% Education/Value, 30% Entertainment/Lifestyle, 20% Product/Promotion, 10% UGC/Social Proof

Return JSON:
{{
  "month": "{month}",
  "content_pillars": ["pillar1", "pillar2", "pillar3", "pillar4"],
  "weekly_themes": [
    {{"week": 1, "theme": "...", "focus": "..."}},
    {{"week": 2, "theme": "...", "focus": "..."}},
    {{"week": 3, "theme": "...", "focus": "..."}},
    {{"week": 4, "theme": "...", "focus": "..."}}
  ],
  "daily_posts": [
    {{
      "day": 1,
      "platform": "Instagram",
      "type": "Carousel|Reel|Story|Feed",
      "topic": "...",
      "caption_hook": "opening line of caption",
      "goal": "awareness|engagement|conversion"
    }}
  ],
  "campaign_weeks": ["any special campaigns or promos to run this month"],
  "kpi_targets": {{"followers_growth": "+X%", "engagement_rate": "X%", "link_clicks": "X/week"}}
}}
""")
        save_output("social_agent", "content_calendar", result, "json")
        return result

    def run_interactive(self):
        console.print(Panel(
            "[bold blue]VIBE — Social Media Agent[/bold blue]\n[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="blue"
        ))
        while True:
            console.print("\n[yellow]Options:[/yellow]")
            console.print("  1. Instagram content suite")
            console.print("  2. TikTok video scripts")
            console.print("  3. 30-day content calendar")
            console.print("  4. Exit")
            choice = input("\nChoice: ").strip()

            if choice == "1":
                name = input("Product name: ").strip()
                result = self.create_instagram_content(name)
                console.print(Panel(str(result), title="Instagram Content", border_style="blue"))
            elif choice == "2":
                name = input("Product name: ").strip()
                result = self.create_tiktok_content(name)
                console.print(Panel(str(result), title="TikTok Scripts", border_style="blue"))
            elif choice == "3":
                month = input("Month (e.g. July 2025): ").strip() or "next month"
                result = self.create_content_calendar(month)
                console.print(Panel(str(result), title="Content Calendar", border_style="blue"))
            elif choice == "4":
                break


if __name__ == "__main__":
    agent = SocialAgent()
    agent.run_interactive()
