"""Pydantic schemas for request/response validation"""
from app.schemas.camera import (
    CameraBase,
    CameraCreate,
    CameraUpdate,
    CameraInDB,
    CameraResponse,
    WorkerControl
)
from app.schemas.detection import (
    DetectionBase,
    DetectionCreate,
    DetectionInDB,
    DetectionResponse,
    DetectionFilter
)

__all__ = [
    "CameraBase",
    "CameraCreate",
    "CameraUpdate",
    "CameraInDB",
    "CameraResponse",
    "WorkerControl",
    "DetectionBase",
    "DetectionCreate",
    "DetectionInDB",
    "DetectionResponse",
    "DetectionFilter",
]
