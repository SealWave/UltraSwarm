"""
agents/fiverr/shared/state.py

Centralized in-memory state store shared across all Fiverr automation agents
within a single session. The Fiverr_Manager owns the Shared_State instance and
passes it as context to every sub-agent invocation.
"""

from datetime import datetime, timezone
from typing import Any


class Shared_State:
    """Centralized state store for all Fiverr agents.

    Attributes
    ----------
    session_id : str
        Unique identifier for the current automation session.
    agent_registry : dict
        Metadata registry keyed by agent name, populated during
        Fiverr_Manager initialization via each agent's get_metadata().
    active_gigs : list
        List of dicts describing currently active Fiverr gig listings.
    open_orders : list
        List of dicts describing open/in-progress Fiverr orders.
    inbox_messages : list
        List of dicts representing unread or recent inbox messages.
    new_events : list
        List of event dicts yet to be dispatched by the Notification_Agent.
    notified_events : set
        Set of composite keys (event_type + timestamp) for already-dispatched
        events, used to prevent duplicate notifications.
    change_log : list
        Append-only list of state-change dicts, each containing 'key',
        'value', and 'timestamp' (UTC ISO-8601 string).
    """

    def __init__(self, session_id: str) -> None:
        self.session_id: str = session_id
        self.agent_registry: dict = {}
        self.active_gigs: list = []
        self.open_orders: list = []
        self.inbox_messages: list = []
        self.new_events: list = []
        self.notified_events: set = set()
        self.change_log: list = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any:
        """Return the value of *key*, or ``None`` if the key does not exist.

        Never raises an exception for missing keys.

        Parameters
        ----------
        key:
            Name of the attribute to retrieve.

        Returns
        -------
        Any
            Current value of the attribute, or ``None`` when absent.
        """
        return getattr(self, key, None)

    def set(self, key: str, value: Any) -> None:
        """Update instance attribute *key* to *value* and record the change.

        The change is appended to :attr:`change_log` as a dict with the keys:

        - ``key`` – attribute name (str)
        - ``value`` – new value (Any)
        - ``timestamp`` – UTC ISO-8601 string (e.g. ``"2024-01-15T10:30:01Z"``)

        Parameters
        ----------
        key:
            Attribute name to set.
        value:
            New value to assign.
        """
        setattr(self, key, value)

        timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.change_log.append(
            {
                "key": key,
                "value": value,
                "timestamp": timestamp,
            }
        )

    def to_context_dict(self) -> dict:
        """Return a JSON-serializable snapshot of the current state.

        ``notified_events`` (a ``set``) is serialized as a **sorted list of
        strings** so the result can be safely passed to ``json.dumps()``.

        Returns
        -------
        dict
            All public state attributes in a plain-dict form.
        """
        return {
            "session_id": self.session_id,
            "agent_registry": self.agent_registry,
            "active_gigs": self.active_gigs,
            "open_orders": self.open_orders,
            "inbox_messages": self.inbox_messages,
            "new_events": self.new_events,
            # Convert set → sorted list for JSON serializability
            "notified_events": sorted(str(e) for e in self.notified_events),
            "change_log": self.change_log,
        }
