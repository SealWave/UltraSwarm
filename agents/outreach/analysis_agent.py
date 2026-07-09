"""
agents/outreach/analysis_agent.py
==================================
The Analysis Agent parses and structures incoming messages from prospects.
Instead of simple sentiment, it runs a multi-dimensional taxonomy evaluation
to extract: Emotion, Interest Level, Intent, Objections, Urgency, and Next Action.

Taxonomy Definitions:
1. Emotion:
   - Happy: Friendly greeting, positive phrases, expressions of excitement.
   - Curious: Asking questions, requesting additional information/details.
   - Neutral: Concise statement, basic acknowledgment, professional greeting.
   - Frustrated: Mild complaints, concerns about past contact, friction statements.
   - Angry: Demands to stop, capitalization, hostile words (unsubscribe immediately).
2. Interest Level:
   - None: Actively rejects, requests opt-out.
   - Low: Acknowledges but states no current interest or budget.
   - Medium: Willing to read more, requests documentation, pricing, or case studies.
   - High: Requests meeting booking, calls, demo booking, or has urgent problem.
3. Intent:
   - Wants information / pricing / demo / meeting.
   - Rejecting (stop, not interested).
   - Asking questions.
   - Requesting callback.
4. Objections:
   - Too expensive, Busy, Already using another provider, No budget, Wrong contact, Not interested, None.
5. Urgency:
   - Immediate, Soon, Future, Unknown.
6. Next Action:
   - Reply immediately, Send pricing, Send case study, Schedule meeting, Follow up later, Escalate to human, Stop outreach.
7. Campaign Stage Recommendation:
   - ADVANCE: High interest + no objections - continue with next stage
   - PAUSE: Low interest or objections - wait before continuing
   - ESCALATE_TO_HUMAN: Frustrated/Angry emotion - human intervention needed
   - STOP: Rejecting intent or opt-out - end outreach
"""

import os
import sys
import json
import re
import logging
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core import make_client
from agents.outreach.context import OutreachContext, VALID_STAGE_RECOMMENDATIONS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AnalysisAgent")

ANALYSIS_SYSTEM_PROMPT = """
You are the Lead Analysis System for the AI Outreach Swarm.
Your task is to parse incoming prospect messages and map them into a structured taxonomy.

Output schema must be JSON with keys:
- "Emotion": Happy | Curious | Neutral | Frustrated | Angry
- "Interest_Level": None | Low | Medium | High
- "Intent": Wants information | Wants pricing | Wants a demo | Wants a meeting | Rejecting | Asking questions | Requesting callback
- "Objections": Too expensive | Busy | Already using another provider | No budget | Wrong contact | Not interested | None
- "Urgency": Immediate | Soon | Future | Unknown
- "Recommended_Next_Action": Reply immediately | Send pricing | Send case study | Schedule meeting | Follow up later | Escalate to human | Stop outreach
- "Campaign_Stage_Recommendation": ADVANCE | PAUSE | ESCALATE_TO_HUMAN | STOP
- "Confidence": Float between 0.0 and 1.0

Campaign_Stage_Recommendation Rules:
- ADVANCE: High interest + no objections - continue with next campaign stage
- PAUSE: Low interest or objections present - wait before continuing
- ESCALATE_TO_HUMAN: Frustrated or Angry emotion - human intervention needed
- STOP: Rejecting intent or explicit opt-out request - end outreach immediately

Examples of Categorizations:
1. Message: "I am interested. Can you send over a demo link?"
   - Emotion: Curious
   - Interest_Level: High
   - Intent: Wants a demo
   - Objections: None
   - Urgency: Soon
   - Recommended_Next_Action: Send case study / Schedule meeting
   - Campaign_Stage_Recommendation: ADVANCE
2. Message: "Please remove me from your list. Do not email again."
   - Emotion: Angry
   - Interest_Level: None
   - Intent: Rejecting
   - Objections: Not interested
   - Urgency: Immediate
   - Recommended_Next_Action: Stop outreach
   - Campaign_Stage_Recommendation: STOP

Ensure your response is valid JSON only. Do not add markdown or descriptive text.
"""

