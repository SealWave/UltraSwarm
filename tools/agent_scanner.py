#!/usr/bin/env python3
"""
tools/agent_scanner.py
=======================
ULTRASWARM AGENT SCANNER
=========================
Automatically discovers every agent in the codebase by scanning agent directories
for Python files that expose the standard interface (name, role, description).

Features:
  1. Scans all agent directories recursively.
  2. Compares discovered agents against a known snapshot (.agent_snapshot.json).
  3. Reports NEW agents added since the last scan.
  4. Updates the Supreme Orchestrator's registry awareness automatically.
  5. Writes an updated snapshot for next comparison.

Usage:
  python tools/agent_scanner.py               # Scan and report
  python tools/agent_scanner.py --watch       # Watch for changes every 30s
  python tools/agent_scanner.py --json        # Output raw JSON (for CI/automation)
  python tools/agent_scanner.py --update-apex # Scan and notify APEX to refresh
"""

import os
import sys
import ast
import json
import time
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SNAPSHOT_FILE = PROJECT_ROOT / ".agent_snapshot.json"

# Agent directories to scan (relative to project root)
AGENT_DIRS = [
    "agents/managers",
    "agents/helpers",
    "agents/external",
    "agents/outreach",
    "agents/ecommerce",
    "agents/fiverr",
    "agents",          # catches browser_operator_agent.py at root level
]

# Files to skip
SKIP_FILES = {
    "__init__.py",
    "registry.py",
    "base_agent.py",
}


# ─────────────────────────────────────────────────────────────────────────────
# AST-BASED SCANNER (no imports, no side-effects, no dependencies)
# ─────────────────────────────────────────────────────────────────────────────

def extract_agent_info_from_ast(filepath: Path) -> Optional[Dict]:
    """
    Parses a Python file using AST (no imports/execution) and extracts
    agent metadata from class-level string assignments.

    Looks for:
        name = "some_agent_name"
        role = "worker|helper|manager|domain"
        description = "..."
    """
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, OSError):
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        attrs = {}
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if not isinstance(target, ast.Name):
                    continue
                key = target.id
                if key not in ("name", "role", "description"):
                    continue
                # Extract string value
                val = stmt.value
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    attrs[key] = val.value
                elif isinstance(val, ast.JoinedStr):
                    # f-string — treat as dynamic
                    attrs[key] = "<dynamic f-string>"

        if "name" in attrs and "role" in attrs:
            return {
                "class_name": node.name,
                "name": attrs.get("name", ""),
                "role": attrs.get("role", "worker"),
                "description": attrs.get("description", "")[:120],
                "file": str(filepath.relative_to(PROJECT_ROOT)),
                "discovered_at": datetime.now().isoformat(),
            }

    return None


def scan_agent_directories() -> Dict[str, Dict]:
    """
    Scans all AGENT_DIRS and returns a dict of discovered agents keyed by name.
    Uses AST parsing — safe, no imports, no side-effects.
    """
    discovered = {}

    for rel_dir in AGENT_DIRS:
        dir_path = PROJECT_ROOT / rel_dir
        if not dir_path.exists():
            continue

        # Only scan the immediate directory (not recursive) to avoid deep nesting
        depth = 1 if rel_dir == "agents" else 0
        py_files = list(dir_path.glob("*.py"))
        if depth:
            # For root agents/ dir only pick direct .py files, skip subdirs
            py_files = [f for f in py_files if f.is_file()]

        for py_file in py_files:
            if py_file.name in SKIP_FILES:
                continue
            info = extract_agent_info_from_ast(py_file)
            if info:
                discovered[info["name"]] = info

    return discovered


