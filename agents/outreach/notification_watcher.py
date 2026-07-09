"""
agents/outreach/notification_watcher.py
========================================
The Notification Watcher is the only continuously running daemon in the swarm.
It polls platforms or acts as an HTTP server wrapper to process incoming webhooks,
parsing triggers to wake the Orchestrator.

Supported Platform Integrations (Simulated/Configured):
- IMAP/SMTP (Email check)
- Twilio Webhooks (WhatsApp/SMS incoming)
- LinkedIn Message Webhooks (or mock scrapers)
- Facebook / Instagram Messaging APIs
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NotificationWatcher")

class NotificationWatcher:
    def __init__(self, orchestrator=None, poll_interval: float = 2.0):
        """
        Initializes the Notification Watcher daemon.
        """
        self.orchestrator = orchestrator
        self.poll_interval = poll_interval
        self._running = False
        
    def start_listening(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Starts the event polling loop. In production, this would open sockets/listeners.
        """
        self._running = True
        logger.info("Notification Watcher daemon activated. Monitoring inbox webhooks...")
        
        try:
            while self._running:
                # Simulate monitoring loop
                event = self._check_external_channels()
                if event:
                    logger.info(f"Incoming event captured: {event.get('platform')} | From: {event.get('contact_id')}")
                    if callback:
                        callback(event)
                    elif self.orchestrator:
                        self._trigger_orchestration(event)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            self.stop_listening()

    def stop_listening(self):
        self._running = False
        logger.info("Notification Watcher daemon stopped.")

    def receive_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        HTTP Endpoint target wrapper. Can receive post requests from Twilio or SendGrid.
        """
        logger.info(f"Received webhook payload: {json.dumps(payload)}")
        parsed_event = self._parse_webhook_payload(payload)
        if parsed_event and self.orchestrator:
            self._trigger_orchestration(parsed_event)
        return {"status": "accepted", "event": parsed_event}

    def _check_external_channels(self) -> Optional[Dict[str, Any]]:
        """
        Mock checker that simulates platform polling checks.
        """
        # In a test loop, we yield nothing to avoid infinite output cycles.
        return None

    def _parse_webhook_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Converts platform-specific webhook formats into standard swarm events.
        """
        # Example Twilio SMS payload
        if "From" in payload and "Body" in payload:
            return {
                "platform": "SMS",
                "contact_id": payload.get("From"),
                "message": payload.get("Body"),
                "timestamp": time.time()
            }
        # Example SendGrid Email payload
        elif "sender" in payload and "subject" in payload:
            return {
                "platform": "Email",
                "contact_id": payload.get("sender"),
                "message": payload.get("text") or payload.get("subject"),
                "timestamp": time.time()
            }
        # Generic payload
        elif "platform" in payload and "contact_id" in payload:
            return payload
            
        return None

    def _trigger_orchestration(self, event: Dict[str, Any]):
        """
        Invokes orchestrator decisions when events land.
        """
        event_str = f"Reply received on {event.get('platform')} from {event.get('contact_id')}: \"{event.get('message')}\""
        if self.orchestrator:
            try:
                # Coordinate workflow step
                decision = self.orchestrator.coordinate_workflow(event_str, f"Watcher: {event.get('platform')}")
                logger.info(f"Orchestration decision executed: {decision}")
            except Exception as e:
                logger.error(f"Watcher failed to trigger orchestrator: {e}")

# --- CLI / Mock Simulation execution interface ---
def run_interactive_simulation():
    print("=" * 60)
    print("AI Outreach Swarm - Notification Watcher Simulation")
    print("=" * 60)

    # Mock Orchestrator to monitor watcher calls
    class MockOrchestrator:
        def coordinate_workflow(self, event: str, context: str) -> str:
            print(f"\n[ORCHESTRATOR TRIPPED]")
            print(f"Event:   {event}")
            print(f"Context: {context}")
            return "Waking Up Swarm -> Transition to AnalysisAgent."

    watcher = NotificationWatcher(orchestrator=MockOrchestrator())
    
    # Simulating Twilio WhatsApp/SMS webhook
    twilio_payload = {
        "From": "+15550192834",
        "Body": "Interested in booking a call next Tuesday."
    }
    
    print("\n--- SIMULATING TWILIO WEBHOOK ---")
    response = watcher.receive_webhook(twilio_payload)
    print(f"Endpoint Response: {response}")

if __name__ == "__main__":
    run_interactive_simulation()
