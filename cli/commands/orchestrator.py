"""Orchestration commands — swarms and orchestrator control"""

import typer
from rich.console import Console
from rich.panel import Panel

from cli.utils import (
    get_orchestrator,
    print_success, print_error, print_info
)

console = Console()
app = typer.Typer(help="Run swarms and orchestrator")


@app.command(name="run")
def run_swarm(
    swarm_type: str = typer.Argument(
        ...,
        help="Swarm type: product|marketing|seo|full"
    ),
):
    """Run a swarm"""
    swarms = {
        "product": "Product Research Swarm",
        "marketing": "Marketing Campaign Swarm",
        "seo": "SEO Deep Dive Swarm",
        "full": "Full Launch Swarm"
    }
    
    if swarm_type not in swarms:
        print_error("Unknown swarm", f"Must be: {', '.join(swarms.keys())}")
        return
    
    try:
        swarm_name = swarms[swarm_type]
        console.print(f"\n[bold cyan]Starting {swarm_name}...[/bold cyan]\n")
        
        if swarm_type == "product":
            from swarms.product_swarm import run_product_swarm
            topic = console.input("[Product Research] Topic/niche: ").strip()
            competitor = console.input("[Product Research] Competitor URL (optional): ").strip()
            run_product_swarm(topic, competitor or None)
        
        elif swarm_type == "marketing":
            from swarms.marketing_swarm import run_marketing_swarm
            product = console.input("[Marketing] Product name: ").strip()
            desc = console.input("[Marketing] Description (optional): ").strip()
            run_marketing_swarm(product, desc)
        
        elif swarm_type == "seo":
            from swarms.seo_swarm import run_seo_swarm
            kws_input = console.input("[SEO] Keywords (comma-separated): ").strip()
            kws = [k.strip() for k in kws_input.split(",") if k.strip()]
            comps_input = console.input("[SEO] Competitor URLs (comma-separated, optional): ").strip()
            comps = [c.strip() for c in comps_input.split(",") if c.strip()] if comps_input else []
            run_seo_swarm(keywords=kws, competitors=comps)
        
        elif swarm_type == "full":
            from swarms.full_launch_swarm import run_full_launch_swarm
            product = console.input("[Full Launch] Product name: ").strip()
            desc = console.input("[Full Launch] Description (optional): ").strip()
            competitor = console.input("[Full Launch] Competitor URL (optional): ").strip()
            run_full_launch_swarm(product, desc, competitor or None)
        
        print_success("Swarm completed", f"{swarm_name} finished")
    
    except Exception as e:
        print_error("Swarm failed", str(e))
        import traceback
        traceback.print_exc()


@app.command(name="apex")
def run_orchestrator(
    goal: str = typer.Option(None, "--goal", "-g", help="Single goal to execute"),
):
    """Run the Supreme Orchestrator (APEX)"""
    try:
        orchestrator = get_orchestrator()
        if not orchestrator:
            print_error("Failed to initialize orchestrator", "Could not create orchestrator agent")
            return
        
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]🚀 SUPREME ORCHESTRATOR (APEX) ACTIVATED[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        if goal:
            # Non-interactive: single goal
            console.print(f"[dim]Goal: {goal}[/dim]\n")
            result = orchestrator.run({
                "goal": goal,
                "session_id": "cli_session",
                "refresh_registry": True
            })
            
            if result.get("success"):
                print_success("Orchestrator completed", "")
                console.print(f"[cyan]{result.get('output', '')}[/cyan]")
                metadata = result.get('metadata', {})
                console.print(f"\n[dim]Registry size: {metadata.get('registry_size', 0)} agents")
                console.print(f"Subtasks completed: {metadata.get('subtask_count', 0)}[/dim]")
            else:
                print_error("Orchestrator failed", result.get('error', 'Unknown error'))
            return
        
        # Interactive mode
        console.print("[dim]You are connected to the Supreme Orchestrator.")
        console.print("It will delegate tasks to any agent in the registry.")
        console.print("Type 'quit' to exit.\n[/dim]")
        
        while True:
            user_goal = console.input("\n[APEX] Your goal: ").strip()
            
            if user_goal.lower() in ["quit", "exit", "q"]:
                console.print("[dim]Goodbye.[/dim]")
                break
            
            if not user_goal:
                continue
            
            console.print("\n[bold cyan]Sending to APEX...[/bold cyan]")
            
            result = orchestrator.run({
                "goal": user_goal,
                "session_id": "cli_session",
                "refresh_registry": True
            })
            
            if result.get("success"):
                console.print(f"\n[green]✓ Success:[/green]")
                console.print(f"[cyan]{result.get('output', '')}[/cyan]")
                metadata = result.get('metadata', {})
                console.print(f"\n[dim]Registry: {metadata.get('registry_size', 0)} agents | Tasks: {metadata.get('subtask_count', 0)}[/dim]")
            else:
                console.print(f"\n[red]✗ Error:[/red]")
                console.print(f"[dim]{result.get('error', 'Unknown error')}[/dim]")
    
    except Exception as e:
        print_error("Orchestrator failed", str(e))
        import traceback
        traceback.print_exc()
