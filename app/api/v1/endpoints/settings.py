"""
Settings API Endpoints

This module provides REST API endpoints for managing application settings,
including central server configuration.

Author: ANPR Team
Created: 2025
"""

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.settings import CentralServerConfig, CentralServerUpdate

# Create router for settings endpoints
router = APIRouter(prefix="/settings", tags=["settings"])


def _mask_api_key(api_key: str) -> str:
    """
    Mask API key for security

    Shows first 8 and last 4 characters, masks the rest.
    Example: "8605fa5cba1d507c7e348186f070f05458fdba9192b9e4791a0026034e790467"
             becomes "8605fa5c...0467"

    Args:
        api_key: Full API key to mask

    Returns:
        Masked API key string
    """
    if len(api_key) <= 12:
        # If key is too short, just mask it completely
        return "***"
    return f"{api_key[:8]}...{api_key[-4:]}"


@router.get("/central-server", response_model=CentralServerConfig)
def get_central_server_config():
    """
    Get current central server configuration

    Returns the current configuration for the central server including
    URL, masked API key, timeout, and organization ID.

    **Returns:**
    - `central_server_url`: URL of the central server
    - `central_server_api_key`: Masked API key (only first 8 and last 4 chars visible)
    - `central_server_timeout`: Request timeout in seconds
    - `organization_id`: Organization ID

    **Security Note:**
    API key is masked for security. Only first 8 and last 4 characters are shown.
    """
    return CentralServerConfig(
        central_server_url=settings.CENTRAL_SERVER_URL,
        central_server_api_key=_mask_api_key(settings.CENTRAL_SERVER_API_KEY),
        central_server_timeout=settings.CENTRAL_SERVER_TIMEOUT,
        central_server_enabled=settings.CENTRAL_SERVER_ENABLED,
        organization_id=settings.ORGANIZATION_ID
    )


@router.put("/central-server", response_model=dict)
def update_central_server_config(config: CentralServerUpdate):
    """
    Update central server configuration

    Updates the central server URL and API key. Changes are applied immediately
    to all new detection uploads.

    **Important:** This is an in-memory update only. Changes will be lost when
    the application restarts. For persistent changes, update the .env file.

    **Request Body:**
    - `central_server_url`: New central server URL (must start with http:// or https://)
    - `central_server_api_key`: New API key for authentication

    **Returns:**
    - Success message with masked new API key
    - Updated configuration details

    **Raises:**
    - `400`: Invalid URL format or empty API key

    **Example:**
    ```json
    {
        "central_server_url": "http://localhost:8010/api/v1/detections",
        "central_server_api_key": "8605fa5cba1d507c7e348186f070f05458fdba9192b9e4791a0026034e790467"
    }
    ```
    """
    try:
        # Update settings
        settings.update_central_server(
            url=config.central_server_url,
            api_key=config.central_server_api_key,
            enabled=config.central_server_enabled
        )

        return {
            "message": "Central server configuration updated successfully",
            "central_server_url": config.central_server_url,
            "central_server_api_key": _mask_api_key(config.central_server_api_key),
            "central_server_enabled": config.central_server_enabled,
            "note": "Changes are in-memory only and will be lost on restart. Update .env file for persistence."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update central server configuration: {str(e)}"
        )
