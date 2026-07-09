"""
swarms/outreach_swarm.py
========================
OUTREACH SWARM ORCHESTRATION PIPELINE
Ties together all the specialized agents (Orchestrator, Research, Strategy, Outreach, 
Analysis, Memory, FollowUp, Watcher) to run automated, multi-platform outreach campaigns.

This pipeline can run in two modes:
1. Active Outbound Campaign: Resolves prospect info, plans strategy, drafts and sends initial message.
2. Event-Driven Wakeup Campaign: Wakes up when the Notification Watcher intercepts a message, 
   runs sentiment analysis, saves history to memory, and drafts the conversational reply.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.outreach.orchestrator_agent import OrchestratorAgent, SwarmState
from agents.outreach.research_agent import ResearchAgent
from agents.outreach.strategy_agent import StrategyAgent
from agents.outreach.outreach_agent import OutreachAgent
from agents.outreach.analysis_agent import AnalysisAgent
from agents.outreach.memory_agent import MemoryAgent
from agents.outreach.follow_up_agent import FollowUpAgent
from agents.outreach.notification_watcher import NotificationWatcher

from swarms.swarm_engine import SwarmResult, run_agent_step, print_swarm_header, print_swarm_summary
from tools.output_manager import save_output
from rich.console import Console
from rich.panel import Panel

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OutreachSwarmPipeline")

def run_outreach_swarm(prospect_name: str, prospect_company: str, target_industry: str = "General Tech") -> SwarmResult:
    """
    Runs the multi-agent AI Outreach Swarm pipeline for a given prospect.
    """
    print_swarm_header(
        "AI OUTREACH SWARM",
        "Automated multi-platform outreach and conversational lead nurture pipeline.",
        ["Orchestrator", "Research", "Strategy", "Outreach", "Watcher", "Analysis", "Memory", "FollowUp"]
    )
    
    swarm = SwarmResult("Outreach Swarm")
    
    # Initialize agents
    orchestrator = OrchestratorAgent()
    research = ResearchAgent()
    strategy = StrategyAgent()
    outreach = OutreachAgent()
    analysis = AnalysisAgent()
    memory = MemoryAgent()
    follow_up = FollowUpAgent()
    watcher = NotificationWatcher(orchestrator=orchestrator)
    
    contact_id = f"{prospect_name}_{prospect_company}".replace(" ", "_").lower()
    
    # Load initial state
    state = SwarmState(
        contact_id=contact_id,
        current_agent="",
        status="PENDING",
        history=[],
        metadata={"target_industry": target_industry}
    )
    
    # --- PHASE 1: RESEARCH & STRATEGY & INITIAL OUTREACH ---
    console.print("\n[bold cyan]━━ PHASE 1: Initial Outbound Pipeline ━━[/bold cyan]")
    
    # Step 1: Research
    state.current_agent = "ResearchAgent"
    prospect_profile = run_agent_step(
        "RESEARCH: Gather Prospect Insights",
        research.gather_info,
        swarm,
        prospect_name,
        prospect_company,
        target_industry
    )
    if not prospect_profile:
        logger.error("Research Phase failed. Aborting pipeline.")
        swarm.add_error("ResearchAgent", "Failed to compile profile.")
        return swarm
        
    memory.store(contact_id, {"profile": prospect_profile})
    state.history.append({"agent": "ResearchAgent", "event": "Profile compiled."})
    
    # Step 2: Strategy
    state.current_agent = "StrategyAgent"
    campaign_strategy = run_agent_step(
        "STRATEGY: Develop Outreach Blueprint",
        strategy.develop_strategy,
        swarm,
        prospect_profile
    )
    if not campaign_strategy:
        logger.error("Strategy Phase failed. Aborting pipeline.")
        swarm.add_error("StrategyAgent", "Failed to compile strategy.")
        return swarm
        
    memory.store(contact_id, {"strategy": campaign_strategy})
    state.history.append({"agent": "StrategyAgent", "event": "Strategy compiled."})
    
    # Step 3: Outreach Draft
    state.current_agent = "OutreachAgent"
    platform = campaign_strategy.get("primary_platform", "Email")
    message_draft = run_agent_step(
        f"OUTREACH: Draft Initial {platform} Copy",
        outreach.draft_message,
        swarm,
        campaign_strategy,
        prospect_profile,
        step="initial"
    )
    if not message_draft:
        logger.error("Outreach drafting failed. Aborting pipeline.")
        swarm.add_error("OutreachAgent", "Failed to compile outreach message.")
        return swarm
        
    memory.store(contact_id, {"sent_message": message_draft})
    state.history.append({"agent": "OutreachAgent", "event": "Initial message sent."})
    state.status = "WAITING_FOR_REPLY"
    
    console.print(Panel(
        f"[green]Initial Message Prepared successfully for {platform} delivery.[/green]\n\n"
        f"[bold]DRAFT MESSAGE:[/bold]\n{message_draft}",
        title="Outbound Success"
    ))
    
    # --- PHASE 2: EVENT-DRIVEN RESPONSE SIMULATION ---
    console.print("\n[bold yellow]━━ PHASE 2: Event-Driven Reply (Simulated Webhook) ━━[/bold yellow]")
    
    mock_inbox_payload = {
        "platform": platform,
        "contact_id": contact_id,
        "message": "Hey! This sounds useful. What is the pricing structure for team tiers?",
        "timestamp": 123456789.0
    }
    
    console.print(f"[dim]Simulating webhook event landing on {platform} inbox...[/dim]")
    
    # Webhook triggers Watcher -> Orchestrator -> AnalysisAgent
    watcher_event_desc = watcher.receive_webhook(mock_inbox_payload)
    state.current_agent = "AnalysisAgent"
    
    # Step 4: Reply Analysis
    analysis_results = run_agent_step(
        "ANALYSIS: Parse Sentiment & Intent",
        analysis.analyze_message,
        swarm,
        mock_inbox_payload["message"]
    )
    if not analysis_results:
        logger.warning("Reply analysis failed. Using fallback response routing.")
        analysis_results = {
            "Emotion": "Neutral",
            "Interest_Level": "Medium",
            "Intent": "Asking questions",
            "Objections": "None",
            "Urgency": "Unknown",
            "Recommended_Next_Action": "Reply immediately"
        }
        
    memory.store(contact_id, {"latest_analysis": analysis_results, "new_message": mock_inbox_payload["message"]})
    state.metadata["latest_analysis"] = analysis_results
    state.history.append({"agent": "AnalysisAgent", "event": "Reply parsed."})
    
    # Step 5: Memory summarization & Context compilation
    state.current_agent = "MemoryAgent"
    context_summary = run_agent_step(
        "MEMORY: Compile Timeline & Context Summary",
        memory.summarize_context,
        swarm,
        contact_id
    )
    state.history.append({"agent": "MemoryAgent", "event": "Context compiled."})
    
    # Step 6: Draft Contextual Reply
    state.current_agent = "OutreachAgent"
    reply_draft = run_agent_step(
        "OUTREACH: Draft Tailored Reply Message",
        outreach.draft_message,
        swarm,
        campaign_strategy,
        prospect_profile,
        context_summary,
        step="reply"
    )
    if reply_draft:
        memory.store(contact_id, {"sent_message": reply_draft})
        state.history.append({"agent": "OutreachAgent", "event": "Reply drafted."})
        
    console.print(Panel(
        f"[green]Structured reply compiled for {platform} delivery.[/green]\n\n"
        f"[bold]REPLY COPY:[/bold]\n{reply_draft}",
        title="Reply Success"
    ))
    
    save_output("swarms", f"outreach_swarm_{contact_id}", swarm.summary(), "json")
    print_swarm_summary(swarm)
    return swarm

if __name__ == "__main__":
    name = input("Prospect Name: ").strip() or "Alice Johnson"
    company = input("Prospect Company: ").strip() or "InnovateCorp"
    run_outreach_swarm(name, company)
