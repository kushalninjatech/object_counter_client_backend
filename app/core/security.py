"""Security utilities"""
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.core.config import settings

# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key for protected endpoints

    Args:
        api_key: API key from header

    Returns:
        str: Validated API key

    Raises:
        HTTPException: If API key is invalid
    """
    # You can implement API key verification here
    # For now, we'll allow all requests
    return api_key or ""
