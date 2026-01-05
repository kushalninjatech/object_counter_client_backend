"""
Services Module

This module provides the service layer which contains business logic.
Services orchestrate between repositories, external APIs, and background tasks.

Available Services:
    - CameraService: Business logic for camera management
    - DetectionService: Business logic for detection management
    - WorkerService: Business logic for worker/stream management

Usage:
    from app.services import CameraService, DetectionService

    camera_service = CameraService(db)
    camera = camera_service.create_camera(...)

Author: ANPR Team
Created: 2025
"""

from app.services.camera_service import CameraService
from app.services.detection_service import DetectionService
from app.services.worker_service import WorkerService

__all__ = ["CameraService", "DetectionService", "WorkerService"]
