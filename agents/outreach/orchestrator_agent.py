"""
agents/outreach/orchestrator_agent.py
======================================
OUTREACH SWARM ORCHESTRATOR (domain coordinator)
=================================================
Note: This is NOT the Supreme Orchestrator (agents/managers/orchestrator_agent.py).
This agent coordinates work WITHIN the Outreach Swarm domain.
It is registered in the universal registry as "outreach_orchestrator" so the
Supreme Orchestrator can dispatch outreach goals directly to it.

Responsibilities:
- Parse incoming triggers (new leads, incoming platform notifications).
- Track swarm state and history.
- Coordinate execution of:
  * OutreachClassifierAgent (Goal Classification) - NEW
  * ResearchAgent (Data Gathering + ICP Matching)
  * StrategyAgent (Approach Planning)
  * OutreachAgent (Drafting Content)
  * AnalysisAgent (Categorizing replies)
  * MemoryAgent (History Persistence)
  * FollowUpAgent (Drip Management)
- Context threading: Pass OutreachContext to every agent call and update after each return.
- State machine with CLASSIFYING, ICP_CHECK, REJECTED states.
- Fallback gracefully when external LLM APIs fail or hit rate limits.
- Manage execution logs.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from agents.outreach.context import (
    OutreachContext,
    ICPMatchResult,
    DynamicStrategy,
    VALID_CAMPAIGN_STAGES,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SwarmOrchestrator")

@dataclass
class SwarmState:
    contact_id: str
    current_agent: str
    status: str  # PENDING, IN_PROGRESS, COMPLETED, FAILED, WAITING_FOR_REPLY, REJECTED
    history: List[Dict[str, Any]]
    metadata: Dict[str, Any]  # Stores OutreachContext at metadata["outreach_context"]
    retry_count: int = 0

    def get_outreach_context(self) -> Optional[OutreachContext]:
        """Retrieve OutreachContext from metadata if present."""
        ctx_data = self.metadata.get("outreach_context")
        if ctx_data is None:
            return None
        if isinstance(ctx_data, OutreachContext):
            return ctx_data
        if isinstance(ctx_data, dict):
            return OutreachContext.from_dict(ctx_data)
        return None

    def set_outreach_context(self, context: OutreachContext) -> None:
        """Store OutreachContext in metadata."""
        self.metadata["outreach_context"] = context

ORCHESTRATOR_SYSTEM_PROMPT = """
You are the Orchestrator Agent for a production-grade AI Outreach Swarm.
Your job is to determine the next agent that should execute in the workflow based on the current state, history, and incoming events.

Specialized Swarm Agents:
1. OutreachClassifierAgent: Classifies raw outreach goals into structured OutreachContext (NEW - entry point).
2. ResearchAgent: Gathers prospect info (company size, pain points, website details, social profiles) and scores ICP match.
3. StrategyAgent: Forms a campaign strategy using LLM reasoning, chooses platform (email/SMS/LinkedIn/WhatsApp), and sets goals.
4. OutreachAgent: Drafts the personalized message or reply.
5. AnalysisAgent: Parses incoming prospect messages into structured JSON (Emotion, Intent, Objection, Urgency).
6. MemoryAgent: Persists OutreachContext and builds context timelines.
7. FollowUpAgent: Calculates dynamic drip schedules and drafts follow-ups if there is no response.
8. NotificationWatcher: Listens for events to wake up the Orchestrator.

State Machine:
- CLASSIFYING: Invoke OutreachClassifierAgent to classify raw goal into OutreachContext.
- RESEARCHING: Invoke ResearchAgent to gather prospect profile and ICP score.
- ICP_CHECK: Evaluate ICP score threshold; transition to REJECTED if score < min_icp_score.
- STRATEGIZING: Invoke StrategyAgent to generate DynamicStrategy.
- OUTREACHING: Invoke OutreachAgent to draft/send messages.
- WAITING: Sleep and monitor for replies.
- ANALYZING: Invoke AnalysisAgent to categorize replies.
- COMPLETED: Terminal state.
- REJECTED: Terminal state for contacts that don't meet ICP threshold.

Transition Rules:
- If a new lead/goal is detected: Route to OutreachClassifierAgent (CLASSIFYING state).
- After OutreachClassifierAgent completes: Transition to RESEARCHING and route to ResearchAgent.
- After ResearchAgent completes: Transition to ICP_CHECK state; evaluate ICP score.
- If ICP score < min_icp_score: Transition to REJECTED terminal state.
- If ICP check passes: Transition to STRATEGIZING and route to StrategyAgent.
- After StrategyAgent completes: Route to OutreachAgent.
- After OutreachAgent drafts/sends: Transition to WAITING_FOR_REPLY and put the system to sleep.
- If Watcher detects a response: Route response to AnalysisAgent.
- After AnalysisAgent completes: Route to MemoryAgent (to store data) then to OutreachAgent (to reply).
- If no reply within target days (drip trigger): Route to FollowUpAgent.
- If FollowUpAgent completes drafting: Route to OutreachAgent (to send).
- If prospect rejects/opts-out: Route to MemoryAgent (to mark opted-out) and set state to COMPLETED.
- ALWAYS check opted_out flag before invoking any message-drafting agent.
- In BULK_CAMPAIGN mode: Skip rejected contacts and continue with next prospect.

