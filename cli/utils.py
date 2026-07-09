"""CLI utilities — formatting, loading, validation shared across all commands"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

# ──────────────────────────────────────────────────────────────────────────
# AGENT DISCOVERY & LOADING
# ──────────────────────────────────────────────────────────────────────────

def discover_agents() -> Dict[str, Dict[str, Any]]:
    """Discover all available agents by scanning agents/ directory"""
    agents = {}
    agents_dir = Path("agents")
    
    if not agents_dir.exists():
        return agents
    
    # Scan for agent files
    for agent_file in agents_dir.rglob("*_agent.py"):
        if agent_file.name.startswith("_"):
            continue
        
        try:
            agent_name = agent_file.stem.replace("_agent", "")
            domain = "ecommerce" if "ecommerce" in str(agent_file) else (
                "external" if "external" in str(agent_file) else
                "manager" if "managers" in str(agent_file) else
                "helper" if "helpers" in str(agent_file) else
                "worker"
            )
            
            agents[agent_name] = {
                "name": agent_name,
                "file": str(agent_file),
                "domain": domain,
                "status": "available"
            }
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load {agent_file}: {e}[/yellow]")
    
    return agents


def get_agent_registry() -> Dict[str, Any]:
    """Get the agent registry from core"""
    try:
        from agents.registry import build_registry
        return build_registry(verbose=False)
    except Exception as e:
        console.print(f"[yellow]Could not load agent registry: {e}[/yellow]")
        return {}


# ──────────────────────────────────────────────────────────────────────────
# SKILL DISCOVERY & LOADING
# ──────────────────────────────────────────────────────────────────────────

def discover_skills() -> Dict[str, Dict[str, Any]]:
    """Discover all available skills by scanning skills/ directory"""
    skills = {}
    skills_dir = Path("skills")
    
    if not skills_dir.exists():
        return skills
    
    for skill_file in skills_dir.rglob("*.json"):
        try:
            with open(skill_file, 'r') as f:
                skill_data = json.load(f)
            
            skill_name = skill_file.stem
            skills[skill_name] = {
                "name": skill_name,
                "file": str(skill_file),
                "domain": skill_data.get("domain", "general"),
                "description": skill_data.get("description", "No description"),
                "capabilities": skill_data.get("capabilities", [])
            }
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load {skill_file}: {e}[/yellow]")
    
    return skills


# ──────────────────────────────────────────────────────────────────────────
# TABLE FORMATTING
# ──────────────────────────────────────────────────────────────────────────

def format_agents_table(agents: Dict[str, Dict[str, Any]]) -> Table:
    """Format agents as a rich table"""
    table = Table(title="Available Agents", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green")
    table.add_column("Domain", style="yellow")
    table.add_column("Type", style="blue")
    table.add_column("Status", style="dim")
    
    for name, data in sorted(agents.items()):
        table.add_row(
            name,
            data.get("domain", "unknown"),
            data.get("type", "worker"),
            data.get("status", "available")
        )
    
    return table


def format_skills_table(skills: Dict[str, Dict[str, Any]]) -> Table:
    """Format skills as a rich table"""
    table = Table(title="Available Skills", show_header=True, header_style="bold cyan")
    table.add_column("Skill Name", style="green")
    table.add_column("Domain", style="yellow")
    table.add_column("Capabilities", style="blue")
    table.add_column("Description", style="dim")
    
    for name, data in sorted(skills.items()):
        caps = ", ".join(data.get("capabilities", [])[:2])
        if len(data.get("capabilities", [])) > 2:
            caps += f", +{len(data.get('capabilities', [])) - 2} more"
        
        table.add_row(
            name,
            data.get("domain", "general"),
            caps or "(none)",
            data.get("description", "")[:50]
        )
    
    return table


# ──────────────────────────────────────────────────────────────────────────
# VALIDATION
# ──────────────────────────────────────────────────────────────────────────

def validate_skill_file(skill_path: str) -> tuple[bool, str]:
    """Validate a skill JSON file"""
    path = Path(skill_path)
    
    if not path.exists():
        return False, f"File not found: {skill_path}"
    
    if not path.suffix == ".json":
        return False, "Skill file must be a JSON file"
    
    try:
        with open(path, 'r') as f:
            skill_data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    
    # Check required fields
    required = ["name", "description", "system_prompt"]
    missing = [f for f in required if f not in skill_data]
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    # Validate capabilities format
    if "capabilities" in skill_data and not isinstance(skill_data["capabilities"], list):
        return False, "capabilities must be a list"
    
    return True, "Valid skill file"


def validate_agent_name(name: str) -> tuple[bool, str]:
    """Validate agent name for creation"""
    if not name:
        return False, "Agent name cannot be empty"
    
    if not name.replace("_", "").isalnum():
        return False, "Agent name must be alphanumeric (underscores allowed)"
    
    if name.startswith("_"):
        return False, "Agent name cannot start with underscore"
    
    # Check if already exists
    agents = discover_agents()
    if name in agents:
        return False, f"Agent '{name}' already exists"
    
    return True, "Valid agent name"


# ──────────────────────────────────────────────────────────────────────────
# RAG ACCESS
# ──────────────────────────────────────────────────────────────────────────

def get_rag_manager():
    """Get the RAG manager from core"""
    try:
        from core.rag_manager import RAGManager
        return RAGManager()
    except Exception as e:
        console.print(f"[red]Failed to initialize RAG manager: {e}[/red]")
        return None


def query_rag(question: str, budget: int = 2000) -> Optional[str]:
    """Query the RAG system"""
    try:
        from core.rag_manager import query_knowledge
        return query_knowledge(question, budget=budget)
    except Exception as e:
        console.print(f"[red]RAG query failed: {e}[/red]")
        return None


# ──────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR ACCESS
# ──────────────────────────────────────────────────────────────────────────

def get_orchestrator():
    """Get the orchestrator agent"""
    try:
        from agents.managers.orchestrator_agent import OrchestratorAgent
        return OrchestratorAgent(skill_name="cli_orchestrator", domain="external", verbose=False)
    except Exception as e:
        console.print(f"[red]Failed to initialize orchestrator: {e}[/red]")
        return None


# ──────────────────────────────────────────────────────────────────────────
# OUTPUT FORMATTING
# ──────────────────────────────────────────────────────────────────────────

def print_success(title: str, message: str = ""):
    """Print success message"""
    if message:
        console.print(Panel(f"[green]{message}[/green]", title=f"✓ {title}", border_style="green"))
    else:
        console.print(f"[green]✓ {title}[/green]")


def print_error(title: str, message: str = ""):
    """Print error message"""
    if message:
        console.print(Panel(f"[red]{message}[/red]", title=f"✗ {title}", border_style="red"))
    else:
        console.print(f"[red]✗ {title}[/red]")


def print_info(title: str, message: str = ""):
    """Print info message"""
    if message:
        console.print(Panel(f"[cyan]{message}[/cyan]", title=f"ℹ {title}", border_style="cyan"))
    else:
        console.print(f"[cyan]ℹ {title}[/cyan]")


def print_warning(title: str, message: str = ""):
    """Print warning message"""
    if message:
        console.print(Panel(f"[yellow]{message}[/yellow]", title=f"⚠ {title}", border_style="yellow"))
    else:
        console.print(f"[yellow]⚠ {title}[/yellow]")
