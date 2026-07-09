"""
agents/external/social_media_agent.py
========================================
Social Media Content Agent — adapted from 500-AI-Agents / 14-social-media-agent
Original: CrewAI (strategist + writer crew) + GPT-4o-mini
This version: Gemini 2.5 Flash with strategy → content pipeline
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from tools.output_manager import save_output
from tools.agent_skill_loader import load_skills_for_task, get_skill_loader
from rich.console import Console
from rich.panel import Panel

console = Console()

SYSTEM_PROMPT = """
You are a social media content strategist and copywriter.

You write platform-native content that drives engagement:
- Twitter/X: punchy, opinion-forward, hook-led (under 280 chars)
- LinkedIn: professional, story-driven (150-200 words)
- Instagram: visual-first, lifestyle language (100-150 words + 15 hashtags)
- TikTok: hook in first 3 words, trend-aware, call-to-action

Rules:
- Never use all-caps except for acronyms.
- No generic hashtags (#love, #life, #motivation).
- Open every post with a scroll-stopping hook.
- Match brand voice if provided.

Output format:
{
  "topic": "...",
  "core_message": "...",
  "target_audience": "...",
  "emotional_hook": "...",
  "twitter_x": {
    "tweet_1": "Under 280 chars",
    "tweet_2": "Alternative variation",
    "thread_opener": "If a thread is appropriate"
  },
  "linkedin": {
    "post": "150-200 word professional post",
    "hashtags": ["#tag1", "#tag2", "#tag3"]
  },
  "instagram": {
    "caption": "100-150 word visual caption",
    "hashtags": ["#tag1", "...up to 15 tags"]
  }
}
"""


class SocialMediaAgent:
    """
    Social Media Content Agent.
    Generates platform-native content for Twitter/X, LinkedIn, Instagram.
    """

    name = "social_media_agent"
    role = "worker"
    description = (
        "Generates platform-optimized social media content for Twitter/X, LinkedIn, "
        "and Instagram from any topic. Includes hashtag strategy and multi-variant posts. "
        "Best for: product launches, thought leadership, announcements, content calendars."
    )
    skill_id = "social_media_skill"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = make_client(SYSTEM_PROMPT, "SOCIAL-MEDIA")

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "skills": [self.skill_id],
        }

    def generate_content(
        self,
        topic: str,
        brand: str = "",
        platforms: list = None,
        tone: str = "engaging",
    ) -> dict:
        """
        Generate social media content for a topic.

        Args:
            topic: The content topic or subject.
            brand: Optional brand name for voice consistency.
            platforms: List of platforms e.g. ["twitter", "linkedin", "instagram"].
                       Defaults to all three.
            tone: Overall tone direction.

        Returns:
            dict with platform-specific content and strategy.
        """
        if platforms is None:
            platforms = ["twitter", "linkedin", "instagram"]

        console.print(f"\n[cyan]SOCIAL MEDIA:[/cyan] {topic[:60]}")

        # Load skill guidance
        skills = load_skills_for_task(f"social media content {topic}", top_k=1)
        skill_block = ""
        if skills:
            loader = get_skill_loader()
            skill_block = loader.build_skill_prompt(skills)

        # Turn 1: Strategy
        strategy_prompt = (
            f"Social media topic: {topic}\n"
            f"Brand: {brand or 'Not specified'}\n"
            f"Platforms: {', '.join(platforms)}\n"
            f"Tone direction: {tone}\n\n"
            f"Define: core message, target audience, emotional hook, 5 relevant hashtags.\n"
            f"Return JSON with keys: core_message, target_audience, emotional_hook, hashtags."
        )
        strategy = self.client.ask_json(strategy_prompt)

        # Turn 2: Content generation
        content_prompt = (
            f"Write social media content for these platforms: {', '.join(platforms)}\n\n"
            f"Topic: {topic}\n"
            f"Brand: {brand or 'General'}\n"
            f"Strategy:\n{strategy}\n\n"
            f"{skill_block}\n"
            f"Generate the full content suite in the required JSON format."
        )
        result = self.client.ask_json(content_prompt)
        result["topic"] = topic
        if brand:
            result["brand"] = brand

        save_output("social_media_agent", f"social_{topic[:30]}", result, "json")
        return result

    def run(self, input_data: dict) -> dict:
        """BaseAgent-compatible run() method."""
        task_id = input_data.get("task_id", "social_task")
        instruction = input_data.get("instruction", "")
        context_data = input_data.get("context", {})
        brand = context_data.get("brand", "")
        platforms = context_data.get("platforms", ["twitter", "linkedin", "instagram"])
        tone = context_data.get("tone", "engaging")

        try:
            result = self.generate_content(
                topic=instruction,
                brand=brand,
                platforms=platforms,
                tone=tone,
            )
            return {
                "success": True,
                "agent_name": self.name,
                "task_id": task_id,
                "output": result,
                "error": None,
                "metadata": {},
                "context_for_next": {"social_content": result},
            }
        except Exception as e:
            return {
                "success": False,
                "agent_name": self.name,
                "task_id": task_id,
                "output": None,
                "error": str(e),
                "metadata": {},
                "context_for_next": {},
            }

    def run_interactive(self):
        """Standalone interactive mode."""
        console.print(Panel(
            "[bold cyan]SOCIAL MEDIA AGENT[/bold cyan]\n"
            "[dim]Powered by Gemini 2.5 Flash[/dim]",
            border_style="cyan"
        ))

        while True:
            topic = input("\nContent topic (or 'exit'): ").strip()
            if topic.lower() in {"exit", "quit", "q"}:
                break
            brand = input("Brand name (optional): ").strip()
            platforms_input = input("Platforms [twitter,linkedin,instagram]: ").strip()
            platforms = [p.strip() for p in platforms_input.split(",")] if platforms_input else None
            result = self.generate_content(topic, brand=brand, platforms=platforms)

            # Display Twitter content
            twitter = result.get("twitter_x", {})
            if twitter:
                console.print(Panel(
                    f"Tweet 1: {twitter.get('tweet_1', '')}\n\n"
                    f"Tweet 2: {twitter.get('tweet_2', '')}",
                    title="Twitter/X", border_style="blue"
                ))
            linkedin = result.get("linkedin", {})
            if linkedin:
                console.print(Panel(
                    linkedin.get("post", ""),
                    title="LinkedIn", border_style="green"
                ))