Context Threading:
- OutreachContext is stored at SwarmState.metadata["outreach_context"].
- Pass OutreachContext to every agent call.
- Update SwarmState.metadata["outreach_context"] after each agent returns.
- Invoke MemoryAgent to persist OutreachContext at each state transition.

Input Format:
Current State JSON: { "contact_id": "...", "current_agent": "...", "status": "...", "history": [...], "metadata": {...} }
Last Event: "..."

Output Format:
You must output a JSON object containing:
- "next_agent": The name of the next agent.
- "action": What needs to be done.
- "rationale": Clear thinking explaining the transition.
"""

class OrchestratorAgent:
    """
    Outreach Swarm internal coordinator.
    Registered in the universal registry as 'outreach_orchestrator'.
    
    Context Threading:
    - Stores OutreachContext at SwarmState.metadata["outreach_context"]
    - Passes OutreachContext to every agent call
    - Updates context after each agent return
    - Persists context via MemoryAgent at each state transition
    """

    name = "outreach_orchestrator"
    role = "domain"
    description = (
        "Top-level coordinator for the AI Outreach Swarm. Manages state transitions "
        "between Classifier, Research, Strategy, Outreach, Analysis, Memory, and FollowUp agents. "
        "Implements context threading with OutreachContext. "
        "Supports CLASSIFYING, ICP_CHECK, and REJECTED states. "
        "Can be dispatched by the Supreme Orchestrator via swarm_domain='outreach'. "
        "Best for: running end-to-end outreach campaigns for a named prospect."
    )

    def __init__(self, client=None, max_retries: int = 3, backoff_factor: float = 2.0, verbose: bool = False):
        """
        Initializes the Orchestrator Agent with optional Gemini client and retry settings.
        """
        self.verbose = verbose
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.client = client or self._init_client()
        self._memory_agent = None  # Lazy-loaded MemoryAgent instance
        
    def _init_client(self):
        try:
            return make_client(
                ORCHESTRATOR_SYSTEM_PROMPT,
                "OUTREACH-Orchestrator",
                api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            logger.warning(f"Failed to initialize live Gemini client: {e}. Falling back to RuleEngine.")
            return None

    def execute_with_retry(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Executes a call with exponential backoff retry logic.
        """
        retries = 0
        wait_time = 1.0
        while retries <= self.max_retries:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Max retries reached. Execution failed: {e}")
                    raise e
                logger.warning(f"Execution failed: {e}. Retrying in {wait_time}s... (Attempt {retries}/{self.max_retries})")
                time.sleep(wait_time)
                wait_time *= self.backoff_factor

    def decide_next_step(self, state: SwarmState, last_event: str) -> Dict[str, Any]:
        """
        Queries the LLM or falls back to standard routing logic to retrieve the next agent transition.
        """
        if self.client:
            try:
                return self.execute_with_retry(self._query_llm, state, last_event)
            except Exception as e:
                logger.error(f"LLM decision failed, falling back to rule-based logic: {e}")
                return self._rule_based_fallback(state, last_event)
        else:
            return self._rule_based_fallback(state, last_event)

    def _query_llm(self, state: SwarmState, last_event: str) -> Dict[str, Any]:
        prompt = (
            f"Current State JSON: {json.dumps(asdict(state))}\n"
            f"Last Event: \"{last_event}\"\n"
            "Return next step JSON:"
        )
        
        if hasattr(self.client, 'generate_content'):
            response = self.client.generate_content(prompt)
            text = response.text
        elif hasattr(self.client, 'invoke'):
            response = self.client.invoke(prompt)
            text = getattr(response, 'content', str(response))
        else:
            raise ValueError("Unsupported client interface.")

        # Clean JSON blocks if LLM wraps output in markdown codeblocks
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)

    def _rule_based_fallback(self, state: SwarmState, last_event: str) -> Dict[str, Any]:
        """
        Determines the next state transitions using hardcoded rule heuristic mapping.
        """
        logger.info(f"Using rule-based fallback decision engine for event: '{last_event}'")
        event_lower = last_event.lower()

        if "new lead" in event_lower or not state.current_agent:
            return {
                "next_agent": "ResearchAgent",
                "action": "Research prospect details using web scraping and browser search.",
                "rationale": "New lead requires research profiling before any strategy can be determined."
            }

        if state.current_agent == "ResearchAgent":
            return {
                "next_agent": "StrategyAgent",
                "action": "Analyze research profile to craft targeted strategy.",
                "rationale": "Research completed. Ready to design outreach approach."
            }

        if state.current_agent == "StrategyAgent":
            return {
                "next_agent": "OutreachAgent",
                "action": "Draft initial outreach message using strategy.",
                "rationale": "Strategy completed. Ready to author the message."
            }

        if state.current_agent == "OutreachAgent":
            return {
                "next_agent": "NotificationWatcher",
                "action": "Transition to sleep mode and monitor for prospect replies.",
                "rationale": "Initial message sent. Swarm will sleep until prospect interacts."
            }

        if "reply received" in event_lower or "message from" in event_lower:
            return {
                "next_agent": "AnalysisAgent",
                "action": "Parse and structure the incoming message content.",
                "rationale": "Prospect reply needs sentiment and intent extraction."
            }

        if state.current_agent == "AnalysisAgent":
            return {
                "next_agent": "MemoryAgent",
                "action": "Save analyzed prospect sentiment/objections/intent.",
                "rationale": "Analysis complete. Context must be persisted to memory."
            }

        if state.current_agent == "MemoryAgent":
            # If the last analysis indicated rejection/stop, mark completed
            # Otherwise reply using OutreachAgent
            last_analysis = state.metadata.get("latest_analysis", {})
            intent = last_analysis.get("Intent", "").lower()
            if "reject" in intent or "stop" in intent:
                return {
                    "next_agent": "None",
                    "action": "Mark outreach completed - Opted Out.",
                    "rationale": "Prospect requested to stop outreach. Ending campaign."
                }
            return {
                "next_agent": "OutreachAgent",
                "action": "Draft reply addressing objections/intent.",
                "rationale": "Memory updated. Outreach agent will reply with context."
            }

        if "no reply" in event_lower or "drip trigger" in event_lower or state.current_agent == "FollowUpAgent":
            if state.current_agent == "FollowUpAgent":
                return {
                    "next_agent": "OutreachAgent",
                    "action": "Deliver follow-up message.",
                    "rationale": "Follow-up message drafted. Ready to send."
                }
            return {
                "next_agent": "FollowUpAgent",
                "action": "Evaluate drip timeline and draft follow-up copy.",
                "rationale": "Prospect has not replied within target timeframe."
            }

        return {
            "next_agent": "None",
            "action": "Terminate workflow due to unhandled event.",
            "rationale": f"Unhandled event transition: State={state.current_agent}, Event={last_event}"
        }

