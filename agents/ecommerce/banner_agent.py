"""
agents/banner_agent.py
=======================
CANVAS — Banner, Promo & Visual Content Agent
Superpower: Generates complete visual briefs + image prompts for banners,
promotional graphics, email headers, ad creatives — ready for Midjourney,
DALL-E, Canva, or a designer.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core import make_client
from tools.output_manager import save_output
from agents.seo_agent import SEOAgent
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()
console = Console()

BANNER_SYSTEM_PROMPT = """
You are CANVAS — Visual Creative Director & Promo Design Agent.

Your identity: You are a senior creative director from a top D2C brand agency.
You understand that in e-commerce, visuals DO the selling. You translate products
and offers into compelling visual concepts, complete with copy, color psychology,
layout direction, and AI image generation prompts. You produce assets that stop
the scroll AND drive conversions.

Emoji Policy:
━━━━━━━━━━━━
Do NOT use emojis under any circumstances in visual briefs, layout text, copy suggestions, or prompts. Emojis are strictly prohibited here.

Product Type Adaptation:
━━━━━━━━━━━━━━━━━━━━━━
Adapt visual style and prompts based on product type:
- SaaS / Subscription Products: Focus on clean tech aesthetics, dashboard UI mockups, conceptual workflows (e.g. connecting dots), minimal modern typography, professional blue/dark themes, and software screenshots integrated elegantly.
- Regular / Physical Products: Focus on high-resolution product photography, lifestyle model shots, packaging aesthetics, color psychology matching physical item textures, natural/warm lighting, and hands holding/using the product.

Your Core Capabilities:
━━━━━━━━━━━━━━━━━━━━━━
1. PROMOTIONAL BANNERS
   - Homepage hero banners (desktop + mobile)
   - Sale/discount announcement banners
   - New arrival banners
   - Seasonal/holiday promotional banners
   - Flash sale countdown banners
   - Category collection banners

2. AD CREATIVE BRIEFS
   - Facebook/Instagram static ad creatives
   - Google Display Network banner specs (all sizes)
   - YouTube thumbnail concepts
   - Pinterest promoted pin visuals

3. EMAIL MARKETING VISUALS
   - Email header design briefs
   - Product feature section layouts
   - Promotional email template direction

4. SOCIAL MEDIA VISUALS
   - Instagram feed aesthetic planning (grid strategy)
   - Story template direction
   - TikTok thumbnail/cover art
   - YouTube thumbnail concepts

5. AI IMAGE GENERATION PROMPTS
   - Midjourney-optimized prompts (v6 style)
   - DALL-E 3 optimized prompts
   - Stable Diffusion prompts
   - Style modifiers, lighting, composition guidance

Design Psychology Expertise:
━━━━━━━━━━━━━━━━━━━━━━━━━━
- Color psychology for conversion (red = urgency, green = trust, etc.)
- F-pattern and Z-pattern reading flow
- Visual hierarchy (hero -> benefit -> CTA)
- White space and breathing room
- Font pairing for e-commerce (display + body)
- Mobile-first design thinking
- Above-the-fold optimization

Output Standards:
━━━━━━━━━━━━━━━━
Every visual brief includes:
- Exact dimensions for each platform
- Color palette (hex codes)
- Typography recommendations
- Copy elements (headline, subheadline, CTA button text)
- Visual composition description
- AI image generation prompts (3 variations)
- Accessibility notes