# Type-specific positive signal patterns per outreach type
TYPE_SPECIFIC_SIGNALS = {
    "INVESTOR": {
        "high_positive": ["send deck", "pitch deck", "deck", "investment thesis", "portfolio fit", "fund details", "traction metrics", "metrics deck"],
        "medium_positive": ["call scheduled", "intro call", "meeting", "learn more", "interested in hearing"],
    },
    "RECRUITMENT": {
        "high_positive": ["open to opportunities", "interested in hearing more", "looking for new role", "exploring options", "ready for next step", "open to discussing"],
        "medium_positive": ["tell me more", "what's the role", "job details", "position sounds", "team size"],
    },
    "PARTNERSHIP": {
        "high_positive": ["partnership", "collaborate", "let's partner", "joint opportunity", "co-create", "integration", "mutual benefit"],
        "medium_positive": ["interested in exploring", "tell me more", "how would this work", "synergy"],
    },
    "EVENT_PROMO": {
        "high_positive": ["attend", "register", "rsvp", "count me in", "sign me up", "i'll be there", "booking"],
        "medium_positive": ["interested", "looks good", "might attend", "considering"],
    },
    "LEAD_GEN": {
        "high_positive": ["demo", "meeting", "call", "purchase", "buy", "subscribe", "sign up", "contract"],
        "medium_positive": ["pricing", "case study", "more info", "brochure", "details"],
    },
    "PR_MEDIA": {
        "high_positive": ["interview", "feature", "article", "coverage", "quote", "exclusive", "story"],
        "medium_positive": ["interested", "tell me more", "send info", "pitch"],
    },
    "CUSTOMER_SUCCESS": {
        "high_positive": ["renew", "upgrade", "expand", "onboard", "training", "success plan"],
        "medium_positive": ["how to", "help", "support", "resources", "best practices"],
    },
    "GENERAL": {
        "high_positive": ["yes", "interested", "meeting", "call", "demo"],
        "medium_positive": ["tell me more", "info", "details", "questions"],
    },
}