# --- CLI / Mock Interactive execution interface ---
def run_interactive_simulation():
    """
    Runs a CLI simulation testing Orchestrator transition logic.
    """
    print("=" * 60)
    print("AI Outreach Swarm - Orchestrator Simulation Interface")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent()
    state = SwarmState(
        contact_id="test_lead_01",
        current_agent="",
        status="PENDING",
        history=[],
        metadata={}
    )
    
    events = [
        "New Lead Found: Alice Johnson, CTO of InnovateCorp",
        "ResearchAgent finished profiling Alice Johnson",
        "StrategyAgent created outbound playbook",
        "OutreachAgent sent message to LinkedIn",
        "NotificationWatcher: reply received 'Sounds cool. What is the pricing?'",
        "AnalysisAgent finished categorization",
        "MemoryAgent updated profile context",
        "OutreachAgent replied with Pricing structure",
        "Drip trigger: No reply received for 5 days",
        "FollowUpAgent drafted Day 7 reminder"
    ]
    
    for idx, event in enumerate(events, 1):
        print(f"\n[Event {idx}] {event}")
        decision = orchestrator.decide_next_step(state, event)
        
        print(f" -> Next Agent:  \033[92m{decision.get('next_agent')}\033[0m")
        print(f" -> Plan Action: {decision.get('action')}")
        print(f" -> Rationale:   {decision.get('rationale')}")
        
        # Advance states
        state.current_agent = decision.get("next_agent", "")
        state.status = "COMPLETED" if state.current_agent == "None" else "IN_PROGRESS"
        state.history.append({"event": event, "decision": decision})
        
        # Simulating metadata changes
        if state.current_agent == "AnalysisAgent":
            state.metadata["latest_analysis"] = {
                "Emotion": "Curious",
                "Interest Level": "High",
                "Intent": "Wants pricing",
                "Objections": "None",
                "Urgency": "Soon",
                "Recommended Next Action": "Reply immediately"
            }
        time.sleep(0.5)

if __name__ == "__main__":
    run_interactive_simulation()
