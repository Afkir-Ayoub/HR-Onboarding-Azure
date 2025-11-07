import json
import os
import msal
import atexit
import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from dotenv import load_dotenv
from pathlib import Path
from dateutil import parser as date_parser
import urllib

logger = logging.getLogger(__name__)
load_dotenv()

# --- Configuration ---
CLIENT_ID = os.getenv("MS_GRAPH_CLIENT_ID")
TENANT_ID = "consumers"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Calendars.ReadWrite", "User.Read"]
CACHE_FILE = Path("ms_graph_token_cache.bin")

# --- MSAL Setup ---
token_cache = msal.SerializableTokenCache()


def load_cache() -> None:
    """Load token cache from file if it exists"""
    if CACHE_FILE.exists():
        try:
            token_cache.deserialize(CACHE_FILE.read_text())
            logger.info("Token cache loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load token cache: {e}")


def save_cache() -> None:
    """Save token cache to file if it has changed"""
    if token_cache.has_state_changed:
        try:
            CACHE_FILE.write_text(token_cache.serialize())
            logger.info("Token cache saved successfully")
        except Exception as e:
            logger.error(f"Failed to save token cache: {e}")


def clear_cache() -> None:
    """Clear the token cache (forces re-authentication)"""
    try:
        # Remove all accounts from the MSAL app
        accounts = app.get_accounts()
        for account in accounts:
            try:
                app.remove_account(account)
                logger.info(f"Removed account: {account.get('username', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Failed to remove account: {e}")
        
        # Clear the in-memory token cache
        empty_cache = '{"AccessToken":{},"RefreshToken":{},"IdToken":{},"Account":{},"AppMetadata":{}}'
        token_cache.deserialize(empty_cache)
        
        # Delete the cache file if it exists
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        
        logger.info("Token cache cleared successfully")
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise


# Load cache
load_cache()

# Register save_cache to be called when the app exits
atexit.register(save_cache)

app = msal.PublicClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    token_cache=token_cache,
)


# --- Core Functions ---
def get_access_token() -> str:
    """
    Get an access token for Microsoft Graph API.
    Uses silent authentication if cached, otherwise initiates device flow.

    Returns:
        str: Valid access token

    Raises:
        Exception: If token acquisition fails
    """
    accounts = app.get_accounts()
    result = None

    if accounts:
        # If we have an account in the cache, try to get a token silently
        logger.info("Attempting to get token from cache...")
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if "access_token" in result:
        logger.info("Access token acquired successfully")
        return result["access_token"]
    else:
        error_msg = result.get("error_description", "Unknown error")
        logger.error(f"Failed to acquire token: {error_msg}")
        raise Exception(f"Could not acquire access token: {error_msg}")


def initiate_device_flow() -> Dict[str, Any]:
    """
    Initiate a device flow for authentication without blocking.
    Returns flow details that can be used for polling.

    Returns:
        Dict containing device_code, user_code, verification_uri, message, etc.

    Raises:
        ValueError: If device flow initiation fails
    """
    logger.info("Initiating device flow...")
    flow = app.initiate_device_flow(scopes=SCOPES)

    if "user_code" not in flow:
        raise ValueError(
            "Failed to create device flow. Please check your app registration."
        )

    logger.info("Device flow initiated successfully")
    return flow


