"""
Detection Service Module

This module provides business logic for detection management.
It orchestrates between the detection repository and upload tasks.

Author: ANPR Team
Created: 2025
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.detection import Detection
from app.repositories.detection_repository import DetectionRepository
from app.schemas.detection import DetectionFilter


class DetectionService:
    """
    Detection Service

    Handles business logic for detection operations including creation, queries,
    filtering, and upload management.

    Responsibilities:
        - Create new detections when objects are detected
        - Query and filter detections by various criteria
        - Manage upload status and retry logic
        - Provide detection statistics and analytics

    Example:
        detection_service = DetectionService(db)

        # Create detection
        detection = detection_service.create_detection(
            camera_id=1,
            camera_name="Gate Camera",
            object_track_id="550e8400-...",
            object_class="car",
            image_path="/detections/image.jpg"
        )

        # Get failed uploads
        failed = detection_service.get_failed_uploads()
    """

    def __init__(self, db: Session):
        """
        Initialize the Detection Service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.detection_repo = DetectionRepository(db)

    def get_detection_by_id(self, detection_id: int) -> Detection:
        """
        Get detection by ID

        Args:
            detection_id: The detection ID

        Returns:
            Detection instance

        Raises:
            HTTPException: If detection not found (404)
        """
        detection = self.detection_repo.get_by_id(detection_id)
        if not detection:
            raise HTTPException(
                status_code=404,
                detail=f"Detection with ID {detection_id} not found"
            )
        return detection

    def get_all_detections(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> List[Detection]:
        """
        Get all detections with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Detection instances
        """
        return self.detection_repo.get_all(
            skip=skip,
            limit=limit,
            order_by="created_at",
            desc=True
        )

    def create_detection(
        self,
        camera_id: int,
        camera_name: str,
        object_track_id: str,
        object_class: str,
        image_path: str
    ) -> Detection:
        """
        Create a new detection

        This is called by the worker when an object crosses the detection line.

        Args:
            camera_id: The camera ID
            camera_name: The camera name
            object_track_id: Unique object tracking UUID
            object_class: Object class (car, truck, person, etc.)
            image_path: Path to the saved detection image

        Returns:
            Created Detection instance
        """
        detection = self.detection_repo.create(
            camera_id=camera_id,
            camera_name=camera_name,
            object_track_id=object_track_id,
            object_class=object_class,
            image_path=image_path
        )

        return detection

    def get_detections_by_camera(
        self,
        camera_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Detection]:
        """
        Get all detections for a specific camera

        Args:
            camera_id: The camera ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Detection instances
        """
        return self.detection_repo.get_by_camera(
            camera_id=camera_id,
            skip=skip,
            limit=limit
        )

    def get_detections_by_object_class(
        self,
        object_class: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Detection]:
        """
        Get all detections for a specific object class

        Args:
            object_class: The object class (car, truck, person, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Detection instances
        """
        return self.detection_repo.get_by_object_class(
            object_class=object_class,
            skip=skip,
            limit=limit
        )

    def get_detections_by_track_id(self, track_id: str) -> List[Detection]:
        """
        Get all detections for a specific tracked object

        Returns all images captured for the same object.

        Args:
            track_id: The unique object tracking ID

        Returns:
            List of Detection instances for the same object
        """
        return self.detection_repo.get_by_track_id(track_id)

    def search_detections_by_track_id(
        self,
        track_id_pattern: str,
        limit: int = 10
    ) -> List[Detection]:
        """
        Search detections by partial track ID

        Args:
            track_id_pattern: Partial track ID to search for
            limit: Maximum number of results

        Returns:
            List of matching Detection instances
        """
        return self.detection_repo.search_by_track_id(
            track_id_pattern=track_id_pattern,
            limit=limit
        )

    def get_failed_uploads(
        self,
        max_retry_count: Optional[int] = None
    ) -> List[Detection]:
        """
        Get all detections that failed to upload

        Args:
            max_retry_count: Optional maximum retry count filter

        Returns:
            List of Detection instances that haven't been uploaded
        """
        return self.detection_repo.get_failed_uploads(
            max_retry_count=max_retry_count
        )

    def get_uploaded_detections(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> List[Detection]:
        """
        Get all successfully uploaded detections

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of uploaded Detection instances
        """
        return self.detection_repo.get_uploaded_detections(
            skip=skip,
            limit=limit
        )

    def get_detections_by_date_range(
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
            start_date: Start of the date range
            end_date: End of the date range
            camera_id: Optional camera ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Detection instances within the date range
        """
        return self.detection_repo.get_by_date_range(
            start_date=start_date,
            end_date=end_date,
            camera_id=camera_id,
            skip=skip,
            limit=limit
        )

    def filter_detections(
        self,
        filters: DetectionFilter
    ) -> List[Detection]:
        """
        Filter detections by multiple criteria

        Args:
            filters: DetectionFilter schema with filter criteria

        Returns:
            List of Detection instances matching the filters
        """
        return self.detection_repo.filter_detections(
            camera_id=filters.camera_id,
            tracker_id=filters.tracker_id,
            object_class=filters.object_class,
            activity_type=filters.activity_type,
            uploaded=filters.uploaded,
            min_retry_count=filters.min_retry_count,
            max_retry_count=filters.max_retry_count,
            start_date=filters.start_date,
            end_date=filters.end_date,
            skip=filters.offset,
            limit=filters.limit
        )

    def count_detections(
        self,
        filters: Optional[DetectionFilter] = None
    ) -> int:
        """
        Count detections matching the given filters

        Args:
            filters: Optional DetectionFilter schema with filter criteria

        Returns:
            Number of detections matching the filters
        """
        if filters is None:
            return self.detection_repo.count()

        return self.detection_repo.count_detections(
            camera_id=filters.camera_id,
            tracker_id=filters.tracker_id,
            object_class=filters.object_class,
            activity_type=filters.activity_type,
            uploaded=filters.uploaded,
            min_retry_count=filters.min_retry_count,
            max_retry_count=filters.max_retry_count,
            start_date=filters.start_date,
            end_date=filters.end_date
        )

    def mark_as_uploaded(
        self,
        detection_id: int,
        central_detection_id: int
    ) -> Detection:
        """
        Mark a detection as successfully uploaded

        This is called by the upload task after successful upload to central server.

        Args:
            detection_id: The detection ID
            central_detection_id: The ID assigned by the central server

        Returns:
            Updated Detection instance

        Raises:
            HTTPException: If detection not found (404)
        """
        detection = self.detection_repo.mark_as_uploaded(
            detection_id=detection_id,
            central_detection_id=central_detection_id
        )

        if not detection:
            raise HTTPException(
                status_code=404,
                detail=f"Detection with ID {detection_id} not found"
            )

        return detection

    def increment_retry_count(self, detection_id: int) -> Detection:
        """
        Increment the upload retry count for a detection

        This is called by the upload task when upload fails.

        Args:
            detection_id: The detection ID

        Returns:
            Updated Detection instance

        Raises:
            HTTPException: If detection not found (404)
        """
        detection = self.detection_repo.increment_retry_count(detection_id)

        if not detection:
            raise HTTPException(
                status_code=404,
                detail=f"Detection with ID {detection_id} not found"
            )

        return detection

    def get_detection_statistics(self) -> Dict[str, Any]:
        """
        Get overall detection statistics

        Returns:
            Dictionary with detection statistics including:
            - Total detections
            - IN/OUT detection counts
            - Uploaded count
            - Failed uploads count
            - Average retry count for failed uploads
            - By camera breakdown
            - By object class breakdown
        """
        from sqlalchemy import func
        from app.models.detection import Detection

        total_count = self.detection_repo.count()
        uploaded_count = self.detection_repo.count_detections(uploaded=True)
        failed_count = self.detection_repo.count_detections(uploaded=False)

        # Count IN and OUT detections
        in_count = self.db.query(func.count(Detection.id)).filter(
            Detection.is_active == True,  # noqa: E712
            Detection.activity_type == 'in'
        ).scalar() or 0

        out_count = self.db.query(func.count(Detection.id)).filter(
            Detection.is_active == True,  # noqa: E712
            Detection.activity_type == 'out'
        ).scalar() or 0

        # Get failed uploads to calculate average retry count
        failed_uploads = self.detection_repo.get_failed_uploads()
        avg_retry_count = (
            sum(d.upload_retry_count for d in failed_uploads) / len(failed_uploads)
            if failed_uploads else 0
        )

        # Get by-camera breakdown
        by_camera = self.db.query(
            Detection.camera_id,
            Detection.camera_name,
            func.count(Detection.id).label('count')
        ).filter(
            Detection.is_active == True  # noqa: E712
        ).group_by(
            Detection.camera_id,
            Detection.camera_name
        ).all()

        # Get by-class breakdown
        by_class = self.db.query(
            Detection.object_class,
            func.count(Detection.id).label('count')
        ).filter(
            Detection.is_active == True  # noqa: E712
        ).group_by(
            Detection.object_class
        ).all()

        return {
            "total_detections": total_count,
            "in_count": in_count,
            "out_count": out_count,
            "uploaded_count": uploaded_count,
            "pending_count": total_count - uploaded_count - failed_count,
            "failed_count": failed_count,
            "upload_success_rate": (
                (uploaded_count / total_count * 100) if total_count > 0 else 0
            ),
            "average_retry_count": round(avg_retry_count, 2),
            "by_camera": [
                {
                    "camera_id": cam_id,
                    "camera_name": cam_name,
                    "count": count
                }
                for cam_id, cam_name, count in by_camera
            ],
            "by_class": [
                {
                    "object_class": obj_class or "unknown",
                    "count": count
                }
                for obj_class, count in by_class
            ]
        }

    def get_detection_statistics_by_camera(
        self,
        camera_id: int
    ) -> Dict[str, Any]:
        """
        Get detection statistics for a specific camera

        Args:
            camera_id: The camera ID

        Returns:
            Dictionary with camera-specific detection statistics
        """
        total_count = self.detection_repo.count_detections(camera_id=camera_id)
        uploaded_count = self.detection_repo.count_detections(
            camera_id=camera_id,
            uploaded=True
        )
        failed_count = self.detection_repo.count_detections(
            camera_id=camera_id,
            uploaded=False
        )

        return {
            "camera_id": camera_id,
            "total_detections": total_count,
            "uploaded": uploaded_count,
            "failed_uploads": failed_count,
            "upload_success_rate": (
                (uploaded_count / total_count * 100) if total_count > 0 else 0
            )
        }

    def get_detection_statistics_by_object_class(self) -> List[Dict[str, Any]]:
        """
        Get detection statistics grouped by object class with IN/OUT breakdown

        Returns:
            List of dictionaries with statistics for each object class including IN/OUT counts,
            current occupancy, capacity, and remaining occupancy
        """
        from sqlalchemy import func, case
        from app.models.detection import Detection
        from app.core.config import settings

        # Get counts grouped by object class and activity type
        results = self.db.query(
            Detection.object_class,
            func.count(Detection.id).label('total_count'),
            func.sum(case((Detection.activity_type == 'in', 1), else_=0)).label('in_count'),
            func.sum(case((Detection.activity_type == 'out', 1), else_=0)).label('out_count')
        ).filter(
            Detection.is_active == True  # noqa: E712
        ).group_by(
            Detection.object_class
        ).all()

        statistics = []
        for object_class, total_count, in_count, out_count in results:
            uploaded_count = self.detection_repo.count_detections(
                object_class=object_class,
                uploaded=True
            )

            # Calculate current occupancy (IN - OUT)
            in_cnt = int(in_count or 0)
            out_cnt = int(out_count or 0)
            current_occupancy = in_cnt - out_cnt

            # Get capacity for this object type
            obj_class_name = object_class or "unknown"
            capacity = settings.OBJECT_CAPACITIES.get(obj_class_name, 5000)

            # Calculate remaining occupancy
            # If current occupancy is negative, show full capacity as remaining
            if current_occupancy < 0:
                remaining_occupancy = capacity
            else:
                remaining_occupancy = capacity - current_occupancy

            statistics.append({
                "object_class": obj_class_name,
                "total_detections": total_count,
                "in_count": in_cnt,
                "out_count": out_cnt,
                "current_occupancy": current_occupancy,
                "capacity": capacity,
                "remaining_occupancy": remaining_occupancy,
                "uploaded": uploaded_count,
                "failed_uploads": total_count - uploaded_count
            })

        return sorted(statistics, key=lambda x: x["total_detections"], reverse=True)
