"""
tools/output_manager.py
=======================
Handles saving agent outputs to disk in organized folders.
Every agent's work is saved automatically with timestamps.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from typing import Optional

console = Console()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))


def save_output(agent_name: str, task: str, content: any, fmt: str = "txt") -> str:
    """
    Save agent output to organized directory structure.
    Returns the file path.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    agent_dir = OUTPUT_DIR / agent_name.lower().replace(" ", "_")
    agent_dir.mkdir(parents=True, exist_ok=True)

    safe_task = task[:40].replace(" ", "_").replace("/", "-")
    filename = f"{safe_task}_{timestamp}.{fmt}"
    filepath = agent_dir / filename

    if fmt == "json":
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(str(content))

    console.print(f"[green]Saved:[/green] {filepath}")
    return str(filepath)


def load_latest(agent_name: str) -> Optional[str]:
    """Load the most recent output from an agent (for agent-to-agent handoff)."""
    agent_dir = OUTPUT_DIR / agent_name.lower().replace(" ", "_")
    if not agent_dir.exists():
        return None
    files = sorted(agent_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    if files:
        with open(files[0], "r", encoding="utf-8") as f:
            return f.read()
    return None


def list_outputs(agent_name: str = None) -> list[dict]:
    """List all saved outputs, optionally filtered by agent."""
    results = []
    search_dir = OUTPUT_DIR / agent_name.lower().replace(" ", "_") if agent_name else OUTPUT_DIR
    if not search_dir.exists():
        return []
    for f in sorted(search_dir.rglob("*"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
        if f.is_file():
            results.append({"name": f.name, "path": str(f), "size": f.stat().st_size})
    return results


# Fix missing Optional import
from typing import Optional