def poll_device_flow(flow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Poll for device flow authentication completion.
    This is non-blocking and should be called repeatedly until authentication completes.

    Args:
        flow: The device flow dictionary returned by initiate_device_flow()

    Returns:
        Dict with 'access_token' if successful, or error information if failed/pending
    """
    try:
        # Validate flow structure
        if not flow or "device_code" not in flow:
            logger.error(f"Invalid flow structure: missing device_code")
            return {
                "status": "error",
                "error": "invalid_flow",
                "error_description": "Invalid device flow structure"
            }
        
        result = app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            logger.info("Access token acquired successfully via device flow")
            save_cache() 
            return result
        elif "error" in result:
            error_code = result.get("error")
            if error_code == "authorization_pending":
                # Still waiting for user to authenticate - this is normal
                logger.debug("Authorization still pending - user hasn't authenticated yet")
                return {"status": "pending"}
            elif error_code == "expired_token":
                # Device code expired
                logger.warning("Device code expired")
                return {
                    "status": "error",
                    "error": error_code,
                    "error_description": "The authentication code has expired. Please start a new authentication flow."
                }
            else:
                # Authentication failed with a specific error
                error_msg = result.get("error_description", f"Error: {error_code}")
                logger.warning(f"Device flow authentication error: {error_code} - {error_msg}")
                return {"status": "error", "error": error_code, "error_description": error_msg}
        else:
            # No error and no access token - still pending
            logger.debug("No access token or error - still pending")
            return {"status": "pending"}
    except Exception as e:
        # Handle any exceptions that might occur during polling
        error_msg = str(e)
        error_type = type(e).__name__
        logger.error(f"Exception during device flow polling ({error_type}): {error_msg}", exc_info=True)
        return {
            "status": "error",
            "error": error_type,
            "error_description": f"An error occurred during authentication: {error_msg}"
        }


def get_access_token_silent() -> Optional[str]:
    """
    Try to get an access token silently from cache.
    Returns None if no valid token is available.

    Returns:
        str: Valid access token, or None if not available
    """
    accounts = app.get_accounts()
    if accounts:
        logger.info("Attempting to get token from cache...")
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            logger.info("Access token acquired from cache")
            return result["access_token"]
    return None


def is_authenticated() -> bool:
    """
    Check if user is currently authenticated (has valid token in cache).

    Returns:
        bool: True if authenticated, False otherwise
    """
    return get_access_token_silent() is not None


class GraphAPIClient:
    """Client for Microsoft Graph API operations"""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self):
        self.token = None
        self.headers = None

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token"""
        if not self.token:
            self.token = get_access_token()
            self.headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict[Any, Any]:
        """
        Make an authenticated request to Microsoft Graph API

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            data: Optional JSON data for POST/PATCH requests

        Returns:
            Response JSON as dictionary

        Raises:
            requests.exceptions.HTTPError: If request fails
        """
        self._ensure_authenticated()

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.request(
                method=method, url=url, headers=self.headers, json=data, timeout=30
            )
            response.raise_for_status()

            # Some endpoints return no content (204)
            if response.status_code == 204:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(
                f"API request failed: {e.response.status_code} - {e.response.text}"
            )
            raise

    # --- User Profile ---
    def get_user_profile(self) -> Dict:
        """Get the authenticated user's profile"""
        return self._make_request("GET", "me")

    # --- Calendar Operations ---
    def create_calendar_event(
        self,
        subject: str,
        start_time: datetime,
        duration_minutes: int = 60,
        body: Optional[str] = None,
        location: Optional[str] = None,
        reminder_minutes: int = 15,
    ) -> Dict:
        """
        Create a calendar event

        Args:
            subject: Event title
            start_time: Event start time (datetime object)
            duration_minutes: Event duration in minutes
            body: Optional event description
            location: Optional event location
            reminder_minutes: Reminder before event (minutes)

        Returns:
            Created event details
        """
        end_time = start_time + timedelta(minutes=duration_minutes)

        event_data = {
            "subject": subject,
            "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
            "isReminderOn": True,
            "reminderMinutesBeforeStart": reminder_minutes,
        }

        if body:
            event_data["body"] = {"contentType": "Text", "content": body}

        if location:
            event_data["location"] = {"displayName": location}

        result = self._make_request("POST", "me/events", event_data)
        logger.info(f"Created calendar event: {subject}")
        return result

    def list_calendar_events(self, days_ahead: int = 7, max_results: int = 50) -> list:
        """
        List upcoming calendar events

        Args:
            days_ahead: Number of days to look ahead
            max_results: Maximum number of events to return

        Returns:
            List of calendar events
        """
        start_time = urllib.parse.quote(datetime.now(timezone.utc).isoformat())
        end_time = urllib.parse.quote((datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat())

        endpoint = (
            f"me/calendar/calendarView?"
            f"startDateTime={start_time}&"
            f"endDateTime={end_time}&"
            f"$top={max_results}"
        )

        result = self._make_request("GET", endpoint)
        return result.get("value", [])


# --- Helper Functions ---
def parse_datetime(time_input: Union[str, datetime]) -> datetime:
    """
    Parse various datetime formats into a datetime object

    Args:
        time_input: String or datetime object

    Returns:
        datetime object

    Raises:
        ValueError: If unable to parse the datetime
    """
    if isinstance(time_input, datetime):
        return time_input

    try:
        # Try ISO format first
        return datetime.fromisoformat(time_input.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pass

    try:
        # Try dateutil parser (very flexible)
        return date_parser.parse(time_input)
    except Exception as e:
        raise ValueError(f"Unable to parse datetime '{time_input}': {e}")


def calendar_event(reminder: Union[str, Dict]) -> str:
    """
    Create a calendar event on the user's Microsoft Calendar. This is for when a user explicitly asks to create a calendar event.

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
    try:
        # Parse input if it's a JSON string
        if isinstance(reminder, str):
            try:
                reminder = json.loads(reminder)
            except json.JSONDecodeError:
                return "❌ Error: Invalid JSON format. Please provide event details as JSON."

        # Validate required fields
        if not isinstance(reminder, dict):
            return "❌ Error: Event details must be a dictionary/JSON object."

        title = reminder.get("title") or reminder.get("subject")
        time_input = (
            reminder.get("time")
            or reminder.get("start_time")
            or reminder.get("datetime")
        )

        if not title:
            return "❌ Error: Event 'title' is required."

        if not time_input:
            return "❌ Error: Event 'time' is required."

        # Parse datetime
        try:
            event_time = parse_datetime(time_input)
        except ValueError as e:
            return f"❌ Error: {str(e)}"

        # Check if event is in the past
        if event_time < datetime.now():
            return f"❌ Error: Event time '{event_time.strftime('%Y-%m-%d %H:%M')}' is in the past."

        # Extract optional fields
        description = reminder.get("description") or reminder.get("body")
        duration = reminder.get("duration_minutes", 60)
        location = reminder.get("location")
        reminder_mins = reminder.get("reminder_minutes", 15)

        # Validate duration
        try:
            duration = int(duration)
            if duration <= 0 or duration > 1440:  # Max 24 hours
                duration = 60
        except (ValueError, TypeError):
            duration = 60

        # Create the event
        client = GraphAPIClient()
        client.create_calendar_event(
            subject=title,
            start_time=event_time,
            duration_minutes=duration,
            body=description,
            location=location,
            reminder_minutes=reminder_mins,
        )

        # Format success message
        event_datetime_str = event_time.strftime("%A, %B %d, %Y at %I:%M %p")
        message = f"✅ Calendar event created successfully!\n\n"
        message += f"📅 {title}\n"
        message += f"🕒 {event_datetime_str}\n"
        message += f"⏱️ Duration: {duration} minutes\n"

        if description:
            message += f"📝 {description}\n"
        if location:
            message += f"📍 {location}\n"

        message += f"\n🔔 Reminder set for {reminder_mins} minutes before the event."

        logger.info(f"Successfully created event: {title}")
        return message

    except Exception as e:
        error_msg = f"❌ Failed to create calendar event: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def list_upcoming_events(days: int = 7) -> str:
    """
    List upcoming calendar events

    Args:
        days: Number of days to look ahead

    Returns:
        Formatted string of events
    """
    try:
        client = GraphAPIClient()
        events = client.list_calendar_events(days_ahead=days)

        if not events:
            return f"No events found in the next {days} days."

        output = [f"\n📅 Upcoming Events (next {days} days):\n"]

        for event in events:
            start = datetime.fromisoformat(
                event["start"]["dateTime"].replace("Z", "+00:00")
            )
            subject = event.get("subject", "No title")
            output.append(f"• {start.strftime('%Y-%m-%d %H:%M')} - {subject}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Failed to list events: {e}", exc_info=True)
        return f"❌ Failed to list events: {str(e)}"

