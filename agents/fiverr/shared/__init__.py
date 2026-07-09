"""
agents/fiverr/shared/
=====================
Shared infrastructure for all Fiverr automation agents.

Provides centralized state management and environment-based configuration
consumed by every Fiverr sub-agent and the Fiverr_Manager orchestrator.

Exports:
    Shared_State    — in-memory context store for a single automation session
    config          — module-level credential and settings constants

Usage:
    from agents.fiverr.shared import Shared_State
    from agents.fiverr.shared import config

    state = Shared_State(session_id="abc123")
    print(config.FIVERR_USERNAME)
"""

from agents.fiverr.shared.state import Shared_State

try:
    from agents.fiverr.shared import config
except ImportError:
    config = None  # type: ignore[assignment]

__all__ = [
    "Shared_State",
    "config",
]
