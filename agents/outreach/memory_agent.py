"""
agents/outreach/memory_agent.py
================================
The Memory Agent persists and organizes interaction history for prospects.
It builds historical context timelines, trims context windows, and saves data to persistent JSON files.

Workspace directory:
- Data is stored in: `agent_workspace/outreach_memory/` as contact-specific JSON records.
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from agents.outreach.context import (
    OutreachContext,
    ICPMatchResult,
    DynamicStrategy,
    VALID_OUTREACH_TYPES,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MemoryAgent")

MEMORY_SYSTEM_PROMPT = """
You are the Memory and Context Architect for the AI Outreach Swarm.
Your job is to read a prospect's history timeline and generate a concise context summary
that can be fed directly to the Outreach Agent to craft subsequent responses.

Ensure you highlight:
1. Current stage of conversation.
2. Direct questions asked by the prospect that remain unanswered.
3. Expressed pain points and objections.
4. Platforms utilized and which were successful.
5. The specific next action recommended.
"""


class ContextCorruptionError(Exception):
    """Raised when stored OutreachContext data is corrupted or missing required fields."""
    pass


class MemoryAgent:
    def __init__(self, client=None, storage_dir: str = "agent_workspace/outreach_memory"):
        self.storage_path = Path(storage_dir)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.client = client or self._init_client()
        
    def _init_client(self):
        try:
            return make_client(
                MEMORY_SYSTEM_PROMPT,
                "OUTREACH-Memory",
                api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            logger.warning(f"Failed to initialize live Gemini client: {e}. Running summary fallbacks.")
            return None

    def _get_file_path(self, contact_id: str) -> Path:
        return self.storage_path / f"{contact_id}.json"

    def _get_profile_file_path(self, contact_id: str) -> Path:
        """Get the file path for storing prospect profile separately."""
        return self.storage_path / f"{contact_id}_profile.json"

    def store(self, contact_id: str, data: Dict[str, Any], context: Optional[OutreachContext] = None):
        """
        Loads the existing file, appends or updates keys, builds timeline events, and saves back.
        
        If an OutreachContext is provided, it is serialized and stored alongside other data.
        The prospect_profile is stored as a separate file reference to keep context lightweight.
        
        Args:
            contact_id: The unique identifier for the contact
            data: Dictionary of data to store (can include 'new_message', 'sent_message', etc.)
            context: Optional OutreachContext to serialize and store
        """
        file_path = self._get_file_path(contact_id)
        current_data = {}
        
        if file_path.exists():
            try:
                current_data = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to read existing memory file {file_path}: {e}")

        # Handle OutreachContext serialization if provided
        if context is not None:
            context_dict = context.to_dict()
            
            # Extract and store prospect_profile separately if it exists
            if context.prospect_profile:
                profile_path = self._get_profile_file_path(contact_id)
                try:
                    profile_data = {
                        "prospect_profile": context.prospect_profile,
                        "contact_id": contact_id,
                        "timestamp": time.time()
                    }
                    profile_path.write_text(
                        json.dumps(profile_data, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )
                    # Store reference instead of full profile
                    context_dict["prospect_profile_ref"] = f"{contact_id}_profile.json"
                    context_dict["prospect_profile"] = None  # Clear to keep context lightweight
                except Exception as e:
                    logger.error(f"Failed to store prospect profile separately: {e}")
            
            # Store the serialized context
            current_data["outreach_context"] = context_dict

        # Update metadata keys
        for k, v in data.items():
            if k == "new_message":
                history = current_data.get("history", [])
                history.append({
                    "role": "prospect",
                    "text": v,
                    "timestamp": time.time()
                })
                current_data["history"] = history
            elif k == "sent_message":
                history = current_data.get("history", [])
                history.append({
                    "role": "agent",
                    "text": v,
                    "timestamp": time.time()
                })
                current_data["history"] = history
            else:
                current_data[k] = v

        # Build clean historical timeline
        current_data["timeline"] = self._build_timeline(current_data)
        
        # Trim history if it exceeds threshold
        current_data["history"] = self._trim_history(current_data.get("history", []))

        try:
            file_path.write_text(json.dumps(current_data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Memory successfully stored for {contact_id}.")
        except Exception as e:
            logger.error(f"Failed to write memory file {file_path}: {e}")

    def retrieve(self, contact_id: str) -> Dict[str, Any]:
        """
        Retrieves the persistent memory data dictionary for a contact.
        """
        file_path = self._get_file_path(contact_id)
        if file_path.exists():
            try:
                return json.loads(file_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to parse memory file {file_path}: {e}")
        return {}

    def retrieve_context(self, contact_id: str) -> Optional[OutreachContext]:
        """
        Retrieves and deserializes the OutreachContext for a contact.
        
        Returns:
            OutreachContext if found and valid, None otherwise.
            If the stored context is corrupted, returns a minimal reconstructed context
            and signals that re-classification is needed.
        """
        file_path = self._get_file_path(contact_id)
        
        if not file_path.exists():
            logger.info(f"No memory file found for contact {contact_id}")
            return None
        
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted JSON in memory file {file_path}: {e}")
            return self._reconstruct_minimal_context(contact_id, {})
        
        context_dict = data.get("outreach_context")
        if context_dict is None:
            logger.info(f"No OutreachContext found for contact {contact_id}")
            return None
        
        try:
            context = self._deserialize_context(contact_id, context_dict)
            
            # Load prospect_profile from separate file if reference exists
            if context and context_dict.get("prospect_profile_ref"):
                profile_path = self._get_profile_file_path(contact_id)
                if profile_path.exists():
                    try:
                        profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
                        context.prospect_profile = profile_data.get("prospect_profile")
                    except Exception as e:
                        logger.warning(f"Failed to load prospect profile for {contact_id}: {e}")
            
            return context
        except ContextCorruptionError as e:
            logger.error(f"Context corruption detected for {contact_id}: {e}")
            return self._reconstruct_minimal_context(contact_id, context_dict)
        except Exception as e:
            logger.error(f"Unexpected error deserializing context for {contact_id}: {e}")
            return self._reconstruct_minimal_context(contact_id, context_dict)

    def _deserialize_context(self, contact_id: str, context_dict: Dict[str, Any]) -> OutreachContext:
        """
        Deserialize a dictionary to an OutreachContext object.
        
        Raises:
            ContextCorruptionError: If required fields are missing or corrupted.
        """
        if not isinstance(context_dict, dict):
            raise ContextCorruptionError("Context data is not a dictionary")
        
        # Check for minimum required fields
        # If we have at least contact_id and outreach_type, we can proceed
        has_minimum_fields = "contact_id" in context_dict or "outreach_type" in context_dict
        
        if not has_minimum_fields and not context_dict:
            raise ContextCorruptionError("Context dictionary is empty")
        
        # Validate outreach_type if present
        outreach_type = context_dict.get("outreach_type", "GENERAL")
        if outreach_type not in VALID_OUTREACH_TYPES:
            logger.warning(f"Invalid outreach_type '{outreach_type}', defaulting to GENERAL")
            context_dict["outreach_type"] = "GENERAL"
        
        try:
            return OutreachContext.from_dict(context_dict)
        except Exception as e:
            raise ContextCorruptionError(f"Failed to deserialize OutreachContext: {e}")

    def _reconstruct_minimal_context(self, contact_id: str, partial_data: Dict[str, Any]) -> OutreachContext:
        """
        Reconstruct a minimal OutreachContext from partial or corrupted data.
        
        This creates a context that signals to the OrchestratorAgent that re-classification is needed.
        The reconstructed context will have:
        - contact_id if available
        - outreach_type set to GENERAL if not determinable
        - campaign_stage set to CLASSIFYING to signal re-classification needed
        """
        logger.warning(f"Reconstructing minimal context for {contact_id} from partial data")
        
        # Extract any salvageable fields
        extracted_contact_id = partial_data.get("contact_id", contact_id)
        extracted_outreach_type = partial_data.get("outreach_type", "GENERAL")
        
        # Validate outreach_type
        if extracted_outreach_type not in VALID_OUTREACH_TYPES:
            extracted_outreach_type = "GENERAL"
        
        # Create minimal context
        minimal_context = OutreachContext(
            contact_id=extracted_contact_id,
            outreach_type=extracted_outreach_type,
            campaign_stage="CLASSIFYING",  # Signal that re-classification is needed
        )
        
        # Try to preserve any other valid fields
        for field_name in ["outreach_goal", "campaign_mode", "campaign_id", "opted_out"]:
            if field_name in partial_data:
                try:
                    setattr(minimal_context, field_name, partial_data[field_name])
                except Exception:
                    pass  # Skip fields that can't be set
        
        return minimal_context

    def needs_reclassification(self, contact_id: str) -> bool:
        """
        Check if the stored context indicates that re-classification is needed.
        
        This is true when:
        - The context was reconstructed from corrupted data
        - The campaign_stage is CLASSIFYING but the context should have progressed
        """
        data = self.retrieve(contact_id)
        context_dict = data.get("outreach_context", {})
        
        # If there's no context, re-classification is needed
        if not context_dict:
            return True
        
        # Check if the context was flagged as needing re-classification
        if context_dict.get("_needs_reclassification", False):
            return True
        
        # Check if the stored campaign_stage is CLASSIFYING for an existing contact
        # (which might indicate a reconstructed context)
        if context_dict.get("campaign_stage") == "CLASSIFYING" and data.get("history"):
            return True
        
        return False

    def store_context(self, contact_id: str, context: OutreachContext):
        """
        Convenience method to store only an OutreachContext without additional data.
        
        Args:
            contact_id: The unique identifier for the contact
            context: The OutreachContext to store
        """
        self.store(contact_id, {}, context=context)

    def _build_timeline(self, data: Dict[str, Any]) -> List[str]:
        """
        Compiles structural history into a human-readable list of events.
        """
        timeline = []
        if "profile" in data:
            timeline.append("Event: Prospect profile researched & saved.")
        if "strategy" in data:
            timeline.append("Event: Campaign strategy plan generated.")
        if "outreach_context" in data:
            ctx = data["outreach_context"]
            if ctx.get("outreach_type"):
                timeline.append(f"Event: Outreach type classified as {ctx.get('outreach_type')}.")
            if ctx.get("icp_match"):
                timeline.append("Event: ICP matching completed.")
            if ctx.get("strategy"):
                timeline.append("Event: Dynamic strategy generated.")
            
        history = data.get("history", [])
        for event in history:
            role = "Prospect" if event.get("role") == "prospect" else "Agent"
            msg = event.get("text", "")
            timeline.append(f"{role}: \"{msg}\"")
            
        return timeline

    def _trim_history(self, history: List[Dict[str, Any]], max_items: int = 20) -> List[Dict[str, Any]]:
        """
        Trims the context window to prevent memory footprint blowing up.
        """
        if len(history) > max_items:
            logger.info(f"Trimming conversation history window to last {max_items} turns.")
            return history[-max_items:]
        return history

    def summarize_context(self, contact_id: str) -> str:
        """
        Generates a contextual summary using LLM or rule-based timeline builder.
        """
        data = self.retrieve(contact_id)
        if not data:
            return "No prior context available."

        timeline = data.get("timeline", [])
        
        # Include OutreachContext info in summary if available
        context_info = ""
        if "outreach_context" in data:
            ctx = data["outreach_context"]
            context_info = (
                f"\nOutreach Context:\n"
                f"- Type: {ctx.get('outreach_type', 'Unknown')}\n"
                f"- Goal: {ctx.get('outreach_goal', 'Unknown')}\n"
                f"- Stage: {ctx.get('campaign_stage', 'Unknown')}\n"
            )
        
        prompt = (
            f"Generate an operational summary for contact ID {contact_id} using this timeline:\n"
            "\n".join(timeline) + context_info + "\n\n"
            "Format the summary focusing on objections, questions, and immediate priorities."
        )

        if self.client:
            try:
                if hasattr(self.client, 'generate_content'):
                    return self.client.generate_content(prompt).text
                elif hasattr(self.client, 'invoke'):
                    response = self.client.invoke(prompt)
                    return getattr(response, 'content', str(response))
            except Exception as e:
                logger.error(f"Memory summarization failed: {e}. Using rule fallback.")
                
        return self._rule_based_summary(data)

    def _rule_based_summary(self, data: Dict[str, Any]) -> str:
        """
        Rule fallback summary generation.
        """
        logger.info("Executing rule-based memory summary fallback.")
        timeline = data.get("timeline", [])
        history = data.get("history", [])
        
        last_prospect_msg = ""
        for h in reversed(history):
            if h.get("role") == "prospect":
                last_prospect_msg = h.get("text", "")
                break

        summary = [
            "### Prospect Memory Summary",
            f"- **Timeline Events**: {len(timeline)} recorded.",
            f"- **Conversational turns**: {len(history)} messages exchanged."
        ]
        
        # Add OutreachContext info if available
        if "outreach_context" in data:
            ctx = data["outreach_context"]
            summary.append(f"- **Outreach Type**: {ctx.get('outreach_type', 'Unknown')}")
            summary.append(f"- **Campaign Stage**: {ctx.get('campaign_stage', 'Unknown')}")
            if ctx.get("opted_out"):
                summary.append("- **Opted Out**: Yes")
        
        if last_prospect_msg:
            summary.append(f"- **Last incoming statement**: \"{last_prospect_msg}\"")
            
        return "\n".join(summary)


# --- CLI / Mock Simulation execution interface ---
def run_interactive_simulation():
    print("=" * 60)
    print("AI Outreach Swarm - Memory Agent Simulation")
    print("=" * 60)
