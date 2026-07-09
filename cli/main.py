"""UltraSwarm CLI — Main entry point and app setup"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

import typer
import os
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich import box

# Import command groups
from cli.commands import agent as agent_cmd
from cli.commands import skill as skill_cmd
from cli.commands import rag as rag_cmd
from cli.commands import orchestrator as orch_cmd
from cli.utils import print_success, print_info

console = Console()

# ──────────────────────────────────────────────────────────────────────────
# APP SETUP
# ──────────────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="uswarm",
    help="🐝 UltraSwarm — Multi-Agent Control System",
    no_args_is_help=False
)

# Add command groups
app.add_typer(agent_cmd.app, name="agent", help="Manage and run agents")
app.add_typer(skill_cmd.app, name="skill", help="Manage skills")
app.add_typer(rag_cmd.app, name="rag", help="Query and manage knowledge base")
app.add_typer(orch_cmd.app, name="swarm", help="Run swarms and orchestrator")


# ──────────────────────────────────────────────────────────────────────────
# INTERACTIVE MENU
# ──────────────────────────────────────────────────────────────────────────

BANNER = """
[bold cyan]
███████╗ ██████╗ ██████╗ ███╗   ███╗    ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
██╔════╝██╔════╝██╔═══██╗████╗ ████║    ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
█████╗  ██║     ██║   ██║██╔████╔██║    ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
██╔══╝  ██║     ██║   ██║██║╚██╔╝██║    ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║    ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
[/bold cyan]
[dim]  AI-Powered Multi-Agent Swarm | CLI Control System[/dim]
"""


def show_interactive_menu():
    """Show enhanced interactive menu"""
    from cli.utils import discover_agents, get_agent_registry
    from tools.browser_bootstrap import describe_browser_status
    
    console.print(BANNER)
    
    # Configuration summary
    store_url = os.getenv("STORE_URL", "not set")
    niche = os.getenv("STORE_NICHE", "not set")
    
    use_local = os.getenv("USE_LOCAL_LLM", "").lower() in ["true", "1", "yes"]
    if use_local:
        model = os.getenv("LOCAL_MODEL_NAME", "liquid/lfm2.5-1.2b") + " (Local)"
    else:
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")
    
    from rich.table import Table
    config_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    config_table.add_column("", style="dim")
    config_table.add_column("")
    config_table.add_row("Store", store_url)
    config_table.add_row("Niche", niche)
    config_table.add_row("Model", model)
    config_table.add_row("Outputs", "./outputs/")
    console.print(config_table)
    
    while True:
        console.print("\n[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]")
        console.print("[bold]AGENTS[/bold] (discovery and execution)")
        console.print("  [cyan]1[/cyan]  List all agents")
        console.print("  [cyan]2[/cyan]  Run an agent")
        console.print("  [cyan]3[/cyan]  Create new agent")
        console.print("  [cyan]4[/cyan]  Describe agent")
        
        console.print("\n[bold]SKILLS[/bold] (capability management)")
        console.print("  [cyan]5[/cyan]  List all skills")
        console.print("  [cyan]6[/cyan]  Add new skill")
        console.print("  [cyan]7[/cyan]  Validate skill file")
        
        console.print("\n[bold]KNOWLEDGE BASE[/bold] (RAG system)")
        console.print("  [cyan]8[/cyan]  Query knowledge base")
        console.print("  [cyan]9[/cyan]  RAG status")
        console.print("  [cyan]10[/cyan] Add document")
        console.print("  [cyan]11[/cyan] Reindex knowledge")
        
        console.print("\n[bold]ORCHESTRATION[/bold] (multi-agent)")
        console.print("  [cyan]12[/cyan] Run swarm (product/marketing/seo/full)")
        console.print("  [cyan]13[/cyan] Supreme Orchestrator (APEX)")
        
        console.print("\n  [dim]0  Exit[/dim]")
        console.print("[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]")
        
        choice = console.input("\nSelect [0-13]: ").strip()
        
        if choice == "0":
            console.print("[dim]Goodbye.[/dim]")
            break
        
        elif choice == "1":
            from cli.commands.agent import list_agents
            list_agents()
        
        elif choice == "2":
            name = console.input("Agent name: ").strip()
            if name:
                from cli.commands.agent import run_agent
                run_agent(name)
        
        elif choice == "3":
            name = console.input("New agent name: ").strip()
            agent_type = console.input("Type (worker/helper) [worker]: ").strip() or "worker"
            if name:
                from cli.commands.agent import create_agent
                create_agent(name, agent_type)
        
        elif choice == "4":
            name = console.input("Agent name: ").strip()
            if name:
                from cli.commands.agent import describe_agent
                describe_agent(name)
        
        elif choice == "5":
            from cli.commands.skill import list_skills
            list_skills()
        
        elif choice == "6":
            path = console.input("Path to skill JSON: ").strip()
            if path:
                from cli.commands.skill import add_skill
                add_skill(path)
        
        elif choice == "7":
            path = console.input("Path to skill JSON: ").strip()
            if path:
                from cli.commands.skill import validate_skill
                validate_skill(path)
        
        elif choice == "8":
            question = console.input("Question: ").strip()
            if question:
                from cli.commands.rag import query_knowledge
                query_knowledge(question)
        
        elif choice == "9":
            from cli.commands.rag import rag_status
            rag_status()
        
        elif choice == "10":
            path = console.input("Document path: ").strip()
            if path:
                from cli.commands.rag import add_document
                add_document(path)
        
        elif choice == "11":
            from cli.commands.rag import reindex_knowledge
            reindex_knowledge()
        
        elif choice == "12":
            swarm = console.input("Swarm type (product/marketing/seo/full): ").strip()
            if swarm:
                from cli.commands.orchestrator import run_swarm
                run_swarm(swarm)
        
        elif choice == "13":
            from cli.commands.orchestrator import run_orchestrator
            run_orchestrator()
        
        else:
            console.print("[red]Invalid choice[/red]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """UltraSwarm CLI — Multi-Agent Control System"""
    # If no command specified, show interactive menu
    if ctx.invoked_subcommand is None:
        show_interactive_menu()


if __name__ == "__main__":
    app()
