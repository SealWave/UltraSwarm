#!/usr/bin/env python3
"""
main.py — ECOM SWARM Master Control
====================================
The single entry point for all agents and swarms.
Run from Termux: python main.py

Usage:
  python main.py                         # Interactive menu
  python main.py --cli                   # Modern CLI mode (Typer)
  python main.py --agent seo             # SEO agent standalone
  python main.py --agent product         # Product agent standalone
  python main.py --agent ads             # Ads agent standalone
  python main.py --agent social          # Social media agent standalone
  python main.py --agent banner          # Banner agent standalone
  python main.py --agent store           # Store manager standalone
  python main.py --agent browser         # Browser operator standalone
  python main.py --swarm product         # Product research swarm
  python main.py --swarm marketing       # Marketing campaign swarm
  python main.py --swarm seo             # SEO audit swarm
  python main.py --swarm full            # Full launch swarm (everything)
  python main.py --orchestrator          # Supreme Orchestrator (all agents)
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

# Check for --cli flag EARLY to delegate to Typer
if "--cli" in sys.argv:
    sys.argv.remove("--cli")
    from cli.main import app
    app()
    sys.exit(0)

from tools.browser_bootstrap import cleanup_browser_runtime, describe_browser_status, ensure_browser_cdp_url

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
except ImportError:
    print("Installing rich...")
    os.system("pip install rich")
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box

console = Console()

# ── ASCII Art Banner ──────────────────────────────────────────────────────────
BANNER = """
[bold cyan]
███████╗ ██████╗ ██████╗ ███╗   ███╗    ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
██╔════╝██╔════╝██╔═══██╗████╗ ████║    ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
█████╗  ██║     ██║   ██║██╔████╔██║    ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
██╔══╝  ██║     ██║   ██║██║╚██╔╝██║    ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║    ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
[/bold cyan]
[dim]  AI-Powered E-commerce Agent Swarm | Gemini 2.5 Flash | Built for Termux[/dim]
"""

# ── Validation ─────────────────────────────────────────────────────────────────
def bootstrap_browser_runtime():
    auto_start = os.getenv("BROWSER_USE_AUTO_START", "true").lower() in {"1", "true", "yes"}
    if not auto_start:
        return
    if os.getenv("BROWSER_USE_CLOUD", "").lower() in {"1", "true", "yes"}:
        return
    try:
        cdp_url = ensure_browser_cdp_url()
        if cdp_url:
            os.environ["BROWSER_USE_CDP_URL"] = cdp_url
            console.print(f"[dim]Browser CDP ready:[/dim] {cdp_url}")
    except Exception as exc:
        console.print(f"[yellow]Browser auto-start skipped:[/yellow] {exc}")


def check_config():
    use_local = os.getenv("USE_LOCAL_LLM", "").lower() in ["true", "1", "yes"]
    api_key = os.getenv("GOOGLE_API_KEY", "")
    
    if api_key or use_local:
        return
        
    console.print(Panel(
        "[bold yellow]LLM Configuration Missing[/bold yellow]\n\n"
        "You need to configure an LLM provider before running Swarms.\n"
        "Would you like to use [cyan]Google Gemini[/cyan] (API key) or a [green]Local LLM[/green] (e.g. LM Studio)?",
        title="Setup Wizard",
        border_style="yellow"
    ))
    
    console.print("\n[1] Google Gemini (Cloud API)")
    console.print("[2] Local LLM (LM Studio / Ollama)\n")
    
    choice = input("Select [1-2]: ").strip()
    
    env_path = Path(".env")
    env_content = env_path.read_text() if env_path.exists() else ""
    
    if choice == "1":
        key = input("\nEnter your GOOGLE_API_KEY: ").strip()
        if key:
            if "GOOGLE_API_KEY=" in env_content:
                import re
                env_content = re.sub(r'GOOGLE_API_KEY=.*', f'GOOGLE_API_KEY={key}', env_content)
            else:
                env_content += f"\nGOOGLE_API_KEY={key}\n"
            env_path.write_text(env_content)
            os.environ["GOOGLE_API_KEY"] = key
            console.print("[green]Saved Google API Key![/green]\n")
        else:
            console.print("[red]No key provided. Exiting.[/red]")
            sys.exit(1)
            
    elif choice == "2":
        default_url = "http://127.0.0.1:1234/v1"
        url = input(f"\nEnter Local LLM Base URL [{default_url}]: ").strip() or default_url
        
        default_model = "liquid/lfm2.5-1.2b"
        model = input(f"Enter Model Name [{default_model}]: ").strip() or default_model
        
        config = f"\n# --- Local LLM Config ---\nUSE_LOCAL_LLM=true\nLOCAL_LLM_URL={url}\nLOCAL_MODEL_NAME={model}\n"
        env_content += config
        env_path.write_text(env_content)
        
        os.environ["USE_LOCAL_LLM"] = "true"
        os.environ["LOCAL_LLM_URL"] = url
        os.environ["LOCAL_MODEL_NAME"] = model
        
        console.print("[green]Saved Local LLM Configuration![/green]\n")
    else:
        console.print("[red]Invalid choice. Exiting.[/red]")
        sys.exit(1)


# ── Agent runners ──────────────────────────────────────────────────────────────
def run_agent(agent_name: str):
    bootstrap_browser_runtime()
    
    # Check for standalone agent files first
    standalone_agents = {
        "seo": "agents.seo_agent",
        "product": "agents.product_agent",
        "ads": "agents.ads_agent",
        "social": "agents.social_agent",
        "banner": "agents.banner_agent",
        "store": "agents.store_manager_agent",
        "browser": "agents.browser_operator_agent",
    }
    
    if agent_name in standalone_agents:
        module_path = standalone_agents[agent_name]
        try:
            module = __import__(module_path, fromlist=[""])
            agent_class = getattr(module, agent_name.capitalize().replace("_", "") + "Agent")
            agent = agent_class()
            agent.run_interactive()
            return
        except Exception as e:
            console.print(f"[yellow]Standalone agent not found for {agent_name}: {e}[/yellow]")

    # Use BaseAgent with validation layer
    try:
        from core.base_agent import BaseAgent
        
        # Get the agent class from the registry
        from agents.registry import build_registry
        registry = build_registry(verbose=False)
        
        if agent_name not in registry:
            # Try common naming variations
            variations = [agent_name.replace("_", ""), agent_name.replace("-", "_")]
            for var in variations:
                if var in registry:
                    agent_name = var
                    break
            else:
                console.print(f"[red]Unknown agent: {agent_name}[/red]")
                console.print(f"[dim]Available agents: {', '.join(registry.keys())}[/dim]")
                return
        
        agent = registry[agent_name]
        console.print(f"[green]Running agent: {agent.name}[/green]")
        
        while True:
            task = input(f"\n[{agent.name}] Enter task (or 'quit' to exit): ").strip()
            if task.lower() in ["quit", "exit", "q"]:
                break
            
            context_input = input(f"[{agent.name}] Context (optional, JSON format): ").strip()
            context = None
            if context_input:
                try:
                    context = eval(context_input)  # Simple eval for JSON-like dicts
                except:
                    console.print("[yellow]Invalid context format, using None[/yellow]")
            
            result = agent.execute_task(task, context)
            
            if result.status == "success":
                console.print(f"\n[green]✓ Success:[/green]")
                console.print(f"[dim]{result.message}[/dim]")
                if result.data:
                    console.print(f"[cyan]Output:[/cyan] {result.data}")
            else:
                console.print(f"\n[red]✗ Error:[/red]")
                console.print(f"[dim]{result.message}[/dim]")
                if result.data:
                    console.print(f"[yellow]Details:[/yellow] {result.data}")
            
            if result.context_for_next:
                console.print(f"[dim]Context for next agent:[/dim] {result.context_for_next}")
    
    except Exception as e:
        console.print(f"[red]Failed to run agent: {e}[/red]")
        import traceback
        traceback.print_exc()


def run_swarm(swarm_name: str):
    bootstrap_browser_runtime()
    
    if swarm_name == "product":
        from swarms.product_swarm import run_product_swarm
        topic = input("Product/niche to research: ").strip()
        competitor = input("Competitor URL (optional): ").strip()
        run_product_swarm(topic, competitor or None)

    elif swarm_name == "marketing":
        from swarms.marketing_swarm import run_marketing_swarm
        product = input("Product name: ").strip()
        desc = input("Description (optional): ").strip()
        run_marketing_swarm(product, desc)

    elif swarm_name == "seo":
        from swarms.seo_swarm import run_seo_swarm
        kws = input("Keywords (comma separated): ").strip().split(",")
        comps_input = input("Competitor URLs (comma separated, optional): ").strip()
        comps = [c.strip() for c in comps_input.split(",") if c.strip()] if comps_input else []
        run_seo_swarm(keywords=[k.strip() for k in kws], competitors=comps)

    elif swarm_name == "full":
        from swarms.full_launch_swarm import run_full_launch_swarm
        product = input("Product name: ").strip()
        desc = input("Description (optional): ").strip()
        competitor = input("Competitor URL (optional): ").strip()
        run_full_launch_swarm(product, desc, competitor or None)

    else:
        console.print(f"[red]Unknown swarm: {swarm_name}[/red]")


def run_supreme_orchestrator():
    """Run the Supreme Orchestrator that can delegate to any agent"""
    bootstrap_browser_runtime()
    
    try:
        console.print("\n[bold cyan]=== SUPREME ORCHESTRATOR (APEX) ===[/bold cyan]")
        console.print("Initializing registry - loading all agents...")
        
        from agents.managers.orchestrator_agent import OrchestratorAgent
        
        orchestrator = OrchestratorAgent(skill_name="supreme_orchestrator", domain="external", verbose=False)
        
        console.print(f"[green]✓ Registry loaded with {len(orchestrator._agent_registry)} agents![/green]")
        console.print("[dim]Agents available: " + ", ".join(list(orchestrator._agent_registry.keys())[:15]) + "[/dim]")
        console.print("\nYou are now connected to the Supreme Orchestrator.")
        console.print("It can delegate tasks to any agent in the registry.")
        console.print("Type 'quit' to exit.\n")
        
        while True:
            goal = input("\n[User] ").strip()
            if goal.lower() in ["quit", "exit", "q"]:
                break
            
            if not goal:
                continue
            
            console.print("\n[bold]Sending to APEX...[/bold]")
            
            result = orchestrator.run({
                "goal": goal,
                "session_id": "user_session",
                "refresh_registry": True
            })
            
            if result.get("success"):
                console.print(f"\n[green]✓ Success:[/green]")
                console.print(f"[cyan]{result.get('output', '')}[/cyan]")
                console.print(f"\n[dim]Registry size: {result.get('metadata', {}).get('registry_size', 0)} agents")
                console.print(f"Subtasks completed: {result.get('metadata', {}).get('subtask_count', 0)}[/dim]")
            else:
                console.print(f"\n[red]✗ Error:[/red]")
                console.print(f"[dim]{result.get('error', 'Unknown error')}[/dim]")
    
    except Exception as e:
        console.print(f"[red]Failed to run orchestrator: {e}[/red]")
        import traceback
        traceback.print_exc()


# ── Hierarchical Menu System ───────────────────────────────────────────────────

def menu_agents(agent_type="ecommerce"):
    """Menu for agent discovery and execution"""
    from cli.utils import discover_agents, get_agent_registry
    
    agents_dict = discover_agents()
    # Convert dict values to list
    agents = list(agents_dict.values())
    filtered = [a for a in agents if (agent_type == "all") or (a.get("domain") == agent_type)]
    
    while True:
        console.print(f"\n[bold white]━━━━━━━━━━━━━━━━━━ {agent_type.upper()} AGENTS ━━━━━━━━━━━━━━━━━━[/bold white]")
        for i, agent in enumerate(filtered[:20], 1):
            console.print(f"  [{i:2d}] {agent['name']:20s} - {agent.get('domain', 'unknown')}")
        console.print(f"\n  [dim]0  Back[/dim]")
        
        choice = input("\nSelect agent [0-20]: ").strip()
        if choice == "0":
            break
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(filtered):
                run_agent(filtered[idx]["name"])
        except (ValueError, IndexError):
            console.print("[red]Invalid choice[/red]")


def menu_skills():
    """Menu for skill management"""
    from cli.utils import discover_skills
    
    while True:
        console.print("\n[bold white]━━━━━━━━━━━━━━━━━━━━━ SKILLS ━━━━━━━━━━━━━━━━━━━━[/bold white]")
        console.print("  [1] List all skills")
        console.print("  [2] Add new skill")
        console.print("  [3] Validate skill JSON")
        console.print("  [4] Describe skill")
        console.print("  [0] Back")
        
        choice = input("\nSelect [0-4]: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            from cli.commands.skill import list_skills
            list_skills()
        elif choice == "2":
            path = input("Path to skill JSON: ").strip()
            if path:
                from cli.commands.skill import add_skill
                add_skill(path)
        elif choice == "3":
            path = input("Path to skill JSON: ").strip()
            if path:
                from cli.commands.skill import validate_skill
                validate_skill(path)
        elif choice == "4":
            name = input("Skill name: ").strip()
            if name:
                from cli.commands.skill import describe_skill
                describe_skill(name)
        else:
            console.print("[red]Invalid choice[/red]")


def menu_knowledge_base():
    """Menu for RAG knowledge base"""
    while True:
        console.print("\n[bold white]━━━━━━━━━━━━━━━━ KNOWLEDGE BASE (RAG) ━━━━━━━━━━━━━━━[/bold white]")
        console.print("  [1] Query knowledge base")
        console.print("  [2] Add document")
        console.print("  [3] List documents")
        console.print("  [4] RAG status")
        console.print("  [5] Index statistics")
        console.print("  [6] Clear cache")
        console.print("  [7] Reindex all")
        console.print("  [0] Back")
        
        choice = input("\nSelect [0-7]: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            question = input("Question: ").strip()
            if question:
                from cli.commands.rag import query_knowledge
                query_knowledge(question)
        elif choice == "2":
            path = input("Document path: ").strip()
            if path:
                from cli.commands.rag import add_document
                add_document(path)
        elif choice == "3":
            from cli.commands.rag import list_documents
            list_documents()
        elif choice == "4":
            from cli.commands.rag import rag_status
            rag_status()
        elif choice == "5":
            from cli.commands.rag import index_stats
            index_stats()
        elif choice == "6":
            from cli.commands.rag import clear_cache
            clear_cache()
        elif choice == "7":
            confirm = input("Reindex all documents? (y/n): ").strip()
            if confirm.lower() == "y":
                from cli.commands.rag import reindex_knowledge
                reindex_knowledge()
        else:
            console.print("[red]Invalid choice[/red]")


def menu_agents_management():
    """Menu for agent discovery and management"""
    from cli.utils import discover_agents
    
    while True:
        console.print("\n[bold white]━━━━━━━━━━━━━━━━ AGENTS MANAGEMENT ━━━━━━━━━━━━━━[/bold white]")
        console.print("  [1] E-Commerce Agents")
        console.print("  [2] External Agents")
        console.print("  [3] Worker Agents")
        console.print("  [4] All Agents")
        console.print("  [5] Create new agent")
        console.print("  [0] Back")
        
        choice = input("\nSelect [0-5]: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            menu_agents("ecommerce")
        elif choice == "2":
            menu_agents("external")
        elif choice == "3":
            menu_agents("worker")
        elif choice == "4":
            menu_agents("all")
        elif choice == "5":
            name = input("New agent name: ").strip()
            agent_type = input("Type (worker/helper) [worker]: ").strip() or "worker"
            if name:
                from cli.commands.agent import create_agent
                create_agent(name, agent_type)
        else:
            console.print("[red]Invalid choice[/red]")


def menu_swarms():
    """Menu for multi-agent swarms"""
    while True:
        console.print("\n[bold white]━━━━━━━━━━━━━━━━━━━ SWARMS (Multi-Agent) ━━━━━━━━━━━━━━━━━[/bold white]")
        console.print("  [1] Full Launch Swarm    - ALL agents (complete product launch)")
        console.print("  [2] Product Research     - SEO + Product + Store")
        console.print("  [3] Marketing Campaign   - Ads + Social + Banners")
        console.print("  [4] SEO Deep Dive        - Full SEO audit")
        console.print("  [0] Back")
        
        choice = input("\nSelect [0-4]: ").strip()
        
        swarm_map = {"1": "full", "2": "product", "3": "marketing", "4": "seo"}
        
        if choice == "0":
            break
        elif choice in swarm_map:
            run_swarm(swarm_map[choice])
        else:
            console.print("[red]Invalid choice[/red]")


def main_menu():
    """Main hierarchical menu"""
    bootstrap_browser_runtime()
    console.print(BANNER)

    # Check store config
    store_url = os.getenv("STORE_URL", "not set")
    niche = os.getenv("STORE_NICHE", "not set")
    
    use_local = os.getenv("USE_LOCAL_LLM", "").lower() in ["true", "1", "yes"]
    if use_local:
        model = os.getenv("LOCAL_MODEL_NAME", "liquid/lfm2.5-1.2b") + " (Local)"
    else:
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

    config_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    config_table.add_column("", style="dim")
    config_table.add_column("")
    config_table.add_row("Store", store_url)
    config_table.add_row("Niche", niche)
    config_table.add_row("Model", model)
    config_table.add_row("Browser", describe_browser_status())
    config_table.add_row("Outputs", "./outputs/")
    console.print(config_table)

    while True:
        console.print("\n[bold white]━━━━━━━━━━━━━━━━━━━━━ MAIN MENU ━━━━━━━━━━━━━━━━━━━━[/bold white]")
        console.print("[bold]ORCHESTRATION[/bold]")
        console.print("  [cyan]1[/cyan]  Multi-Agent Swarms")
        console.print("  [cyan]2[/cyan]  Supreme Orchestrator (APEX)")
        
        console.print("\n[bold]AGENTS[/bold]")
        console.print("  [green]3[/green]  Agent Management & Discovery")
        
        console.print("\n[bold]SKILLS & KNOWLEDGE[/bold]")
        console.print("  [yellow]4[/yellow] Skill Management")
        console.print("  [yellow]5[/yellow] Knowledge Base (RAG)")
        
        console.print("\n[bold]LEGACY[/bold]")
        console.print("  [magenta]6[/magenta] Run specific agent (legacy)")
        
        console.print("\n  [dim]0  Exit[/dim]")
        console.print("[bold white]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold white]")

        choice = input("\nSelect [0-6]: ").strip()

        if choice == "0":
            console.print("[dim]Goodbye.[/dim]")
            break
        elif choice == "1":
            menu_swarms()
        elif choice == "2":
            run_supreme_orchestrator()
        elif choice == "3":
            menu_agents_management()
        elif choice == "4":
            menu_skills()
        elif choice == "5":
            menu_knowledge_base()
        elif choice == "6":
            agent_name = input("Agent name: ").strip()
            if agent_name:
                run_agent(agent_name)
        else:
            console.print("[red]Invalid choice[/red]")


def interactive_menu():
    """Wrapper for backward compatibility"""
    main_menu()


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ECOM SWARM — AI Agent System")
    parser.add_argument("--agent", type=str, help="Run a specific agent: seo|product|ads|social|banner|store|browser|research|email|stocks|support|social-ai|tests|competitive|debate")
    parser.add_argument("--swarm", type=str, help="Run a swarm: product|marketing|seo|full")
    parser.add_argument("--orchestrator", action="store_true", help="Run the Supreme Orchestrator")
    args = parser.parse_args()

    try:
        check_config()
        bootstrap_browser_runtime()

        if args.agent:
            run_agent(args.agent)
        elif args.swarm:
            run_swarm(args.swarm)
        elif args.orchestrator:
            run_supreme_orchestrator()
        else:
            interactive_menu()
    finally:
        cleanup_browser_runtime()
