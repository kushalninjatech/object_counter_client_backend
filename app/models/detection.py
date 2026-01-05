"""
Detection Model Module

This module defines the Detection database model which represents a detected object
(vehicle, person, etc.) captured by a camera. Each detection includes the object's
tracking ID, class, image path, and upload status to the central server.

Author: ANPR Team
Created: 2025
"""

from sqlalchemy import Column, Integer, String, Boolean, Index, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.enums import ActivityType


class Detection(BaseModel):
    """
    Detection Database Model

    Represents a single object detection event captured by a camera. When an object
    (vehicle, person, etc.) crosses the detection line within the ROI, a detection
    record is created with an image and metadata.

    The detection includes:
    - Object tracking information (unique ID and class)
    - Reference to the camera that made the detection
    - Image file path
    - Upload status to central server (with retry tracking)

    Note: We use created_at (from BaseModel) as the detection timestamp.

    Attributes:
        id (int): Unique identifier (inherited from BaseModel)
        camera_id (int): Foreign key reference to the camera
        camera_name (str): Name of the camera (denormalized for performance)
        object_track_id (str): Unique UUID for tracking the same object across frames
        object_class (str): Class of detected object (car, truck, person, etc.)
        image_path (str): File system path to the saved detection image
        uploaded (bool): Whether the detection has been uploaded to central server
        upload_retry_count (int): Number of upload retry attempts made
        central_detection_id (int): ID assigned by central server after successful upload
        is_active (bool): Whether the record is active (inherited from BaseModel)
        created_at (datetime): When the detection occurred (inherited from BaseModel)
        updated_at (datetime): When the record was last updated (inherited from BaseModel)

    Relationships:
        camera: Many-to-one relationship with Camera model

    Example:
        detection = Detection(
            camera_id=1,
            camera_name="Gate Camera 1",
            object_track_id="550e8400-e29b-41d4-a716-446655440000",
            object_class="car",
            image_path="office/2026/01/02/12-00-00_550e8400-e29b-41d4-a716-446655440000_in.jpg"
        )
    """

    __tablename__ = "detections"

    # Camera Reference
    # Foreign key with CASCADE delete - if camera is deleted, its detections are also deleted
    camera_id = Column(
        Integer,
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the camera that made this detection"
    )

    # Denormalized camera name for faster queries without joins
    # This trades storage space for query performance
    camera_name = Column(
        String(255),
        nullable=False,
        comment="Name of the camera (denormalized for performance)"
    )

    # Object Tracking Information
    # UUID that uniquely identifies this object across multiple frames
    # Same object detected in multiple frames will have the same track_id
    object_track_id = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Unique UUID for tracking the same object across frames"
    )

    # Object Classification
    # The type of object detected (e.g., car, truck, bus, motorcycle, person)
    # Based on COCO dataset classes
    object_class = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Type of detected object (car, truck, bus, motorcycle, person, etc.)"
    )

    # Activity Direction
    # Direction of movement when crossing the detection line: "in" or "out"
    activity_type = Column(
        Enum(ActivityType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True,
        comment="Detection direction: 'in' or 'out'"
    )

    # Image Storage
    # Relative path from detections directory to the saved detection image
    # Format: {camera_name}/{YYYY}/{MM}/{DD}/{HH-MM-SS}_{uuid}_{direction}.jpg
    # Example: office/2026/01/02/09-49-19_12345678-abcd-1234-abcd-123456789012_in.jpg
    image_path = Column(
        String(512),
        nullable=False,
        comment="Relative path to the detection image (from detections dir)"
    )

    # Upload Status to Central Server
    # Whether this detection has been successfully uploaded
    uploaded = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether the detection has been uploaded to central server"
    )

    # Upload Retry Tracking
    # Number of times we've attempted to upload this detection
    # Used for progressive backoff and giving up after max retries
    upload_retry_count = Column(
        Integer,
        default=0,
        nullable=False,
        index=True,
        comment="Number of upload retry attempts (for failed uploads)"
    )

    # Central Server Reference
    # ID assigned by the central server after successful upload
    # NULL until the detection is successfully uploaded
    central_detection_id = Column(
        Integer,
        nullable=True,
        comment="Detection ID from central server (NULL until uploaded)"
    )

    # Relationships
    # Many detections belong to one camera
    camera = relationship(
        "Camera",
        back_populates="detections"
    )

    @property
    def detected_at(self):
        """Alias for created_at - when the detection occurred"""
        return self.created_at

    @property
    def image_url(self):
        """URL to access the detection image via static files"""
        # Return URL with full path structure
        # Format: "camera_name/year/month/day/time_uuid_direction.jpg"
        # Example: "/detections/office/2026/01/02/12-00-00_uuid_in.jpg"
        return f"/detections/{self.image_path}"

    # Composite Indexes for Optimized Queries
    # These indexes improve performance for common query patterns
    __table_args__ = (
        # For queries like "get detections for camera X ordered by time"
        # Note: created_at index already exists in BaseModel
        Index('idx_detection_camera_created', 'camera_id', 'created_at'),

        # For queries like "find failed uploads that need retry"
        Index('idx_detection_uploaded_retry', 'uploaded', 'upload_retry_count'),

        # For queries like "find all detections for a specific tracked object"
        Index('idx_detection_track_camera', 'object_track_id', 'camera_id'),

        # For queries like "find all car detections in last 24 hours"
        Index('idx_detection_class_created', 'object_class', 'created_at'),
    )

    def __repr__(self):
        """
        String representation of the Detection instance

        Returns:
            str: A readable representation showing key detection details
        """
        track_id_short = self.object_track_id[:8] if self.object_track_id else 'None'
        return (f"<Detection(id={self.id}, camera_id={self.camera_id}, "
                f"class='{self.object_class}', track_id='{track_id_short}...', "
                f"uploaded={self.uploaded})>")
