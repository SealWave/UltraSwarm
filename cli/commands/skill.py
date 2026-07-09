"""Skill management commands — list, add, validate, describe"""

import typer
import json
from pathlib import Path
from rich.console import Console

from cli.utils import (
    discover_skills, format_skills_table, validate_skill_file,
    print_success, print_error, print_info, print_warning
)

console = Console()
app = typer.Typer(help="Manage skills")


@app.command(name="list")
def list_skills():
    """List all available skills"""
    skills = discover_skills()
    
    if not skills:
        print_warning("No skills found", "Check skills/ directory exists")
        return
    
    console.print(format_skills_table(skills))
    console.print(f"\n[dim]{len(skills)} skills available[/dim]")


@app.command(name="describe")
def describe_skill(
    name: str = typer.Argument(..., help="Skill name to describe")
):
    """Show detailed info about a skill"""
    skills = discover_skills()
    
    if name not in skills:
        print_error("Skill not found", f"'{name}' not in available skills")
        console.print(f"[dim]Available: {', '.join(sorted(skills.keys()))}[/dim]")
        return
    
    skill = skills[name]
    
    # Load full skill data
    try:
        with open(skill['file'], 'r') as f:
            skill_data = json.load(f)
    except Exception as e:
        print_error("Failed to load skill", str(e))
        return
    
    from rich.panel import Panel
    from rich.syntax import Syntax
    
    # Build detailed output
    panel_content = f"""
[bold cyan]Name:[/bold cyan] {skill['name']}
[bold cyan]Domain:[/bold cyan] {skill.get('domain', 'general')}
[bold cyan]Description:[/bold cyan] {skill.get('description', 'No description')}
[bold cyan]File:[/bold cyan] {skill['file']}

[bold cyan]Capabilities:[/bold cyan]
"""
    
    for cap in skill.get('capabilities', []):
        panel_content += f"\n  • {cap}"
    
    console.print(Panel(panel_content.strip(), title=f"🔧 Skill: {name}", border_style="cyan"))
    
    # Show system prompt preview
    if 'system_prompt' in skill_data:
        prompt_preview = skill_data['system_prompt'][:200]
        if len(skill_data['system_prompt']) > 200:
            prompt_preview += "..."
        console.print(f"\n[bold cyan]System Prompt:[/bold cyan]\n[dim]{prompt_preview}[/dim]")


@app.command(name="validate")
def validate_skill(
    path: str = typer.Argument(..., help="Path to skill JSON file")
):
    """Validate a skill file"""
    valid, msg = validate_skill_file(path)
    
    if valid:
        print_success("Skill validation", msg)
        
        # Load and show summary
        try:
            with open(path, 'r') as f:
                skill_data = json.load(f)
            
            console.print(f"\n[dim]Skill Details:[/dim]")
            console.print(f"  Name: {skill_data.get('name', 'N/A')}")
            console.print(f"  Description: {skill_data.get('description', 'N/A')}")
            console.print(f"  Capabilities: {len(skill_data.get('capabilities', []))} defined")
            console.print(f"  Domain: {skill_data.get('domain', 'general')}")
        except Exception as e:
            console.print(f"[yellow]Note: Could not load full details: {e}[/yellow]")
    else:
        print_error("Skill validation failed", msg)


@app.command(name="add")
def add_skill(
    path: str = typer.Argument(..., help="Path to skill JSON file"),
    test: bool = typer.Option(True, "--test/--no-test", help="Test skill with mock agent"),
):
    """Add a new skill, validate, and optionally test it"""
    from pathlib import Path
    
    skill_path = Path(path)
    
    # Step 1: Validate file
    valid, msg = validate_skill_file(path)
    if not valid:
        print_error("Validation failed", msg)
        return
    
    console.print(f"[green]✓[/green] Skill file valid")
    
    # Load skill data
    with open(skill_path, 'r') as f:
        skill_data = json.load(f)
    
    skill_name = skill_data.get('name', skill_path.stem)
    
    # Step 2: Copy to skills directory
    try:
        target_dir = Path("skills") / skill_data.get('domain', 'general')
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{skill_name}.json"
        
        with open(target_file, 'w') as f:
            json.dump(skill_data, f, indent=2)
        
        console.print(f"[green]✓[/green] Skill copied to {target_file}")
    except Exception as e:
        print_error("Failed to copy skill", str(e))
        return
    
    # Step 3: Test with mock agent
    if test:
        try:
            from core.base_agent import BaseAgent
            
            console.print(f"\n[dim]Testing skill with mock agent...[/dim]")
            agent = BaseAgent(skill_name=skill_name, domain=skill_data.get('domain', 'general'))
            
            # Simple test: check if agent initialized
            if agent.skill:
                console.print(f"[green]✓[/green] Skill loaded successfully in agent")
                console.print(f"  Skill name: {agent.skill.name}")
                console.print(f"  Model: {agent.skill.models}")
            else:
                print_warning("Skill test", "Skill loaded but skill object is None")
        except Exception as e:
            print_warning("Skill test failed", str(e))
            console.print("[dim]Note: Skill was added, but test failed. It may still be usable.[/dim]")
    
    print_success("Skill added successfully", f"'{skill_name}' is now available")


@app.command(name="remove")
def remove_skill(
    name: str = typer.Argument(..., help="Skill name to remove"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
):
    """Remove a skill"""
    skills = discover_skills()
    
    if name not in skills:
        print_error("Skill not found", f"'{name}' not in available skills")
        return
    
    skill_file = skills[name]['file']
    
    if not confirm:
        console.print(f"[yellow]Delete skill:[/yellow] {skill_file}")
        if not typer.confirm("Continue?", default=False):
            console.print("[dim]Cancelled[/dim]")
            return
    
    try:
        Path(skill_file).unlink()
        print_success("Skill removed", f"Deleted {skill_file}")
    except Exception as e:
        print_error("Failed to remove skill", str(e))
