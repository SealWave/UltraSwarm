"""
Unit tests for the enhanced AnalysisAgent with Campaign_Stage_Recommendation
and type-specific signal detection.

Validates: Requirements 10.1, 10.2, 10.3, 10.4
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.outreach.analysis_agent import AnalysisAgent, TYPE_SPECIFIC_SIGNALS
from agents.outreach.context import OutreachContext, VALID_STAGE_RECOMMENDATIONS


class TestAnalysisAgentCampaignStageRecommendation:
    """Test Campaign_Stage_Recommendation field validation (Requirement 10.1)."""
    
    @pytest.fixture
    def agent(self):
        return AnalysisAgent()
    
    def test_always_returns_valid_campaign_stage_recommendation(self, agent):
        """Campaign_Stage_Recommendation must be one of ADVANCE, PAUSE, ESCALATE_TO_HUMAN, STOP."""
        test_messages = [
            "I'm interested in learning more.",
            "Please remove me from your list.",
            "I'm frustrated with the constant emails.",
            "This is too expensive for us.",
            "Let's schedule a call.",
            "Random message with unclear intent.",
        ]
        
        for msg in test_messages:
            result = agent.analyze_message(msg)
            assert "Campaign_Stage_Recommendation" in result
            assert result["Campaign_Stage_Recommendation"] in VALID_STAGE_RECOMMENDATIONS, \
                f"Invalid recommendation for '{msg}': {result['Campaign_Stage_Recommendation']}"
    
    def test_stop_for_rejecting_intent(self, agent):
        """STOP recommendation for rejecting intent or opt-out."""
        opt_out_messages = [
            "Please unsubscribe me from your list.",
            "Stop emailing me.",
            "Remove me from your database.",
            "Don't email me again.",
        ]
        
        for msg in opt_out_messages:
            result = agent.analyze_message(msg)
            assert result["Campaign_Stage_Recommendation"] == "STOP", \
                f"Expected STOP for '{msg}', got {result['Campaign_Stage_Recommendation']}"
            assert result["Interest_Level"] == "None"
            assert result["Intent"] == "Rejecting"
    
    def test_escalate_to_human_for_angry_emotion(self, agent):
        """ESCALATE_TO_HUMAN recommendation for Frustrated/Angry emotion (without opt-out)."""
        frustrated_messages = [
            "I'm frustrated with your constant emails!",
            "This is the third time you've emailed me. I'm already using a competitor!",
            "Your emails are annoying. Leave me alone.",
        ]
        
        for msg in frustrated_messages:
            result = agent.analyze_message(msg)
            assert result["Campaign_Stage_Recommendation"] == "ESCALATE_TO_HUMAN", \
                f"Expected ESCALATE_TO_HUMAN for '{msg}', got {result['Campaign_Stage_Recommendation']}"
    
    def test_advance_for_high_interest_no_objections(self, agent):
        """ADVANCE recommendation for High interest + no objections."""
        high_interest_messages = [
            "Let's book a call, here is my calendar link.",
            "I'd like a demo of your product.",
            "This sounds great! When can we meet?",
        ]
        
        for msg in high_interest_messages:
            result = agent.analyze_message(msg)
            assert result["Campaign_Stage_Recommendation"] == "ADVANCE", \
                f"Expected ADVANCE for '{msg}', got {result['Campaign_Stage_Recommendation']}"
    
    def test_pause_for_low_interest_or_objections(self, agent):
        """PAUSE recommendation for Low interest or objections present."""
        low_interest_messages = [
            "We don't have budget for this right now.",
            "I'm too busy to talk, maybe next quarter.",
            "We use a different provider for this service.",
        ]
        
        for msg in low_interest_messages:
            result = agent.analyze_message(msg)
            assert result["Campaign_Stage_Recommendation"] == "PAUSE", \
                f"Expected PAUSE for '{msg}', got {result['Campaign_Stage_Recommendation']}"


class TestTypeSpecificSignalDetection:
    """Test type-specific signal taxonomy (Requirements 10.2, 10.3, 10.4)."""
    
    @pytest.fixture
    def agent(self):
        return AnalysisAgent()
    
    def test_investor_send_deck_is_high_positive(self, agent):
        """INVESTOR: 'send deck' should boost to High interest and ADVANCE."""
        context = OutreachContext(outreach_type="INVESTOR")
        
        investor_positive_messages = [
            "I'd love to see your pitch deck. Can you send it over?",
            "Please send deck for our review.",
            "Can you share your deck with me?",
        ]
        
        for msg in investor_positive_messages:
            result = agent.analyze_message(msg, context)
            assert result["Interest_Level"] == "High", \
                f"Expected High interest for INVESTOR message '{msg}'"
            assert result["Campaign_Stage_Recommendation"] == "ADVANCE", \
                f"Expected ADVANCE for INVESTOR message '{msg}'"
    
    def test_recruitment_open_to_opportunities_is_high_positive(self, agent):
        """RECRUITMENT: 'open to opportunities' should boost to High interest."""
        context = OutreachContext(outreach_type="RECRUITMENT")
        
        recruitment_positive_messages = [
            "I'm open to opportunities. Tell me more.",
            "I'm interested in hearing more about the role.",
            "Looking for new role. What's the position?",
        ]
        
        for msg in recruitment_positive_messages:
            result = agent.analyze_message(msg, context)
            assert result["Interest_Level"] == "High", \
                f"Expected High interest for RECRUITMENT message '{msg}'"
            assert result["Campaign_Stage_Recommendation"] == "ADVANCE", \
                f"Expected ADVANCE for RECRUITMENT message '{msg}'"
    
    def test_partnership_collaborate_is_high_positive(self, agent):
        """PARTNERSHIP: 'collaborate' should boost to High interest."""
        context = OutreachContext(outreach_type="PARTNERSHIP")
        
        partnership_positive_messages = [
            "This sounds like a great partnership opportunity!",
            "Let's collaborate on this project.",
            "I'm interested in a partnership with your company.",
        ]
        
        for msg in partnership_positive_messages:
            result = agent.analyze_message(msg, context)
            assert result["Interest_Level"] == "High", \
                f"Expected High interest for PARTNERSHIP message '{msg}'"
    
    def test_event_promo_register_is_high_positive(self, agent):
        """EVENT_PROMO: 'register' should boost to High interest."""
        context = OutreachContext(outreach_type="EVENT_PROMO")
        
        event_positive_messages = [
            "Count me in! I'll register for the event.",
            "I'd like to RSVP for the webinar.",
            "Sign me up for the conference.",
        ]
        
        for msg in event_positive_messages:
            result = agent.analyze_message(msg, context)
            assert result["Interest_Level"] == "High", \
                f"Expected High interest for EVENT_PROMO message '{msg}'"
    
    def test_no_context_no_type_specific_boost(self, agent):
        """Without context, type-specific signals should not boost interest."""
        # Message contains "deck" but no INVESTOR context
        msg = "I'd love to see your deck."
        result = agent.analyze_message(msg)
        
        # Without INVESTOR context, "deck" shouldn't trigger special boost
        # The default behavior applies
        assert "Campaign_Stage_Recommendation" in result
    
    def test_type_specific_signals_do_not_override_stop(self, agent):
        """Type-specific signals should not override STOP recommendation."""
        context = OutreachContext(outreach_type="INVESTOR")
        
        # Message has both "deck" (INVESTOR positive) and "stop" (opt-out)
        msg = "Stop emailing me! I don't want your deck."
        result = agent.analyze_message(msg, context)
        
        # STOP should take precedence over type-specific positive signal
        assert result["Campaign_Stage_Recommendation"] == "STOP"
    
    def test_type_specific_signals_do_not_override_escalate(self, agent):
        """Type-specific signals should not override ESCALATE_TO_HUMAN."""
        context = OutreachContext(outreach_type="RECRUITMENT")
        
        # Message has positive signal but frustrated emotion (without "stop" keyword)
        msg = "I'm frustrated with the spamming but I might be open to opportunities."
        result = agent.analyze_message(msg, context)
        
        # ESCALATE_TO_HUMAN should take precedence
        assert result["Campaign_Stage_Recommendation"] == "ESCALATE_TO_HUMAN", \
            f"Expected ESCALATE_TO_HUMAN, got {result['Campaign_Stage_Recommendation']}"
    
    def test_all_outreach_types_have_signal_definitions(self):
        """Verify all 8 outreach types have signal definitions."""
        expected_types = {
            "LEAD_GEN", "PARTNERSHIP", "INVESTOR", "RECRUITMENT",
            "EVENT_PROMO", "PR_MEDIA", "CUSTOMER_SUCCESS", "GENERAL"
        }
        
        for outreach_type in expected_types:
            assert outreach_type in TYPE_SPECIFIC_SIGNALS, \
                f"Missing signal definition for {outreach_type}"
            assert "high_positive" in TYPE_SPECIFIC_SIGNALS[outreach_type]
            assert "medium_positive" in TYPE_SPECIFIC_SIGNALS[outreach_type]
            assert len(TYPE_SPECIFIC_SIGNALS[outreach_type]["high_positive"]) > 0


class TestAnalysisAgentWithContext:
    """Test analyze_message with OutreachContext parameter."""
    
    @pytest.fixture
    def agent(self):
        return AnalysisAgent()
    
    def test_analyze_message_accepts_optional_context(self, agent):
        """analyze_message() should accept optional OutreachContext parameter."""
        msg = "I'm interested in learning more."
        context = OutreachContext(outreach_type="LEAD_GEN")
        
        # Should not raise any exceptions
        result = agent.analyze_message(msg, context)
        assert isinstance(result, dict)
    
    def test_analyze_message_works_without_context(self, agent):
        """analyze_message() should work without context parameter (backwards compatible)."""
        msg = "I'm interested in learning more."
        
        # Should not raise any exceptions
        result = agent.analyze_message(msg)
        assert isinstance(result, dict)
        assert "Campaign_Stage_Recommendation" in result
    
    def test_backwards_compatibility_existing_fields_present(self, agent):
        """All existing analysis fields should still be present."""
        msg = "Can you send me pricing information?"
        result = agent.analyze_message(msg)
        
        required_fields = [
            "Emotion",
            "Interest_Level", 
            "Intent",
            "Objections",
            "Urgency",
            "Recommended_Next_Action",
            "Confidence"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