# ─────────────────────────────────────────────────────────────────────────────
# SNAPSHOT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def load_snapshot() -> Dict[str, Dict]:
    """Load the previous agent snapshot from disk."""
    if not SNAPSHOT_FILE.exists():
        return {}
    try:
        return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_snapshot(agents: Dict[str, Dict]) -> None:
    """Persist the current agent snapshot to disk."""
    SNAPSHOT_FILE.write_text(
        json.dumps(agents, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def diff_agents(
    previous: Dict[str, Dict],
    current: Dict[str, Dict]
) -> Tuple[List[Dict], List[str]]:
    """
    Compares two snapshots.
    Returns:
        new_agents:     list of newly discovered agent dicts
        removed_agents: list of agent names no longer found
    """
    prev_names = set(previous.keys())
    curr_names = set(current.keys())

    new_agents = [current[n] for n in (curr_names - prev_names)]
    removed_agents = list(prev_names - curr_names)

    return new_agents, removed_agents


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

def print_report(
    current: Dict[str, Dict],
    new_agents: List[Dict],
    removed_agents: List[str],
    json_mode: bool = False
) -> None:
    """Prints a formatted scan report to stdout."""

    if json_mode:
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(current),
            "new_agents": new_agents,
            "removed_agents": removed_agents,
            "all_agents": list(current.values()),
        }
        print(json.dumps(report, indent=2))
        return

    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        console = Console()
    except ImportError:
        _print_plain_report(current, new_agents, removed_agents)
        return

    # ── Header ──────────────────────────────────────────────────────────────
    console.print(Panel(
        f"[bold cyan]UltraSwarm Agent Scanner[/bold cyan]\n"
        f"[dim]Scanned at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n"
        f"[bold green]{len(current)} agents discovered[/bold green]  "
        f"{'[bold yellow]' + str(len(new_agents)) + ' NEW[/bold yellow]  ' if new_agents else ''}"
        f"{'[bold red]' + str(len(removed_agents)) + ' REMOVED[/bold red]' if removed_agents else ''}",
        title="APEX Registry Scan",
        border_style="cyan"
    ))

    # ── New agents alert ─────────────────────────────────────────────────────
    if new_agents:
        console.print("\n[bold yellow]🆕 NEWLY DETECTED AGENTS[/bold yellow]")
        for a in new_agents:
            console.print(
                f"  [green]+[/green] [bold]{a['name']}[/bold] "
                f"([dim]{a['role']}[/dim])  "
                f"[dim]{a['file']}[/dim]"
            )
            if a.get("description"):
                console.print(f"    [dim]{a['description'][:100]}[/dim]")

    # ── Removed agents alert ─────────────────────────────────────────────────
    if removed_agents:
        console.print("\n[bold red]❌ AGENTS NO LONGER FOUND[/bold red]")
        for name in removed_agents:
            console.print(f"  [red]-[/red] {name}")

    if not new_agents and not removed_agents:
        console.print("\n[green]✓ No changes detected since last scan.[/green]")

    # ── Full registry table ──────────────────────────────────────────────────
    console.print()
    table = Table(
        title="Full Agent Registry",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan"
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Agent Name", style="cyan")
    table.add_column("Role", style="magenta", width=10)
    table.add_column("Class", style="dim", width=28)
    table.add_column("File", style="dim")

    role_order = {"manager": 0, "domain": 1, "worker": 2, "helper": 3}
    sorted_agents = sorted(
        current.values(),
        key=lambda a: (role_order.get(a["role"], 9), a["name"])
    )

    for i, agent in enumerate(sorted_agents, 1):
        role_color = {
            "manager": "red", "domain": "yellow",
            "worker": "green", "helper": "blue"
        }.get(agent["role"], "white")
        table.add_row(
            str(i),
            agent["name"],
            f"[{role_color}]{agent['role']}[/{role_color}]",
            agent.get("class_name", "?"),
            agent["file"],
        )

    console.print(table)


def _print_plain_report(current, new_agents, removed_agents):
    """Fallback plain-text report (no rich)."""
    print(f"\n{'='*60}")
    print(f"UltraSwarm Agent Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total agents: {len(current)}")
    if new_agents:
        print(f"\nNEW AGENTS ({len(new_agents)}):")
        for a in new_agents:
            print(f"  + {a['name']} ({a['role']}) — {a['file']}")
    if removed_agents:
        print(f"\nREMOVED AGENTS ({len(removed_agents)}):")
        for name in removed_agents:
            print(f"  - {name}")
    print(f"\nALL AGENTS:")
    for name, info in sorted(current.items()):
        print(f"  [{info['role']:8}] {name:40} {info['file']}")
    print("="*60)


# ─────────────────────────────────────────────────────────────────────────────
# APEX NOTIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def notify_apex(new_agents: List[Dict]) -> None:
    """
    If new agents are detected and an APEX Orchestrator instance is importable,
    trigger a registry refresh so it immediately becomes aware.
    """
    if not new_agents:
        return
    try:
        from agents.managers.orchestrator_agent import OrchestratorAgent
        # We don't instantiate (expensive) — just write a flag file that
        # OrchestratorAgent.__init__ can read on next startup.
        flag = PROJECT_ROOT / ".new_agents_detected"
        flag.write_text(
            json.dumps([a["name"] for a in new_agents]),
            encoding="utf-8"
        )
        print(f"\n[Scanner] APEX notified — {len(new_agents)} new agent(s) flagged.")
        print(f"[Scanner] APEX will auto-refresh its registry on next invocation.")
    except Exception as e:
        print(f"[Scanner] Could not notify APEX: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# WATCH MODE
# ─────────────────────────────────────────────────────────────────────────────

def watch_mode(interval: int = 30) -> None:
    """Continuously monitors for new agents every `interval` seconds."""
    print(f"[Scanner] Watch mode active — checking every {interval}s. Ctrl+C to stop.")
    try:
        while True:
            previous = load_snapshot()
            current = scan_agent_directories()
            new_agents, removed = diff_agents(previous, current)
            if new_agents or removed:
                print(f"\n[Scanner] Change detected at {datetime.now().strftime('%H:%M:%S')}!")
                print_report(current, new_agents, removed)
                save_snapshot(current)
                notify_apex(new_agents)
            else:
                print(f"[Scanner] {datetime.now().strftime('%H:%M:%S')} — No changes.", end="\r")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[Scanner] Watch mode stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UltraSwarm Agent Scanner — detects new/removed agents in the codebase."
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Watch for changes continuously (default interval: 30s)."
    )
    parser.add_argument(
        "--interval", type=int, default=30,
        help="Watch interval in seconds (default: 30)."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON (useful for CI pipelines)."
    )
    parser.add_argument(
        "--update-apex", action="store_true",
        help="Notify APEX to refresh registry if new agents are found."
    )
    parser.add_argument(
        "--no-snapshot", action="store_true",
        help="Skip saving snapshot (dry-run mode)."
    )
    args = parser.parse_args()

    if args.watch:
        watch_mode(interval=args.interval)
        return

    previous = load_snapshot()
    current = scan_agent_directories()
    new_agents, removed = diff_agents(previous, current)

    print_report(current, new_agents, removed, json_mode=args.json)

    if not args.no_snapshot:
        save_snapshot(current)

    if args.update_apex:
        notify_apex(new_agents)

    # Exit code 1 if changes detected (useful for CI checks)
    sys.exit(1 if (new_agents or removed) else 0)


if __name__ == "__main__":
    main()
