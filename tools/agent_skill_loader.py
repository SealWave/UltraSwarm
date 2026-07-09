"""
tools/agent_skill_loader.py
============================
Intelligent Agent Skill Loader
================================
Dynamically selects the best agent skills for a given task and injects
their SKILL.md content as structured system prompt blocks.

Works alongside the existing skill_loader.py (which handles JSON skills).
This module handles the Markdown-based SKILL.md files in skills/external/
as well as skills in the knowledge/ directory.

Usage:
    from tools.agent_skill_loader import AgentSkillLoader

    loader = AgentSkillLoader()

    # Score and load best skills for a task description
    skills = loader.load_best_skills(
        task="Write a series of social media posts for our new product launch",
        top_k=2
    )

    # Get a formatted system prompt block for injection
    prompt_block = loader.build_skill_prompt(skills)
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from functools import lru_cache


# ── Skill directories ──────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
EXTERNAL_SKILLS_DIR = ROOT / "skills" / "external"
KNOWLEDGE_SKILLS_DIR = ROOT / "knowledge"


@dataclass
class SkillMatch:
    """Result of a skill-to-task matching operation."""
    skill_id: str
    skill_name: str
    agent_id: str
    domain: str
    score: float                          # 0.0 – 1.0 relevance score
    matched_keywords: List[str]
    content: str                          # Full raw SKILL.md content
    source_file: str
    best_for: str = ""                    # Short description from skill file


@dataclass
class AgentSkillRegistry:
    """In-memory registry of all indexed skills."""
    skills: List[Dict] = field(default_factory=list)


class AgentSkillLoader:
    """
    Loads and indexes agent skill files (SKILL.md format), then matches
    skills to tasks using keyword-weighted scoring.

    Scoring algorithm (keyword overlap + domain boost):
        base_score = matched_keywords / total_keywords_in_skill
        domain_boost = +0.2 if task mentions domain name
        title_boost = +0.15 if task mentions skill name directly
        final_score = min(1.0, base_score + domain_boost + title_boost)

    Tie-breaking: alphabetical by skill_id for deterministic output.
    """

    def __init__(
        self,
        external_skills_dir: Optional[Path] = None,
        knowledge_dir: Optional[Path] = None,
    ):
        self.external_dir = external_skills_dir or EXTERNAL_SKILLS_DIR
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_SKILLS_DIR
        self._registry: List[Dict] = []
        self._build_registry()

    # ── Registry build ─────────────────────────────────────────────────────────

    def _build_registry(self) -> None:
        """Scan all skill directories and index available skills."""
        self._registry = []

        # Load external (500-agents derived) skills
        if self.external_dir.exists():
            for skill_file in sorted(self.external_dir.glob("*.md")):
                record = self._parse_skill_md(skill_file, source="external")
                if record:
                    self._registry.append(record)

        # Load knowledge/ SKILL.md files (agent-browser etc.) — these are
        # already in the project and should also be matchable
        if self.knowledge_dir.exists():
            for skill_file in sorted(self.knowledge_dir.glob("*.md")):
                record = self._parse_skill_md(skill_file, source="knowledge")
                if record:
                    self._registry.append(record)

    def _parse_skill_md(self, path: Path, source: str = "external") -> Optional[Dict]:
        """
        Parse a SKILL.md file into a registry record.

        Extracts:
          - skill_id: derived from filename (snake_case without _skill suffix)
          - skill_name: from the H1 line
          - agent_id: from the **Agent ID:** line
          - domain: from the **Domain:** line
          - best_for: from the **Best For:** line
          - keywords: from the ## Keywords section
          - content: full file text

        Files missing the **Agent ID:** marker are still indexed with a
        derived agent_id, so knowledge/ stubs work too.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return None

        if not content.strip():
            return None

        # Derive skill_id from filename
        skill_id = path.stem.replace("-", "_")

        # Parse H1 for skill name
        name_match = re.search(r"^#\s+SKILL:\s+(.+)$", content, re.MULTILINE)
        skill_name = name_match.group(1).strip() if name_match else path.stem.replace("_", " ").title()

        # Parse Agent ID
        aid_match = re.search(r"\*\*Agent ID:\*\*\s+`([^`]+)`", content)
        agent_id = aid_match.group(1).strip() if aid_match else skill_id

        # Parse Domain
        domain_match = re.search(r"\*\*Domain:\*\*\s+(.+)$", content, re.MULTILINE)
        domain = domain_match.group(1).strip().lower() if domain_match else "general"

        # Parse Best For
        best_match = re.search(r"\*\*Best For:\*\*\s+(.+)$", content, re.MULTILINE)
        best_for = best_match.group(1).strip() if best_match else ""

        # Parse keywords section
        kw_section = re.search(r"## Keywords.*?\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        keywords: List[str] = []
        if kw_section:
            raw_kw = kw_section.group(1).strip()
            # Keywords are comma/newline separated tokens
            keywords = [
                kw.strip().lower()
                for kw in re.split(r"[,\n]", raw_kw)
                if kw.strip()
            ]

        # Augment keywords with domain and skill name tokens
        name_tokens = re.findall(r"[a-z0-9]+", skill_name.lower())
        domain_tokens = re.findall(r"[a-z0-9]+", domain.lower())
        best_tokens = re.findall(r"[a-z0-9]+", best_for.lower()) if best_for else []
        all_keywords = list({*keywords, *name_tokens, *domain_tokens, *best_tokens})

        return {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "agent_id": agent_id,
            "domain": domain,
            "best_for": best_for,
            "keywords": all_keywords,
            "content": content,
            "source_file": str(path),
            "source": source,
        }

    # ── Task matching ──────────────────────────────────────────────────────────

    def score_skill(self, skill: Dict, task: str) -> Tuple[float, List[str]]:
        """
        Score a skill's relevance to a task description.

        Returns (score: float, matched_keywords: List[str]).
        """
        task_lower = task.lower()
        task_tokens = set(re.findall(r"[a-z0-9]+", task_lower))

        if not skill["keywords"]:
            return (0.0, [])

        matched = [kw for kw in skill["keywords"] if kw in task_lower or kw in task_tokens]
        base = len(matched) / max(len(skill["keywords"]), 1)

        # Domain boost
        domain_tokens = re.findall(r"[a-z0-9]+", skill["domain"].lower())
        domain_boost = 0.2 if any(dt in task_lower for dt in domain_tokens) else 0.0

        # Skill name boost
        name_tokens = re.findall(r"[a-z0-9]+", skill["skill_name"].lower())
        name_boost = 0.15 if any(nt in task_lower for nt in name_tokens) else 0.0

        # Agent ID direct mention boost
        agent_boost = 0.25 if skill["agent_id"].replace("_", " ") in task_lower else 0.0

        score = min(1.0, base + domain_boost + name_boost + agent_boost)
        return (score, matched)

    def find_best_skills(
        self,
        task: str,
        top_k: int = 3,
        min_score: float = 0.05,
        source_filter: Optional[str] = None,
    ) -> List[SkillMatch]:
        """
        Score all registered skills against the task and return the top-k matches.

        Args:
            task: Natural language task description or instruction.
            top_k: Maximum number of skills to return.
            min_score: Minimum relevance score (0.0-1.0) — skills below this are excluded.
            source_filter: "external" | "knowledge" | None (all sources).

        Returns:
            List of SkillMatch objects, sorted by score descending.
        """
        candidates = self._registry
        if source_filter:
            candidates = [s for s in candidates if s.get("source") == source_filter]

        scored: List[Tuple[float, str, Dict, List[str]]] = []
        for skill in candidates:
            score, matched = self.score_skill(skill, task)
            if score >= min_score:
                scored.append((score, skill["skill_id"], skill, matched))

        # Sort by score desc, then skill_id asc for determinism
        scored.sort(key=lambda x: (-x[0], x[1]))

        results = []
        for score, _, skill, matched in scored[:top_k]:
            results.append(SkillMatch(
                skill_id=skill["skill_id"],
                skill_name=skill["skill_name"],
                agent_id=skill["agent_id"],
                domain=skill["domain"],
                score=score,
                matched_keywords=matched,
                content=skill["content"],
                source_file=skill["source_file"],
                best_for=skill.get("best_for", ""),
            ))

        return results

    def load_best_skills(
        self,
        task: str,
        top_k: int = 3,
        min_score: float = 0.05,
    ) -> List[SkillMatch]:
        """
        Convenience alias for find_best_skills(). Searches all sources.
        """
        return self.find_best_skills(task, top_k=top_k, min_score=min_score)

    # ── Prompt building ────────────────────────────────────────────────────────

    def build_skill_prompt(
        self,
        skills: List[SkillMatch],
        include_full_content: bool = False,
    ) -> str:
        """
        Build a system prompt injection block from a list of matched skills.

        Args:
            skills: List of SkillMatch objects (from find_best_skills / load_best_skills).
            include_full_content: If True, includes the full SKILL.md content.
                                  If False, includes a condensed block (name, domain,
                                  best_for, top instructions only).

        Returns:
            Formatted string ready to append to any agent's system prompt.
        """
        if not skills:
            return ""

        lines = [
            "---",
            "# LOADED AGENT SKILLS",
            "The following specialist skills are available for this task.\n"
            "Apply the instructions and output formats from each relevant skill.",
            "",
        ]

        for i, sm in enumerate(skills, 1):
            lines.append(f"## [{i}] {sm.skill_name}")
            lines.append(f"**Agent:** `{sm.agent_id}` | **Domain:** {sm.domain} | **Relevance:** {sm.score:.0%}")
            if sm.best_for:
                lines.append(f"**Best For:** {sm.best_for}")
            lines.append("")

            if include_full_content:
                # Inject the full SKILL.md (minus the H1 header, already added above)
                body = re.sub(r"^#\s+SKILL:.*\n", "", sm.content, count=1).strip()
                lines.append(body)
            else:
                # Condensed: extract Instructions and Constraints sections only
                instructions = self._extract_section(sm.content, "Instructions for Agent")
                constraints = self._extract_section(sm.content, "Constraints")
                output_fmt = self._extract_section(sm.content, "Output Format")

                if output_fmt:
                    lines.append("**Output Format:**")
                    lines.append(output_fmt)
                    lines.append("")
                if instructions:
                    lines.append("**Instructions:**")
                    lines.append(instructions)
                    lines.append("")
                if constraints:
                    lines.append("**Constraints:**")
                    lines.append(constraints)

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _extract_section(self, content: str, section_title: str) -> str:
        """
        Extract the content of a named ## section from a SKILL.md file.
        Returns the section content without the heading line.
        """
        pattern = rf"##\s+{re.escape(section_title)}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    # ── Utility ────────────────────────────────────────────────────────────────

    def list_skills(self) -> List[Dict]:
        """Return a summary list of all registered skills."""
        return [
            {
                "skill_id": s["skill_id"],
                "skill_name": s["skill_name"],
                "agent_id": s["agent_id"],
                "domain": s["domain"],
                "best_for": s.get("best_for", ""),
                "source": s.get("source", "unknown"),
                "keyword_count": len(s["keywords"]),
            }
            for s in self._registry
        ]

    def get_skill_by_id(self, skill_id: str) -> Optional[Dict]:
        """Retrieve a specific skill by its ID."""
        for s in self._registry:
            if s["skill_id"] == skill_id:
                return s
        return None

    def reload(self) -> None:
        """Force a reload of all skill files (useful after adding new skills)."""
        self._build_registry()


# ── Module-level singleton ─────────────────────────────────────────────────────
_loader_instance: Optional[AgentSkillLoader] = None


def get_skill_loader() -> AgentSkillLoader:
    """Get or create the module-level AgentSkillLoader singleton."""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = AgentSkillLoader()
    return _loader_instance


def load_skills_for_task(
    task: str,
    top_k: int = 3,
    min_score: float = 0.05,
    as_prompt: bool = False,
    include_full_content: bool = False,
) -> "List[SkillMatch] | str":
    """
    Top-level convenience function.

    Args:
        task: Natural language task description.
        top_k: Number of top skills to return.
        min_score: Minimum relevance threshold.
        as_prompt: If True, return a formatted prompt string instead of SkillMatch list.
        include_full_content: Only used when as_prompt=True. Include full SKILL.md body.

    Returns:
        List[SkillMatch] when as_prompt=False.
        str (formatted prompt block) when as_prompt=True.
    """
    loader = get_skill_loader()
    skills = loader.load_best_skills(task, top_k=top_k, min_score=min_score)
    if as_prompt:
        return loader.build_skill_prompt(skills, include_full_content=include_full_content)
    return skills
