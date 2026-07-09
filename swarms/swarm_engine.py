"""
swarms/swarm_engine.py
=======================
The Swarm Engine — coordinates multiple agents running in sequence/parallel.
Each swarm is a named workflow that chains agents together with shared context.
"""

import time
import json
from typing import Callable
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from tools.output_manager import save_output

console = Console()


class SwarmResult:
    """Holds the accumulated output of a swarm run."""
    def __init__(self, swarm_name: str):
        self.swarm_name = swarm_name
        self.results = {}
        self.errors = {}
        self.start_time = time.time()

    def add(self, agent_name: str, result: any):
        self.results[agent_name] = result

    def add_error(self, agent_name: str, error: str):
        self.errors[agent_name] = error

    def elapsed(self) -> str:
        seconds = int(time.time() - self.start_time)
        return f"{seconds // 60}m {seconds % 60}s"

    def summary(self) -> dict:
        return {
            "swarm": self.swarm_name,
            "elapsed": self.elapsed(),
            "agents_completed": list(self.results.keys()),
            "agents_failed": list(self.errors.keys()),
            "results": self.results,
        }


def run_agent_step(name: str, fn: Callable, result_store: SwarmResult, *args, **kwargs):
    """Run a single agent step with error handling and progress display."""
    console.print(f"\n[bold]Running:[/bold] [cyan]{name}[/cyan]")
    try:
        result = fn(*args, **kwargs)
        result_store.add(name, result)
        console.print(f"[green]-- {name} complete[/green]")
        return result
    except Exception as e:
        console.print(f"[red]!! {name} failed: {e}[/red]")
        result_store.add_error(name, str(e))
        return None


def print_swarm_header(swarm_name: str, description: str, agents: list):
    table = Table(title=f"Swarm: {swarm_name}", border_style="cyan", show_header=False)
    table.add_column("", style="dim")
    table.add_column("")
    table.add_row("Description", description)
    table.add_row("Agents", " -> ".join(agents))
    console.print(table)


def print_swarm_summary(result: SwarmResult):
    console.print(Panel(
        f"[green]Swarm Complete[/green]\n"
        f"Time: {result.elapsed()}\n"
        f"Agents done: {len(result.results)}\n"
        f"Errors: {len(result.errors)}\n"
        f"Outputs saved to: ./outputs/",
        title=f"Complete: {result.swarm_name}",
        border_style="green"
    ))
