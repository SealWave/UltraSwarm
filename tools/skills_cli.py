#!/usr/bin/env python3
"""
tools/skills_cli.py
====================
ULTRASWARM SKILLS VIEWER
=========================
CLI tool to browse, search, and inspect all skills available to UltraSwarm agents.

Skills are the specialist knowledge blocks injected into agent system prompts.
They live in the skills/ directory as .json or .md files.

Commands:
  python tools/skills_cli.py list                        # List all skills
  python tools/skills_cli.py list --domain external      # Filter by domain
  python tools/skills_cli.py search "email drafting"     # Search by keyword
  python tools/skills_cli.py show web_research_skill     # Show full skill detail
  python tools/skills_cli.py agents                      # Show which agent uses which skill
  python tools/skills_cli.py match "I need to write an outreach email"  # Match task to skills
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SKILLS_DIR = PROJECT_ROOT / "skills"


# ─────────────────────────────────────────────────────────────────────────────
# SKILL FILE DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────

def discover_skill_files() -> List[Dict]:
    """
    Scans the skills/ directory tree and returns metadata for every skill file.
    Handles both .json and .md skill formats.
    """
    skills = []
    for skill_file in SKILLS_DIR.rglob("*"):
        if skill_file.is_dir() or skill_file.suffix not in (".json", ".md"):
            continue
        if skill_file.name.startswith("."):
            continue

        rel_path = skill_file.relative_to(PROJECT_ROOT)
        # Derive domain from folder structure
        parts = rel_path.parts
        domain = parts[1] if len(parts) > 2 else "general"

        skill_id = skill_file.stem
        info = {
            "skill_id": skill_id,
            "domain": domain,
            "format": skill_file.suffix.lstrip("."),
            "file": str(rel_path),
            "size_bytes": skill_file.stat().st_size,
            "name": skill_id.replace("_", " ").replace("-", " ").title(),
            "description": "",
            "best_for": "",
            "keywords": [],
            "agent_id": "",
        }

        # Parse content for richer metadata
        try:
            content = skill_file.read_text(encoding="utf-8", errors="ignore")
            if skill_file.suffix == ".json":
                data = json.loads(content)
                info["name"] = data.get("name", info["name"])
                info["description"] = data.get("description", "")[:150]
                info["agent_id"] = data.get("agent_id", data.get("name", skill_id))
            elif skill_file.suffix == ".md":
                # Extract agent ID, best_for from SKILL.md headers
                for line in content.split("\n"):
                    if line.startswith("**Agent ID:**"):
                        info["agent_id"] = line.split("**Agent ID:**")[-1].strip().strip("`")
                    elif line.startswith("**Best For:**"):
                        info["best_for"] = line.split("**Best For:**")[-1].strip()[:120]
                    elif line.startswith("## Keywords"):
                        # next non-empty line has keywords
                        pass
                # Quick description: first non-header, non-empty line
                for line in content.split("\n"):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
                        info["description"] = stripped[:150]
                        break
        except Exception:
            pass

        skills.append(info)

    return sorted(skills, key=lambda s: (s["domain"], s["skill_id"]))


# ─────────────────────────────────────────────────────────────────────────────
# AGENT → SKILL MAPPING (from class attributes)
# ─────────────────────────────────────────────────────────────────────────────

def build_agent_skill_map() -> Dict[str, List[str]]:
    """
    Reads every agent file via AST and extracts `default_skills` or `skill_id`
    to build a map of { agent_name → [skill_ids] }.
    No imports — purely AST-based.
    """
    import ast

    agent_dirs = [
        "agents/managers",
        "agents/helpers",
        "agents/external",
        "agents/outreach",
        "agents/ecommerce",
        "agents/fiverr",
        "agents",
    ]

    result: Dict[str, List[str]] = {}

    for rel_dir in agent_dirs:
        dir_path = PROJECT_ROOT / rel_dir
        if not dir_path.exists():
            continue
        for py_file in dir_path.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "registry.py":
                continue
            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue

                agent_name = None
                skills = []

                for stmt in node.body:
                    if not isinstance(stmt, ast.Assign):
                        continue
                    for target in stmt.targets:
                        if not isinstance(target, ast.Name):
                            continue
                        key = target.id
                        val = stmt.value

                        if key == "name" and isinstance(val, ast.Constant):
                            agent_name = val.value

                        elif key == "skill_id" and isinstance(val, ast.Constant):
                            skills.append(val.value)

                        elif key == "default_skills" and isinstance(val, ast.List):
                            for elt in val.elts:
                                if isinstance(elt, ast.Constant):
                                    skills.append(elt.value)

                if agent_name and skills:
                    result[agent_name] = skills

    return result


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _console():
    try:
        from rich.console import Console
        return Console()
    except ImportError:
        return None


def _print_skills_table(skills: List[Dict], title: str = "UltraSwarm Skills") -> None:
    console = _console()
    if not console:
        print(f"\n{title}")
        print("=" * 60)
        for s in skills:
            print(f"  [{s['domain']:12}] {s['skill_id']:40} ({s['format']})")
        return

    try:
        from rich.table import Table
        from rich import box
    except ImportError:
        return

    table = Table(title=title, box=box.ROUNDED, show_lines=True, header_style="bold cyan")
    table.add_column("#", width=4, style="dim")
    table.add_column("Skill ID", style="cyan")
    table.add_column("Domain", style="magenta", width=12)
    table.add_column("Format", width=6)
    table.add_column("Agent", style="yellow")
    table.add_column("Best For / Description", style="dim")

    for i, s in enumerate(skills, 1):
        best = s.get("best_for") or s.get("description", "")
        agent = s.get("agent_id", "")
        table.add_row(
            str(i),
            s["skill_id"],
            s["domain"],
            s["format"],
            agent[:28],
            best[:70],
        )

    console.print(table)


def _show_skill_detail(skill: Dict, file_path: Path) -> None:
    console = _console()
    content = ""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        content = "(Could not read skill file)"

    if console:
        from rich.panel import Panel
        from rich.syntax import Syntax
        console.print(Panel(
            f"[bold]{skill['name']}[/bold]\n"
            f"[dim]Domain:[/dim] {skill['domain']}  "
            f"[dim]Format:[/dim] {skill['format']}  "
            f"[dim]File:[/dim] {skill['file']}\n"
            f"[dim]Agent:[/dim] {skill.get('agent_id', 'N/A')}",
            title="Skill Detail",
            border_style="cyan"
        ))
        syntax = Syntax(content, "markdown" if skill["format"] == "md" else "json",
                        theme="monokai", line_numbers=True, word_wrap=True)
        console.print(syntax)
    else:
        print(f"\n{'='*60}")
        print(f"Skill: {skill['name']} ({skill['skill_id']})")
        print(f"File:  {skill['file']}")
        print(f"{'='*60}")
        print(content)


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def cmd_list(args, skills: List[Dict]) -> None:
    filtered = skills
    if args.domain:
        filtered = [s for s in skills if s["domain"].lower() == args.domain.lower()]
    if not filtered:
        print(f"No skills found for domain: '{args.domain}'")
        return
    _print_skills_table(filtered, title=f"UltraSwarm Skills — {args.domain or 'All Domains'}")


def cmd_search(args, skills: List[Dict]) -> None:
    query = args.query.lower()
    matched = [
        s for s in skills
        if query in s["skill_id"].lower()
        or query in s.get("description", "").lower()
        or query in s.get("best_for", "").lower()
        or query in s.get("agent_id", "").lower()
        or query in s.get("domain", "").lower()
    ]
    if not matched:
        print(f"No skills matched: '{args.query}'")
        return
    _print_skills_table(matched, title=f"Search results: '{args.query}'")


def cmd_show(args, skills: List[Dict]) -> None:
    skill_id = args.skill_id.lower()
    match = next((s for s in skills if s["skill_id"].lower() == skill_id), None)
    if not match:
        # Try partial match
        match = next((s for s in skills if skill_id in s["skill_id"].lower()), None)
    if not match:
        print(f"Skill not found: '{args.skill_id}'")
        print(f"Available: {', '.join(s['skill_id'] for s in skills)}")
        return
    file_path = PROJECT_ROOT / match["file"]
    _show_skill_detail(match, file_path)


def cmd_agents(args, skills: List[Dict]) -> None:
    """Show which agent uses which skill(s)."""
    console = _console()
    agent_map = build_agent_skill_map()

    if not agent_map:
        print("No agent-skill mappings found.")
        return

    if console:
        from rich.table import Table
        from rich import box
        table = Table(
            title="Agent → Skill Mapping",
            box=box.ROUNDED,
            show_lines=True,
            header_style="bold cyan"
        )
        table.add_column("Agent", style="cyan")
        table.add_column("Skills", style="yellow")

        for agent_name, agent_skills in sorted(agent_map.items()):
            table.add_row(agent_name, "\n".join(agent_skills) if agent_skills else "[dim]none[/dim]")
        console.print(table)
    else:
        print("\nAgent → Skill Mapping")
        print("=" * 50)
        for agent_name, agent_skills in sorted(agent_map.items()):
            print(f"  {agent_name}:")
            for s in agent_skills:
                print(f"    - {s}")


def cmd_match(args, skills: List[Dict]) -> None:
    """Find the best matching skills for a given task description."""
    task = args.task.lower()
    console = _console()

    # Simple keyword scoring
    scored = []
    for skill in skills:
        haystack = " ".join([
            skill.get("skill_id", ""),
            skill.get("domain", ""),
            skill.get("description", ""),
            skill.get("best_for", ""),
            skill.get("agent_id", ""),
        ]).lower()
        # Count how many words in the query appear in the haystack
        words = [w for w in task.split() if len(w) > 3]
        score = sum(1 for w in words if w in haystack)
        if score > 0:
            scored.append((score, skill))

    scored.sort(key=lambda x: -x[0])
    top = [s for _, s in scored[:10]]

    if not top:
        print(f"No matching skills found for: '{args.task}'")
        return

    if console:
        from rich.panel import Panel
        console.print(Panel(
            f"[dim]Task:[/dim] {args.task}\n"
            f"[dim]Best matching skills:[/dim]",
            title="Skill Matcher",
            border_style="cyan"
        ))

    _print_skills_table(top, title=f"Top Skills for: '{args.task[:50]}'")

    # Also try the real loader if available
    try:
        from tools.agent_skill_loader import load_skills_for_task
        real_matches = load_skills_for_task(args.task, top_k=5)
        if real_matches and console:
            console.print(f"\n[dim]Also matched by semantic loader ({len(real_matches)} skills)[/dim]")
            for sm in real_matches:
                console.print(f"  [cyan]{sm.skill_name}[/cyan] — score: {sm.score:.0%}")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UltraSwarm Skills Viewer — browse and inspect all agent skills.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/skills_cli.py list
  python tools/skills_cli.py list --domain external
  python tools/skills_cli.py search "email"
  python tools/skills_cli.py show web_research_skill
  python tools/skills_cli.py agents
  python tools/skills_cli.py match "write a cold outreach email"
        """
    )

    subparsers = parser.add_subparsers(dest="command")

    # list
    p_list = subparsers.add_parser("list", help="List all skills")
    p_list.add_argument("--domain", help="Filter by domain (e.g. external, ecommerce)")

    # search
    p_search = subparsers.add_parser("search", help="Search skills by keyword")
    p_search.add_argument("query", help="Search term")

    # show
    p_show = subparsers.add_parser("show", help="Show full detail for a skill")
    p_show.add_argument("skill_id", help="Skill ID to display")

    # agents
    subparsers.add_parser("agents", help="Show which agent uses which skill(s)")

    # match
    p_match = subparsers.add_parser("match", help="Find best skills for a task description")
    p_match.add_argument("task", help="Natural language task description")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    skills = discover_skill_files()

    if args.command == "list":
        cmd_list(args, skills)
    elif args.command == "search":
        cmd_search(args, skills)
    elif args.command == "show":
        cmd_show(args, skills)
    elif args.command == "agents":
        cmd_agents(args, skills)
    elif args.command == "match":
        cmd_match(args, skills)


if __name__ == "__main__":
    main()