class AnalysisAgent:
    def __init__(self, client=None):
        self.client = client or self._init_client()
        
    def _init_client(self):
        try:
            return make_client(
                ANALYSIS_SYSTEM_PROMPT,
                "OUTREACH-Analysis",
                api_key=os.getenv("GOOGLE_API_KEY_4") or os.getenv("GOOGLE_API_KEY")
            )
        except Exception as e:
            logger.warning(f"Failed to initialize live Gemini client: {e}. Running in fallback state.")
            return None

    def analyze_message(self, message: str, context: Optional[OutreachContext] = None) -> Dict[str, Any]:
        """
        Processes incoming text and returns a validated classification dictionary.
        
        Args:
            message: The incoming reply message to analyze
            context: Optional OutreachContext for type-specific signal detection
            
        Returns:
            Dict with analysis fields including Campaign_Stage_Recommendation
        """
        prompt = f"Incoming Message: \"{message}\"\nParse and structure:"
        
        if self.client:
            try:
                if hasattr(self.client, 'generate_content'):
                    text = self.client.generate_content(prompt).text
                elif hasattr(self.client, 'invoke'):
                    response = self.client.invoke(prompt)
                    text = getattr(response, 'content', str(response))
                else:
                    text = ""
                
                text = text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(text)
                
                # Verify structure contains keys
                self._validate_schema(parsed)
                
                # Ensure Campaign_Stage_Recommendation is present
                if "Campaign_Stage_Recommendation" not in parsed:
                    parsed["Campaign_Stage_Recommendation"] = self._determine_stage_recommendation(parsed)
                
                # Apply type-specific signal detection if context provided
                if context:
                    parsed = self._apply_type_specific_signals(message, parsed, context)
                
                return parsed
            except Exception as e:
                logger.error(f"LLM analysis failed or returned invalid JSON: {e}. Using regex/heuristic rules.")
                
        return self._rule_based_analysis(message, context)

    def _validate_schema(self, data: Dict[str, Any]):
        required_keys = ["Emotion", "Interest_Level", "Intent", "Objections", "Urgency", "Recommended_Next_Action"]
        for key in required_keys:
            if key not in data:
                raise KeyError(f"Missing required analysis taxonomy key: '{key}'")

    def _apply_type_specific_signals(self, message: str, analysis: Dict[str, Any], context: OutreachContext) -> Dict[str, Any]:
        """
        Apply type-specific signal detection based on outreach_type.
        Enhances analysis with type-aware positive signal detection.
        
        Note: Type-specific signals do NOT override STOP or ESCALATE_TO_HUMAN recommendations.
        """
        msg_lower = message.lower()
        outreach_type = context.outreach_type
        
        # Don't boost if already STOP or ESCALATE_TO_HUMAN
        if analysis.get("Campaign_Stage_Recommendation") in ["STOP", "ESCALATE_TO_HUMAN"]:
            return analysis
        
        if outreach_type not in TYPE_SPECIFIC_SIGNALS:
            outreach_type = "GENERAL"
        
        signals = TYPE_SPECIFIC_SIGNALS[outreach_type]
        
        # Check for high-positive signals
        high_positive_found = any(signal in msg_lower for signal in signals.get("high_positive", []))
        medium_positive_found = any(signal in msg_lower for signal in signals.get("medium_positive", []))
        
        if high_positive_found:
            # Boost interest level if type-specific high-positive signal found
            if analysis["Interest_Level"] in ["Low", "Medium"]:
                analysis["Interest_Level"] = "High"
            # Set ADVANCE recommendation for high-positive signals
            if analysis.get("Campaign_Stage_Recommendation") not in ["STOP", "ESCALATE_TO_HUMAN"]:
                analysis["Campaign_Stage_Recommendation"] = "ADVANCE"
            logger.info(f"Type-specific high-positive signal detected for {outreach_type}: boosting to High interest")
        
        elif medium_positive_found:
            # Ensure at least Medium interest for type-specific medium signals
            if analysis["Interest_Level"] == "Low":
                analysis["Interest_Level"] = "Medium"
            if analysis.get("Campaign_Stage_Recommendation") == "PAUSE":
                analysis["Campaign_Stage_Recommendation"] = "ADVANCE"
            logger.info(f"Type-specific medium-positive signal detected for {outreach_type}")
        
        return analysis

    def _determine_stage_recommendation(self, analysis: Dict[str, Any]) -> str:
        """
        Determine Campaign_Stage_Recommendation based on analysis fields.
        
        Rules:
        - STOP: Rejecting intent or opt-out
        - ESCALATE_TO_HUMAN: Frustrated/Angry emotion
        - ADVANCE: High interest + no objections
        - PAUSE: Low interest or objections present
        """
        emotion = analysis.get("Emotion", "Neutral")
        interest = analysis.get("Interest_Level", "Low")
        intent = analysis.get("Intent", "")
        objections = analysis.get("Objections", "None")
        
        # STOP: Rejecting intent or explicit opt-out
        if intent == "Rejecting" or "stop" in str(intent).lower() or "unsubscribe" in str(intent).lower():
            return "STOP"
        
        # ESCALATE_TO_HUMAN: Frustrated or Angry emotion
        if emotion in ["Frustrated", "Angry"]:
            return "ESCALATE_TO_HUMAN"
        
        # ADVANCE: High interest + no objections
        if interest == "High" and objections == "None":
            return "ADVANCE"
        
        # PAUSE: Low interest or objections present
        if interest == "Low" or objections != "None":
            return "PAUSE"
        
        # Default to ADVANCE for Medium/High interest without objections
        if interest in ["Medium", "High"]:
            return "ADVANCE"
        
        return "PAUSE"

    def _rule_based_analysis(self, message: str, context: Optional[OutreachContext] = None) -> Dict[str, Any]:
        """
        Regex-based heuristic system parsing intent and emotion when LLM API is unavailable.
        
        Args:
            message: The incoming reply message to analyze
            context: Optional OutreachContext for type-specific signal detection
            
        Returns:
            Dict with analysis fields including Campaign_Stage_Recommendation
        """
        logger.info("Using rule-based analysis taxonomy fallback.")
        msg = message.lower()
        
        # Default fallback categorization
        analysis = {
            "Emotion": "Neutral",
            "Interest_Level": "Low",
            "Intent": "Asking questions",
            "Objections": "None",
            "Urgency": "Unknown",
            "Recommended_Next_Action": "Reply immediately",
            "Campaign_Stage_Recommendation": "PAUSE",
            "Confidence": 0.5
        }

        # Emotion parsing (but don't set final recommendation yet)
        if any(w in msg for w in ["great", "thanks", "happy", "awesome", "perfect"]):
            analysis["Emotion"] = "Happy"
        elif any(w in msg for w in ["what", "how", "why", "pricing", "cost", "demo"]):
            analysis["Emotion"] = "Curious"
        elif any(w in msg for w in ["stop", "remove", "do not", "unsubscribe", "don't", "no"]):
            analysis["Emotion"] = "Angry"
        elif any(w in msg for w in ["already", "busy", "later", "frustrated", "bothering"]):
            analysis["Emotion"] = "Frustrated"

        # Intent and Interest mapping (these take priority for recommendation)
        # Check for STOP conditions first (opt-out, rejection)
        if any(w in msg for w in ["unsubscribe", "remove", "stop", "don't email", "do not"]):
            analysis["Interest_Level"] = "None"
            analysis["Intent"] = "Rejecting"
            analysis["Objections"] = "Not interested"
            analysis["Urgency"] = "Immediate"
            analysis["Recommended_Next_Action"] = "Stop outreach"
            analysis["Campaign_Stage_Recommendation"] = "STOP"
            # Return early - STOP takes highest priority
            return analysis
        
        # Check for ESCALATE conditions (frustrated/angry without explicit opt-out)
        if analysis["Emotion"] in ["Frustrated", "Angry"]:
            # These emotions indicate potential issues but not explicit rejection
            analysis["Campaign_Stage_Recommendation"] = "ESCALATE_TO_HUMAN"
            # Still parse for other signals below
        
        # Continue parsing for other intents
        if any(w in msg for w in ["pricing", "cost", "price", "how much"]):
            analysis["Interest_Level"] = "Medium"
            analysis["Intent"] = "Wants pricing"
            analysis["Urgency"] = "Soon"
            analysis["Recommended_Next_Action"] = "Send pricing"
            # Only set ADVANCE if not already ESCALATE
            if analysis["Campaign_Stage_Recommendation"] not in ["ESCALATE_TO_HUMAN", "STOP"]:
                analysis["Campaign_Stage_Recommendation"] = "ADVANCE"
        elif any(w in msg for w in ["demo", "show me", "how it works", "screencast"]):
            analysis["Interest_Level"] = "High"
            analysis["Intent"] = "Wants a demo"
            analysis["Urgency"] = "Soon"
            analysis["Recommended_Next_Action"] = "Schedule meeting"
            if analysis["Campaign_Stage_Recommendation"] not in ["ESCALATE_TO_HUMAN", "STOP"]:
                analysis["Campaign_Stage_Recommendation"] = "ADVANCE"
        elif any(w in msg for w in ["calendar", "call", "meet", "schedule", "zoom"]):
            analysis["Interest_Level"] = "High"
            analysis["Intent"] = "Wants a meeting"
            analysis["Urgency"] = "Immediate"
            analysis["Recommended_Next_Action"] = "Schedule meeting"
            if analysis["Campaign_Stage_Recommendation"] not in ["ESCALATE_TO_HUMAN", "STOP"]:
                analysis["Campaign_Stage_Recommendation"] = "ADVANCE"
        elif any(w in msg for w in ["busy", "no time", "later", "next month", "q4"]):
            analysis["Interest_Level"] = "Low"
            analysis["Intent"] = "Asking questions"
            analysis["Objections"] = "Busy"
            analysis["Urgency"] = "Future"
            analysis["Recommended_Next_Action"] = "Follow up later"
            analysis["Campaign_Stage_Recommendation"] = "PAUSE"
        elif any(w in msg for w in ["expensive", "budget", "cost too high"]):
            analysis["Interest_Level"] = "Low"
            analysis["Intent"] = "Asking questions"
            analysis["Objections"] = "Too expensive"
            analysis["Urgency"] = "Future"
            analysis["Recommended_Next_Action"] = "Reply immediately"
            analysis["Campaign_Stage_Recommendation"] = "PAUSE"
        
        # Apply type-specific signals if context provided
        if context:
            analysis = self._apply_type_specific_signals(message, analysis, context)
        
        return analysis