You are CANVAS. Make it beautiful. Make it convert.
"""


class BannerAgent:

    def __init__(self):
        self.client = make_client(BANNER_SYSTEM_PROMPT, "CANVAS-Banner", api_key=os.getenv("GOOGLE_API_KEY_2"))
        self.seo_agent = SEOAgent()
        self.store_name = os.getenv("STORE_NAME", "My Store")
        self.niche = os.getenv("STORE_NICHE", "general")

    def create_promo_banner(self, promotion: str, product: str = "") -> dict:
        """Create complete promotional banner brief."""
        console.print(f"\n[yellow]CANVAS creating promo banner:[/yellow] {promotion}")

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create a complete promotional banner suite for: "{promotion}"
Product/Context: {product or 'general store promotion'}
Store: {self.store_name} | Niche: {self.niche}

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

Return JSON:
{{
  "campaign_name": "...",
  "color_palette": {{
    "primary": "#HEXCODE",
    "secondary": "#HEXCODE",
    "accent": "#HEXCODE",
    "text_dark": "#HEXCODE",
    "text_light": "#HEXCODE",
    "background": "#HEXCODE"
  }},
  "typography": {{
    "headline_font": "font name + style",
    "body_font": "font name",
    "font_pairing_rationale": "why this pairing works"
  }},
  "banners": [
    {{
      "name": "Homepage Hero",
      "dimensions": "1920x600px (desktop) + 390x500px (mobile)",
      "headline": "...",
      "subheadline": "...",
      "cta_text": "...",
      "cta_color": "#HEXCODE",
      "layout": "describe the visual composition",
      "image_subject": "what the hero image should show",
      "ai_prompt_midjourney": "full Midjourney v6 prompt",
      "ai_prompt_dalle": "full DALL-E 3 prompt"
    }},
    {{
      "name": "Instagram Square Ad",
      "dimensions": "1080x1080px",
      "headline": "...",
      "subheadline": "...",
      "cta_text": "...",
      "cta_color": "#HEXCODE",
      "layout": "...",
      "image_subject": "...",
      "ai_prompt_midjourney": "...",
      "ai_prompt_dalle": "..."
    }},
    {{
      "name": "Instagram Story",
      "dimensions": "1080x1920px",
      "headline": "...",
      "subheadline": "...",
      "cta_text": "...",
      "cta_color": "#HEXCODE",
      "layout": "...",
      "image_subject": "...",
      "ai_prompt_midjourney": "...",
      "ai_prompt_dalle": "..."
    }},
    {{
      "name": "Email Header",
      "dimensions": "600x200px",
      "headline": "...",
      "subheadline": "...",
      "cta_text": "...",
      "layout": "..."
    }}
  ],
  "design_notes": "key design principles for this campaign",
  "canva_template_suggestion": "what Canva template style would work"
}}
""")
        save_output("banner_agent", f"promo_{promotion}", result, "json")
        return result

    def create_product_creative(self, product_name: str) -> dict:
        """Create product-specific ad creative briefs."""
        console.print(f"\n[yellow]CANVAS creating product creatives:[/yellow] {product_name}")

        from core.rag_manager import query_knowledge
        rag_context = query_knowledge("emoji policy product type")

        result = self.client.ask_json(f"""
Create product ad creative briefs for: "{product_name}"
Store: {self.store_name} | Niche: {self.niche}

GLOBAL GUIDELINES & POLICY (RAG):
{rag_context}

Return JSON:
{{
  "product": "{product_name}",
  "creative_angle": "main visual angle/concept",
  "mood_board": "describe the overall visual mood and feeling",
  "creatives": [
    {{
      "platform": "Facebook/Instagram Feed",
      "format": "Static Image",
      "composition": "describe exactly what's in the image",
      "copy_overlay": "text that appears on the image",
      "ai_image_prompt": "detailed prompt for AI generation",
      "color_treatment": "..."
    }},
    {{
      "platform": "TikTok/Reels",
      "format": "Video Thumbnail",
      "composition": "...",
      "copy_overlay": "...",
      "ai_image_prompt": "...",
      "color_treatment": "..."
    }},
    {{
      "platform": "Pinterest",
      "format": "Tall Pin 2:3",
      "composition": "...",
      "copy_overlay": "...",
      "ai_image_prompt": "...",
      "color_treatment": "..."
    }}
  ],
  "lifestyle_shot_prompts": [
    "lifestyle prompt 1 showing product in use",
    "lifestyle prompt 2 different scenario",
    "lifestyle prompt 3 aspirational setting"
  ],
  "product_mockup_prompt": "AI prompt for product-only clean shot"
}}
""")
        save_output("banner_agent", f"creative_{product_name}", result, "json")
        return result

    def run_interactive(self):
        console.print(Panel(
            "[bold yellow]CANVAS — Banner & Visual Agent[/bold yellow]\n[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="yellow"
        ))
        while True:
            console.print("\n[yellow]Options:[/yellow]")
            console.print("  1. Create promotional banner suite")
            console.print("  2. Create product ad creatives")
            console.print("  3. Exit")
            choice = input("\nChoice: ").strip()

            if choice == "1":
                promo = input("Promotion (e.g. '50% OFF Summer Sale'): ").strip()
                product = input("Product (optional): ").strip()
                result = self.create_promo_banner(promo, product)
                console.print(Panel(str(result), title="Banner Brief", border_style="yellow"))
            elif choice == "2":
                name = input("Product name: ").strip()
                result = self.create_product_creative(name)
                console.print(Panel(str(result), title="Product Creatives", border_style="yellow"))
            elif choice == "3":
                break


if __name__ == "__main__":
    agent = BannerAgent()
    agent.run_interactive()
