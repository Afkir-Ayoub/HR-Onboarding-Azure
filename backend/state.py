"""Application state management."""
from typing import Optional, Dict, Any


class AppState:
    """Application state to hold the agent and query engine."""

    agent: Optional[object] = None
    query_engine: Optional[object] = None
    active_device_flows: Dict[str, Dict[str, Any]] = {}


# Global application state instance
app_state = AppState()

