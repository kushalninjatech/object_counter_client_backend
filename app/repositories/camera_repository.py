"""
Camera Repository Module

This module provides the repository for camera-related database operations.
It extends the BaseRepository with camera-specific query methods.

Author: ANPR Team
Created: 2025
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.camera import Camera
from app.repositories.base import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    """
    Camera Repository

    Handles all database operations related to cameras. Provides methods for
    querying cameras by various criteria such as name or active status.

    Inherits common CRUD operations from BaseRepository and adds camera-specific queries.

    Example:
        camera_repo = CameraRepository(db)

        # Get camera by ID
        camera = camera_repo.get_by_id(1)

        # Create new camera
        camera = camera_repo.create(
            name="Gate Camera",
            stream_url="rtsp://...",
            roi_polygon=[[0, 0], [100, 0], [100, 100], [0, 100]],
            detection_line=[50, 50, 50, 100],
            organization_id=1
        )

        # Get all active cameras
        cameras = camera_repo.get_active_cameras()
    """

    def __init__(self, db: Session):
        """
        Initialize the Camera Repository

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(Camera, db)

    def get_by_name(self, name: str) -> Optional[Camera]:
        """
        Get a camera by exact name

        Args:
            name: The camera name

        Returns:
            Camera instance if found, None otherwise
        """
        return self.db.query(Camera).filter(
            Camera.name == name,
            Camera.is_active == True  # noqa: E712
        ).first()

    def search_by_name(self, name_pattern: str, limit: int = 10) -> List[Camera]:
        """
        Search cameras by name pattern (case-insensitive)

        Args:
            name_pattern: Pattern to search for (supports SQL LIKE wildcards)
            limit: Maximum number of results (default: 10)

        Returns:
            List of matching Camera instances

        Example:
            # Find cameras with "gate" in the name
            cameras = camera_repo.search_by_name("%gate%")
        """
        return self.db.query(Camera).filter(
            Camera.name.ilike(f"%{name_pattern}%"),
            Camera.is_active == True  # noqa: E712
        ).limit(limit).all()

    def get_active_cameras(self) -> List[Camera]:
        """
        Get all active cameras

        Returns:
            List of active Camera instances ordered by name
        """
        return self.db.query(Camera).filter(
            Camera.is_active == True  # noqa: E712
        ).order_by(Camera.name).all()

    def update_stream_settings(
        self,
        camera_id: int,
        target_fps: Optional[int] = None,
        confidence: Optional[float] = None
    ) -> Optional[Camera]:
        """
        Update camera stream processing settings

        Args:
            camera_id: The camera ID
            target_fps: Optional new target FPS (frames to process per second)
            confidence: Optional new confidence threshold (0.0-1.0)

        Returns:
            Updated Camera instance if found, None otherwise

        Example:
            camera = camera_repo.update_stream_settings(1, target_fps=5, confidence=0.7)
        """
        camera = self.get_by_id(camera_id)
        if not camera:
            return None

        if target_fps is not None:
            camera.target_fps = target_fps

        if confidence is not None:
            camera.confidence = confidence

        self.db.commit()
        self.db.refresh(camera)
        return camera

    def update_roi_config(
        self,
        camera_id: int,
        roi_polygon: Optional[List[List[int]]] = None,
        detection_line: Optional[List[int]] = None
    ) -> Optional[Camera]:
        """
        Update camera ROI (Region of Interest) configuration

        Args:
            camera_id: The camera ID
            roi_polygon: Optional new ROI polygon coordinates [[x1,y1], [x2,y2], ...]
            detection_line: Optional new detection line coordinates [x1, y1, x2, y2]

        Returns:
            Updated Camera instance if found, None otherwise

        Example:
            camera = camera_repo.update_roi_config(
                1,
                roi_polygon=[[0, 0], [100, 0], [100, 100], [0, 100]],
                detection_line=[50, 0, 50, 100]
            )
        """
        camera = self.get_by_id(camera_id)
        if not camera:
            return None

        if roi_polygon is not None:
            camera.roi_polygon = roi_polygon

        if detection_line is not None:
            camera.detection_line = detection_line

        self.db.commit()
        self.db.refresh(camera)
        return camera

    def deactivate(self, camera_id: int) -> bool:
        """
        Deactivate a camera (soft delete)

        This marks the camera as inactive instead of permanently deleting it.
        Useful for maintaining historical data and audit trails.

        Args:
            camera_id: The camera ID

        Returns:
            True if deactivated successfully, False if not found
        """
        return self.delete(camera_id, soft_delete=True)

    def activate(self, camera_id: int) -> bool:
        """
        Activate a previously deactivated camera

        Args:
            camera_id: The camera ID

        Returns:
            True if activated successfully, False if not found
        """
        camera = self.get_by_id(camera_id, include_inactive=True)
        if not camera:
            return False

        camera.is_active = True
        self.db.commit()
        return True

    def get_with_detection_count(self, camera_id: int) -> Optional[dict]:
        """
        Get camera with its total detection count

        Args:
            camera_id: The camera ID

        Returns:
            Dictionary with camera data and detection count, or None if not found

        Example:
            result = camera_repo.get_with_detection_count(1)
            # Returns: {"camera": Camera(...), "detection_count": 42}
        """
        camera = self.get_by_id(camera_id)
        if not camera:
            return None

        # Count detections for this camera
        from app.models.detection import Detection
        detection_count = self.db.query(Detection).filter(
            Detection.camera_id == camera_id,
            Detection.is_active == True  # noqa: E712
        ).count()

        return {
            "camera": camera,
            "detection_count": detection_count
        }
