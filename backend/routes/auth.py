"""Authentication API routes for Microsoft Graph."""
import logging
import uuid
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..ms_graph import (
    initiate_device_flow,
    poll_device_flow,
    is_authenticated,
    get_access_token_silent,
    clear_cache,
    GraphAPIClient,
)
from ..state import app_state

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/initiate")
def initiate_auth() -> Dict[str, Any]:
    """
    Initiate device flow authentication.
    Returns the authentication URL and user code for the frontend to display.
    """
    try:
        # Check if already authenticated
        if is_authenticated():
            return {
                "status": "authenticated",
                "message": "User is already authenticated",
            }

        # Initiate device flow
        flow = initiate_device_flow()

        # Generate a unique flow ID to track this authentication session
        flow_id = str(uuid.uuid4())
        app_state.active_device_flows[flow_id] = flow

        return {
            "status": "pending",
            "flow_id": flow_id,
            "user_code": flow.get("user_code"),
            "verification_uri": flow.get("verification_uri"),
            "message": flow.get("message"),
            "expires_in": flow.get("expires_in", 900),  # Default 15 minutes
        }
    except Exception as e:
        logger.error(f"Failed to initiate authentication: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate authentication: {str(e)}",
        )


@router.get("/auth/status")
def get_auth_status(flow_id: str) -> Dict[str, Any]:
    """
    Poll for authentication status.
    Checks if the device flow authentication has completed.
    """
    try:
        if is_authenticated():
            app_state.active_device_flows.clear()
            return {
                "status": "authenticated",
                "message": "User is authenticated",
            }

        # Check if flow exists
        if flow_id not in app_state.active_device_flows:
            raise HTTPException(
                status_code=404,
                detail="Authentication flow not found. Please initiate a new flow.",
            )

        flow = app_state.active_device_flows[flow_id]

        # Poll the device flow
        result = poll_device_flow(flow)

        if "access_token" in result:
            # Authentication successful
            app_state.active_device_flows.pop(flow_id, None)
            return {
                "status": "authenticated",
                "message": "Authentication successful",
            }
        elif result.get("status") == "error":
            # Authentication failed
            app_state.active_device_flows.pop(flow_id, None)
            error_description = result.get("error_description") or result.get("error") or "Unknown authentication error"
            return {
                "status": "error",
                "error": result.get("error", "unknown_error"),
                "error_description": error_description,
            }
        else:
            return {
                "status": "pending",
                "message": "Waiting for user authentication",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check authentication status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check authentication status: {str(e)}",
        )


@router.get("/auth/check")
def check_auth() -> Dict[str, Any]:
    """
    Check if user is currently authenticated.
    Returns authentication status without requiring a flow_id.
    """
    try:
        authenticated = is_authenticated()
        if authenticated:
            return {
                "status": "authenticated",
                "authenticated": True,
            }
        else:
            return {
                "status": "not_authenticated",
                "authenticated": False,
            }
    except Exception as e:
        logger.error(f"Failed to check authentication: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check authentication: {str(e)}",
        )


@router.get("/auth/user")
def get_user() -> Dict[str, Any]:
    """
    Get the authenticated user's profile.
    """
    try:
        if not is_authenticated():
            raise HTTPException(
                status_code=401,
                detail="User is not authenticated. Please authenticate first.",
            )

        client = GraphAPIClient()
        profile = client.get_user_profile()

        return {
            "status": "success",
            "user": profile,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user profile: {str(e)}",
        )


@router.post("/auth/logout")
def logout() -> Dict[str, Any]:
    """
    Logout the user by clearing the token cache.
    """
    try:
        clear_cache()
        app_state.active_device_flows.clear()
        return {
            "status": "success",
            "message": "Logged out successfully",
        }
    except Exception as e:
        logger.error(f"Failed to logout: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to logout: {str(e)}",
        )

