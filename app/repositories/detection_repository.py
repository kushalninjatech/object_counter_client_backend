"""
Detection Repository Module

This module provides the repository for detection-related database operations.
It extends the BaseRepository with detection-specific query methods.

Author: ANPR Team
Created: 2025
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.detection import Detection
from app.repositories.base import BaseRepository


class DetectionRepository(BaseRepository[Detection]):
    """
    Detection Repository

    Handles all database operations related to detections. Provides methods for
    querying detections by various criteria such as camera, object class, upload status,
    date ranges, etc.

    Inherits common CRUD operations from BaseRepository and adds detection-specific queries.

    Example:
        detection_repo = DetectionRepository(db)

        # Get detection by ID
        detection = detection_repo.get_by_id(1)

        # Create new detection
        detection = detection_repo.create(
            camera_id=1,
            camera_name="Gate Camera",
            object_track_id="550e8400-e29b-41d4-a716-446655440000",
            object_class="car",
            image_path="/detections/image.jpg"
        )

        # Get failed uploads
        failed = detection_repo.get_failed_uploads()
    """

    def __init__(self, db: Session):
        """
        Initialize the Detection Repository

        Args:
            db: SQLAlchemy database session
        """
        super().__init__(Detection, db)

    def get_by_camera(
        self,
        camera_id: int,
        skip: int = 0,
        limit: int = 50,
        include_inactive: bool = False
    ) -> List[Detection]:
        """
        Get all detections for a specific camera

        Args:
            camera_id: The camera ID
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            include_inactive: Whether to include inactive detections (default: False)

        Returns:
            List of Detection instances ordered by creation time (newest first)
        """
        query = self.db.query(Detection).filter(Detection.camera_id == camera_id)

        if not include_inactive:
            query = query.filter(Detection.is_active == True)  # noqa: E712

        return query.order_by(Detection.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_object_class(
        self,
        object_class: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Detection]:
        """
        Get all detections for a specific object class

        Args:
            object_class: The object class (e.g., "car", "truck", "person")
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of Detection instances
        """
        return self.db.query(Detection).filter(
            Detection.object_class == object_class,
            Detection.is_active == True  # noqa: E712
        ).order_by(Detection.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_track_id(self, track_id: str) -> List[Detection]:
        """
        Get all detections for a specific tracked object

        This returns all the different images captured for the same tracked object.

        Args:
            track_id: The unique object tracking ID (UUID)

        Returns:
            List of Detection instances for the same object
        """
        return self.db.query(Detection).filter(
            Detection.object_track_id == track_id,
            Detection.is_active == True  # noqa: E712
        ).order_by(Detection.created_at.asc()).all()

    def search_by_track_id(self, track_id_pattern: str, limit: int = 10) -> List[Detection]:
        """
        Search detections by track ID pattern (partial match)

        Args:
            track_id_pattern: Pattern to search for (e.g., first 8 characters of UUID)
            limit: Maximum number of results (default: 10)

        Returns:
            List of matching Detection instances
        """
        return self.db.query(Detection).filter(
            Detection.object_track_id.ilike(f"%{track_id_pattern}%"),
            Detection.is_active == True  # noqa: E712
        ).limit(limit).all()

    def get_failed_uploads(self, max_retry_count: Optional[int] = None) -> List[Detection]:
        """
        Get all detections that failed to upload

        Args:
            max_retry_count: Optional maximum retry count filter

        Returns:
            List of Detection instances that haven't been uploaded

        Example:
            # Get all failed uploads
            failed = detection_repo.get_failed_uploads()

            # Get failed uploads with less than 3 retries
            failed = detection_repo.get_failed_uploads(max_retry_count=2)
        """
        query = self.db.query(Detection).filter(
            Detection.uploaded == False,  # noqa: E712
            Detection.is_active == True  # noqa: E712
        )

        if max_retry_count is not None:
            query = query.filter(Detection.upload_retry_count <= max_retry_count)

        return query.order_by(Detection.created_at.desc()).all()

    def get_uploaded_detections(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> List[Detection]:
        """
        Get all successfully uploaded detections

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of Detection instances that have been uploaded
        """
        return self.db.query(Detection).filter(
            Detection.uploaded == True,  # noqa: E712
            Detection.is_active == True  # noqa: E712
        ).order_by(Detection.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        camera_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Detection]:
        """
        Get detections within a date range

        Args:
            start_date: Start of the date range (inclusive)
            end_date: End of the date range (inclusive)
            camera_id: Optional camera ID to filter by
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of Detection instances within the date range
        """
        query = self.db.query(Detection).filter(
            Detection.created_at >= start_date,
            Detection.created_at <= end_date,
            Detection.is_active == True  # noqa: E712
        )

        if camera_id is not None:
            query = query.filter(Detection.camera_id == camera_id)

        return query.order_by(Detection.created_at.desc()).offset(skip).limit(limit).all()

    def filter_detections(
        self,
        camera_id: Optional[int] = None,
        tracker_id: Optional[str] = None,
        object_class: Optional[str] = None,
        activity_type: Optional[str] = None,
        uploaded: Optional[bool] = None,
        min_retry_count: Optional[int] = None,
        max_retry_count: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Detection]:
        """
        Filter detections by multiple criteria

        This is a flexible method that allows combining multiple filters.

        Args:
            camera_id: Filter by camera ID
            tracker_id: Filter by tracker ID (partial match)
            object_class: Filter by object class
            activity_type: Filter by activity type (in/out)
            uploaded: Filter by upload status
            min_retry_count: Filter by minimum retry count
            max_retry_count: Filter by maximum retry count
            start_date: Filter by start date
            end_date: Filter by end date
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of Detection instances matching all provided filters
        """
        query = self.db.query(Detection).filter(Detection.is_active == True)  # noqa: E712

        # Apply filters
        if camera_id is not None:
            query = query.filter(Detection.camera_id == camera_id)

        if tracker_id is not None:
            query = query.filter(Detection.object_track_id.ilike(f"%{tracker_id}%"))

        if object_class is not None:
            query = query.filter(Detection.object_class == object_class)

        if activity_type is not None:
            query = query.filter(Detection.activity_type == activity_type)

        if uploaded is not None:
            query = query.filter(Detection.uploaded == uploaded)

        if min_retry_count is not None:
            query = query.filter(Detection.upload_retry_count >= min_retry_count)

        if max_retry_count is not None:
            query = query.filter(Detection.upload_retry_count <= max_retry_count)

        if start_date is not None:
            query = query.filter(Detection.created_at >= start_date)

        if end_date is not None:
            query = query.filter(Detection.created_at <= end_date)

        return query.order_by(Detection.created_at.desc()).offset(skip).limit(limit).all()

    def count_detections(
        self,
        camera_id: Optional[int] = None,
        tracker_id: Optional[str] = None,
        object_class: Optional[str] = None,
        activity_type: Optional[str] = None,
        uploaded: Optional[bool] = None,
        min_retry_count: Optional[int] = None,
        max_retry_count: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Count detections matching the given filters

        Args:
            camera_id: Filter by camera ID
            tracker_id: Filter by tracker ID (partial match)
            object_class: Filter by object class
            activity_type: Filter by activity type (in/out)
            uploaded: Filter by upload status
            min_retry_count: Filter by minimum retry count
            max_retry_count: Filter by maximum retry count
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Number of detections matching the filters
        """
        query = self.db.query(Detection).filter(Detection.is_active == True)  # noqa: E712

        # Apply same filters as filter_detections
        if camera_id is not None:
            query = query.filter(Detection.camera_id == camera_id)

        if tracker_id is not None:
            query = query.filter(Detection.object_track_id.ilike(f"%{tracker_id}%"))

        if object_class is not None:
            query = query.filter(Detection.object_class == object_class)

        if activity_type is not None:
            query = query.filter(Detection.activity_type == activity_type)

        if uploaded is not None:
            query = query.filter(Detection.uploaded == uploaded)

        if min_retry_count is not None:
            query = query.filter(Detection.upload_retry_count >= min_retry_count)

        if max_retry_count is not None:
            query = query.filter(Detection.upload_retry_count <= max_retry_count)

        if start_date is not None:
            query = query.filter(Detection.created_at >= start_date)

        if end_date is not None:
            query = query.filter(Detection.created_at <= end_date)

        return query.count()

    def mark_as_uploaded(
        self,
        detection_id: int,
        central_detection_id: int
    ) -> Optional[Detection]:
        """
        Mark a detection as successfully uploaded

        Args:
            detection_id: The detection ID
            central_detection_id: The ID assigned by the central server

        Returns:
            Updated Detection instance if found, None otherwise
        """
        detection = self.get_by_id(detection_id)
        if not detection:
            return None

        detection.uploaded = True
        detection.central_detection_id = central_detection_id

        self.db.commit()
        self.db.refresh(detection)
        return detection

    def increment_retry_count(self, detection_id: int) -> Optional[Detection]:
        """
        Increment the upload retry count for a detection

        Args:
            detection_id: The detection ID

        Returns:
            Updated Detection instance if found, None otherwise
        """
        detection = self.get_by_id(detection_id)
        if not detection:
            return None

        detection.upload_retry_count += 1

        self.db.commit()
        self.db.refresh(detection)
        return detection