# --- CLI / Mock Simulation execution interface ---
def run_interactive_simulation():
    print("=" * 60)
    print("AI Outreach Swarm - Analysis Agent Simulation")
    print("=" * 60)
    
    test_messages = [
        "Sounds interesting. Can you send pricing information?",
        "Please unsubscribe me and stop emailing.",
        "We are currently using HubSpot, no budget to change now.",
        "Let's book a call, here is my link.",
        "I'd love to see your pitch deck. Can you send it over?",
        "I'm open to opportunities. Tell me more about the role.",
        "This partnership sounds great. Let's collaborate!",
        "I'm frustrated with your constant emails. Stop bothering me."
    ]
    
    agent = AnalysisAgent()
    
    # Test without context
    print("\n" + "-" * 60)
    print("Testing without OutreachContext:")
    print("-" * 60)
    for idx, msg in enumerate(test_messages[:4], 1):
        print(f"\n[Test {idx}] Message: '{msg}'")
        analysis = agent.analyze_message(msg)
        print(json.dumps(analysis, indent=2))
    
    # Test with context (type-specific signals)
    print("\n" + "-" * 60)
    print("Testing with OutreachContext (type-specific signals):")
    print("-" * 60)
    
    # Create test contexts for different outreach types
    test_contexts = [
        ("INVESTOR", "I'd love to see your pitch deck. Can you send it over?"),
        ("RECRUITMENT", "I'm open to opportunities. Tell me more about the role."),
        ("PARTNERSHIP", "This partnership sounds great. Let's collaborate!"),
        ("EVENT_PROMO", "Count me in! I'll register for the event."),
    ]
    
    for idx, (outreach_type, msg) in enumerate(test_contexts, 1):
        print(f"\n[Test {idx}] Outreach Type: {outreach_type}")
        print(f"Message: '{msg}'")
        context = OutreachContext(outreach_type=outreach_type)
        analysis = agent.analyze_message(msg, context)
        print(json.dumps(analysis, indent=2))

if __name__ == "__main__":
    run_interactive_simulation()
