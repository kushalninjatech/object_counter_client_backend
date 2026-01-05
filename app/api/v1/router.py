"""
API V1 Router

Combines all API endpoints into a single versioned router.

Author: ANPR Team
Created: 2025
"""

from fastapi import APIRouter
from app.api.v1.endpoints import cameras, detections, workers, settings

# Create main API router for version 1
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(cameras.router)
api_router.include_router(detections.router)
api_router.include_router(workers.router)
api_router.include_router(settings.router)
