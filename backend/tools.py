"""LangChain tool definitions for the HR assistant agent."""
import logging
from langchain_core.tools import tool
from .ms_graph import calendar_event, list_upcoming_events
from .state import app_state

logger = logging.getLogger(__name__)


@tool
def hr_knowledge_base(query: str) -> str:
    """Search the company's HR knowledge base for information about HR policies,
    onboarding procedures, first-week tasks, benefits, or contact information.

    Args:
        query: A clear, specific question about HR topics

    Returns:
        Information from the HR knowledge base
    """
    try:
        if not app_state.query_engine:
            return "I'm sorry, the knowledge base is not available at the moment."
        response = app_state.query_engine.query(query)
        return str(response)
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return f"I encountered an error accessing the knowledge base: {str(e)}"


@tool
def create_calendar_event(reminder):
    """Create a calendar event on the user's Microsoft Calendar. This is for when a user explicitly asks to create a calendar event or reminder.
    
    Args:
        reminder: JSON string or dict with event details. Expected keys:
            - title (required): Event title
            - time (required): Event datetime (ISO format or natural language)
            - description (optional): Event description
            - duration_minutes (optional): Event duration (default: 60)
            - location (optional): Event location
            - reminder_minutes (optional): Reminder time before event (default: 15)

    Returns:
        str: Success or error message for the agent

    Example input:
        {
            "title": "Team meeting",
            "time": "2025-11-06T14:00:00",
            "description": "Discuss Q4 goals",
            "duration_minutes": 60,
            "location": "Conference Room A"
        }
    """
    return calendar_event(reminder)


@tool
def list_calendar_events(days: int = 7):
    """List upcoming calendar events.
    
    Args:
        days: Number of days to look ahead (default: 7)
    
    Returns:
        Formatted string of events
    """
    return list_upcoming_events(days)

