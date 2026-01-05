"""
Camera Service Module

This module provides business logic for camera management.
It orchestrates between the camera repository and other services.

Author: ANPR Team
Created: 2025
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.camera import Camera
from app.models.enums import StreamType
from app.repositories.camera_repository import CameraRepository
from app.schemas.camera import CameraCreate, CameraUpdate


class CameraService:
    """
    Camera Service

    Handles business logic for camera operations including creation, updates,
    deletion, and validation. This service sits between the API layer and
    the repository layer.

    Responsibilities:
        - Validate business rules before database operations
        - Coordinate with worker service for camera stream management
        - Handle camera lifecycle events
        - Provide camera statistics and analytics

    Example:
        camera_service = CameraService(db)

        # Create camera
        camera = camera_service.create_camera(
            name="Gate Camera",
            stream_url="rtsp://...",
            roi_polygon=[[0,0], [100,0], [100,100], [0,100]],
            detection_line=[50, 0, 50, 100],
            organization_id=1
        )

        # Update camera
        updated = camera_service.update_camera(
            camera_id=1,
            name="Updated Gate Camera",
            confidence=0.8
        )
    """

    def __init__(self, db: Session):
        """
        Initialize the Camera Service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.camera_repo = CameraRepository(db)

    def get_camera_by_id(self, camera_id: int) -> Camera:
        """
        Get camera by ID

        Args:
            camera_id: The camera ID

        Returns:
            Camera instance

        Raises:
            HTTPException: If camera not found (404)
        """
        camera = self.camera_repo.get_by_id(camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail=f"Camera with ID {camera_id} not found")
        return camera

    def get_all_cameras(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[Camera]:
        """
        Get all cameras with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: Whether to return only active cameras

        Returns:
            List of Camera instances
        """
        return self.camera_repo.get_all(
            skip=skip,
            limit=limit,
            include_inactive=not active_only
        )

    def get_active_cameras(self) -> List[Camera]:
        """
        Get all active cameras

        Returns:
            List of active Camera instances
        """
        return self.camera_repo.get_active_cameras()

    def create_camera(
        self,
        name: str,
        stream_url: str,
        roi_polygon: List[List[int]],
        detection_line: List[int],
        stream_type: StreamType = StreamType.DOWNSIDE_UP,
        target_fps: int = 3,
        confidence: float = 0.3,
        detection_types: List[int] = None,
        organization_id: int = 1
    ) -> Camera:
        """
        Create a new camera

        Validates camera configuration before creation.

        Args:
            name: Camera name
            stream_url: Video stream URL (RTSP, HTTP, IP, etc.)
            roi_polygon: Region of Interest polygon coordinates
            detection_line: Detection line coordinates [x1, y1, x2, y2]
            stream_type: Stream orientation type (default: DOWNSIDE_UP)
            target_fps: Target frames per second (default: 3)
            confidence: Detection confidence threshold (default: 0.3)
            detection_types: List of YOLO class IDs to detect (default: None)
            organization_id: Organization ID (default: 1)

        Returns:
            Created Camera instance

        Raises:
            HTTPException: If camera with same name exists (400)
        """
        # Check if camera with same name already exists
        existing = self.camera_repo.get_by_name(name)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Camera with name '{name}' already exists"
            )

        # Validate ROI polygon (at least 3 points)
        if len(roi_polygon) < 3:
            raise HTTPException(
                status_code=400,
                detail="ROI polygon must have at least 3 points"
            )

        # Validate detection line (exactly 4 coordinates)
        if len(detection_line) != 4:
            raise HTTPException(
                status_code=400,
                detail="Detection line must have exactly 4 coordinates [x1, y1, x2, y2]"
            )

        # Validate target FPS
        if target_fps < 1 or target_fps > 30:
            raise HTTPException(
                status_code=400,
                detail="Target FPS must be between 1 and 30"
            )

        # Validate confidence threshold
        if confidence < 0.0 or confidence > 1.0:
            raise HTTPException(
                status_code=400,
                detail="Confidence must be between 0.0 and 1.0"
            )

        # Create camera
        camera = self.camera_repo.create(
            name=name,
            stream_url=stream_url,
            stream_type=stream_type,
            roi_polygon=roi_polygon,
            detection_line=detection_line,
            target_fps=target_fps,
            confidence=confidence,
            detection_types=detection_types,
            organization_id=organization_id
        )

        return camera

    def update_camera(
        self,
        camera_id: int,
        **update_data
    ) -> Camera:
        """
        Update camera details

        Args:
            camera_id: The camera ID
            **update_data: Fields to update

        Returns:
            Updated Camera instance

        Raises:
            HTTPException: If camera not found (404) or validation fails (400)
        """
        # Check if camera exists
        camera = self.get_camera_by_id(camera_id)

        # If updating name, check for duplicates
        if 'name' in update_data and update_data['name'] != camera.name:
            existing = self.camera_repo.get_by_name(update_data['name'])
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Camera with name '{update_data['name']}' already exists"
                )

        # Validate ROI polygon if provided
        if 'roi_polygon' in update_data:
            if len(update_data['roi_polygon']) < 3:
                raise HTTPException(
                    status_code=400,
                    detail="ROI polygon must have at least 3 points"
                )

        # Validate detection line if provided
        if 'detection_line' in update_data:
            if len(update_data['detection_line']) != 4:
                raise HTTPException(
                    status_code=400,
                    detail="Detection line must have exactly 4 coordinates"
                )

        # Validate target FPS if provided
        if 'target_fps' in update_data:
            if update_data['target_fps'] < 1 or update_data['target_fps'] > 30:
                raise HTTPException(
                    status_code=400,
                    detail="Target FPS must be between 1 and 30"
                )

        # Validate confidence if provided
        if 'confidence' in update_data:
            if update_data['confidence'] < 0.0 or update_data['confidence'] > 1.0:
                raise HTTPException(
                    status_code=400,
                    detail="Confidence must be between 0.0 and 1.0"
                )

        # Update camera
        updated_camera = self.camera_repo.update(camera_id, **update_data)

        return updated_camera

    def delete_camera(self, camera_id: int, soft_delete: bool = True) -> Dict[str, Any]:
        """
        Delete a camera

        Args:
            camera_id: The camera ID
            soft_delete: If True, mark as inactive; if False, permanently delete

        Returns:
            Dictionary with success message

        Raises:
            HTTPException: If camera not found (404)

        Note:
            Before deleting, ensure the camera's worker is stopped using WorkerService
        """
        # Check if camera exists
        camera = self.get_camera_by_id(camera_id)

        # Delete camera
        success = self.camera_repo.delete(camera_id, soft_delete=soft_delete)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete camera"
            )

        return {
            "message": f"Camera '{camera.name}' deleted successfully",
            "camera_id": camera_id,
            "soft_delete": soft_delete
        }

    def deactivate_camera(self, camera_id: int) -> Camera:
        """
        Deactivate a camera (soft delete)

        Args:
            camera_id: The camera ID

        Returns:
            Deactivated Camera instance

        Raises:
            HTTPException: If camera not found (404)
        """
        # Check if camera exists
        camera = self.get_camera_by_id(camera_id)

        # Deactivate
        success = self.camera_repo.deactivate(camera_id)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to deactivate camera"
            )

        # Refresh camera object
        return self.camera_repo.get_by_id(camera_id, include_inactive=True)

    def activate_camera(self, camera_id: int) -> Camera:
        """
        Activate a previously deactivated camera

        Args:
            camera_id: The camera ID

        Returns:
            Activated Camera instance

        Raises:
            HTTPException: If camera not found (404)
        """
        success = self.camera_repo.activate(camera_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Camera with ID {camera_id} not found"
            )

        return self.camera_repo.get_by_id(camera_id)

    def search_cameras(self, name_pattern: str, limit: int = 10) -> List[Camera]:
        """
        Search cameras by name pattern

        Args:
            name_pattern: Pattern to search for
            limit: Maximum number of results

        Returns:
            List of matching Camera instances
        """
        return self.camera_repo.search_by_name(name_pattern, limit=limit)

    def get_camera_statistics(self, camera_id: int) -> Dict[str, Any]:
        """
        Get statistics for a camera including detection count

        Args:
            camera_id: The camera ID

        Returns:
            Dictionary with camera statistics

        Raises:
            HTTPException: If camera not found (404)
        """
        result = self.camera_repo.get_with_detection_count(camera_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Camera with ID {camera_id} not found"
            )

        camera = result["camera"]
        detection_count = result["detection_count"]

        return {
            "camera_id": camera.id,
            "name": camera.name,
            "stream_url": camera.stream_url,
            "is_active": camera.is_active,
            "detection_count": detection_count,
            "created_at": camera.created_at,
            "updated_at": camera.updated_at
        }

    def update_stream_settings(
        self,
        camera_id: int,
        target_fps: Optional[int] = None,
        confidence: Optional[float] = None
    ) -> Camera:
        """
        Update camera stream processing settings

        Args:
            camera_id: The camera ID
            target_fps: Optional new target FPS
            confidence: Optional new confidence threshold

        Returns:
            Updated Camera instance

        Raises:
            HTTPException: If camera not found (404) or validation fails (400)

        Note:
            If a worker is running for this camera, it should be restarted
            to apply the new settings.
        """
        # Validate inputs
        if target_fps is not None and (target_fps < 1 or target_fps > 30):
            raise HTTPException(
                status_code=400,
                detail="Target FPS must be between 1 and 30"
            )

        if confidence is not None and (confidence < 0.0 or confidence > 1.0):
            raise HTTPException(
                status_code=400,
                detail="Confidence must be between 0.0 and 1.0"
            )

        # Update settings
        updated_camera = self.camera_repo.update_stream_settings(
            camera_id,
            target_fps=target_fps,
            confidence=confidence
        )

        if not updated_camera:
            raise HTTPException(
                status_code=404,
                detail=f"Camera with ID {camera_id} not found"
            )

        return updated_camera

    def update_roi_configuration(
        self,
        camera_id: int,
        roi_polygon: Optional[List[List[int]]] = None,
        detection_line: Optional[List[int]] = None
    ) -> Camera:
        """
        Update camera ROI configuration

        Args:
            camera_id: The camera ID
            roi_polygon: Optional new ROI polygon
            detection_line: Optional new detection line

        Returns:
            Updated Camera instance

        Raises:
            HTTPException: If camera not found (404) or validation fails (400)

        Note:
            If a worker is running for this camera, it should be restarted
            to apply the new ROI configuration.
        """
        # Validate ROI polygon
        if roi_polygon is not None and len(roi_polygon) < 3:
            raise HTTPException(
                status_code=400,
                detail="ROI polygon must have at least 3 points"
            )

        # Validate detection line
        if detection_line is not None and len(detection_line) != 4:
            raise HTTPException(
                status_code=400,
                detail="Detection line must have exactly 4 coordinates"
            )

        # Update configuration
        updated_camera = self.camera_repo.update_roi_config(
            camera_id,
            roi_polygon=roi_polygon,
            detection_line=detection_line
        )

        if not updated_camera:
            raise HTTPException(
                status_code=404,
                detail=f"Camera with ID {camera_id} not found"
            )

        return updated_camera
