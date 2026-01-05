"""
Repositories Module

This module provides the repository layer for database operations.
Repositories encapsulate all database queries and provide a clean interface
for the service layer.

Available Repositories:
    - BaseRepository: Abstract base repository with common CRUD operations
    - CameraRepository: Repository for camera-related database operations
    - DetectionRepository: Repository for detection-related database operations

Usage:
    from app.repositories import CameraRepository, DetectionRepository

    camera_repo = CameraRepository(db)
    camera = camera_repo.get_by_id(1)

Author: ANPR Team
Created: 2025
"""

from app.repositories.base import BaseRepository
from app.repositories.camera_repository import CameraRepository
from app.repositories.detection_repository import DetectionRepository

__all__ = ["BaseRepository", "CameraRepository", "DetectionRepository"]
