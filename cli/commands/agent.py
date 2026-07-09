"""Agent management commands — list, run, create, describe"""

import typer
import json
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from cli.utils import (
    discover_agents, get_agent_registry, format_agents_table,
    validate_agent_name, print_success, print_error, print_info
)

console = Console()
app = typer.Typer(help="Manage and run agents")


@app.command(name="list")
def list_agents():
    """List all available agents"""
    agents = discover_agents()
    
    if not agents:
        print_error("No agents found", "Check agents/ directory exists")
        return
    
    console.print(format_agents_table(agents))
    console.print(f"\n[dim]{len(agents)} agents available[/dim]")


@app.command(name="describe")
def describe_agent(name: str = typer.Argument(..., help="Agent name to describe")):
    """Show detailed info about an agent"""
    agents = discover_agents()
    
    if name not in agents:
        print_error("Agent not found", f"'{name}' not in available agents")
        console.print(f"[dim]Available: {', '.join(sorted(agents.keys()))}[/dim]")
        return
    
    agent = agents[name]
    
    panel_content = f"""
[bold cyan]Name:[/bold cyan] {agent['name']}
[bold cyan]File:[/bold cyan] {agent['file']}
[bold cyan]Domain:[/bold cyan] {agent.get('domain', 'unknown')}
[bold cyan]Status:[/bold cyan] {agent.get('status', 'unknown')}
"""
    
    console.print(Panel(panel_content.strip(), title=f"📋 Agent: {name}", border_style="cyan"))


@app.command(name="run")
def run_agent(
    name: str = typer.Argument(..., help="Agent name to run"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="JSON context input"),
    task: Optional[str] = typer.Option(None, "--task", "-t", help="Task to execute (non-interactive)"),
):
    """Run an agent interactively or with a specific task"""
    from core.base_agent import BaseAgent
    
    agents = discover_agents()
    
    if name not in agents:
        print_error("Agent not found", f"'{name}' not available")
        return
    
    try:
        # Try to get from registry first
        registry = get_agent_registry()
        if name in registry:
            agent = registry[name]
        else:
            # Fall back to BaseAgent
            agent = BaseAgent(skill_name=name, domain=agents[name].get('domain', 'general'))
        
        console.print(f"\n[green]✓ Loaded agent:[/green] {name}\n")
        
        # Parse context if provided
        context_data = None
        if context:
            try:
                context_data = json.loads(context)
            except json.JSONDecodeError:
                print_warning("Invalid JSON context, ignoring")
        
        # Non-interactive mode: run single task
        if task:
            console.print(f"[dim]Executing task: {task}[/dim]\n")
            result = agent.execute_task(task, context_data)
            
            if result.status == "success":
                print_success("Task completed")
                console.print(f"[cyan]{result.message}[/cyan]")
                if result.data:
                    console.print(f"[dim]Output:[/dim] {result.data}")
            else:
                print_error("Task failed", result.message)
            return
        
        # Interactive mode
        console.print("[dim]Interactive mode. Type 'quit' to exit.[/dim]\n")
        while True:
            task_input = console.input(f"\n[{name}] Task: ").strip()
            
            if task_input.lower() in ["quit", "exit", "q"]:
                break
            
            if not task_input:
                continue
            
            context_input = console.input(f"[{name}] Context (JSON, optional): ").strip()
            context_for_task = None
            if context_input:
                try:
                    context_for_task = json.loads(context_input)
                except json.JSONDecodeError:
                    console.print("[yellow]Invalid JSON, skipping context[/yellow]")
            
            result = agent.execute_task(task_input, context_for_task)
            
            if result.status == "success":
                console.print(f"\n[green]✓ Success:[/green]")
                console.print(f"[cyan]{result.message}[/cyan]")
                if result.data:
                    console.print(f"[dim]Output:[/dim] {result.data}")
            else:
                console.print(f"\n[red]✗ Error:[/red]")
                console.print(f"[cyan]{result.message}[/cyan]")
    
    except Exception as e:
        print_error("Failed to run agent", str(e))
        import traceback
        traceback.print_exc()


@app.command(name="create")
def create_agent(
    name: str = typer.Argument(..., help="Name for new agent"),
    agent_type: str = typer.Option("worker", "--type", "-t", help="Type: worker or helper"),
):
    """Create a new agent from template"""
    # Validate name
    valid, msg = validate_agent_name(name)
    if not valid:
        print_error("Invalid agent name", msg)
        return
    
    if agent_type not in ["worker", "helper"]:
        print_error("Invalid type", "Must be 'worker' or 'helper'")
        return
    
    try:
        # Determine target directory
        if agent_type == "worker":
            target_dir = Path("agents/workers")
        else:
            target_dir = Path("agents/helpers")
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Load template
        template_path = Path(__file__).parent.parent / "templates" / f"{agent_type}_agent.py"
        if not template_path.exists():
            print_error("Template not found", f"Missing template: {template_path}")
            return
        
        with open(template_path, 'r') as f:
            template = f.read()
        
        # Substitute agent name
        agent_code = template.replace("__AGENT_NAME__", name)
        agent_code = agent_code.replace("__AGENT_CLASS__", name.title().replace("_", ""))
        
        # Write agent file
        agent_file = target_dir / f"{name}_agent.py"
        agent_file.write_text(agent_code)
        
        # Create skill file
        skill_data = {
            "name": name,
            "description": f"{name.replace('_', ' ').title()} Agent",
            "domain": "workers" if agent_type == "worker" else "helpers",
            "system_prompt": f"You are the {name.replace('_', ' ').title()} Agent.",
            "capabilities": ["task_execution", "analysis"],
            "models": ["gemini-2.5-flash-preview-05-20"],
            "temperature": 0.7
        }
        
        skill_dir = Path("skills") / ("workers" if agent_type == "worker" else "helpers")
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / f"{name}.json"
        
        with open(skill_file, 'w') as f:
            json.dump(skill_data, f, indent=2)
        
        print_success("Agent created", f"New {agent_type} agent: {name}")
        console.print(f"\n[dim]Files created:[/dim]")
        console.print(f"  [cyan]{agent_file}[/cyan]")
        console.print(f"  [cyan]{skill_file}[/cyan]")
        
    except Exception as e:
        print_error("Failed to create agent", str(e))


# Import after defining to avoid circular imports
def print_warning(title: str, message: str = ""):
    from cli.utils import print_warning as util_warning
    util_warning(title, message)
