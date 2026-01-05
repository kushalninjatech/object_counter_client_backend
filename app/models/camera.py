"""
Camera Model Module

This module defines the Camera database model which represents a physical camera
that monitors a specific area. Each camera has stream details, ROI configuration,
and processing settings.

Author: ANPR Team
Created: 2025
"""

from sqlalchemy import Column, Integer, String, Float, JSON, Index, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.enums import StreamType


class Camera(BaseModel):
    """
    Camera Database Model

    Represents a physical camera that captures video streams and performs object detection.
    Each camera is configured with a stream URL (RTSP, HTTP, IP, etc.), Region of Interest (ROI),
    detection line, and processing parameters.

    The camera processes frames from the video stream, detects objects within the ROI,
    and triggers detection events when objects cross the detection line.

    Attributes:
        id (int): Unique identifier (inherited from BaseModel)
        name (str): Human-readable name for the camera
        stream_url (str): Video stream URL - supports RTSP, HTTP, IP camera, file path, etc.
        stream_type (StreamType): Stream orientation - 'upside-down' or 'downside-up' (default: downside-up)
        roi_polygon (list): List of [x, y] coordinates defining the Region of Interest
        detection_line (list): [x1, y1, x2, y2] coordinates for the detection line
        target_fps (int): Target frames per second for processing (default: 3)
        confidence (float): Detection confidence threshold 0.0-1.0 (default: 0.3)
        organization_id (int): ID of the organization that owns this camera
        is_active (bool): Whether the camera is active (inherited from BaseModel)
        created_at (datetime): When the camera was added (inherited from BaseModel)
        updated_at (datetime): When the camera was last updated (inherited from BaseModel)

    Relationships:
        detections: One-to-many relationship with Detection model

    Example:
        camera = Camera(
            name="Gate Camera 1",
            stream_url="rtsp://admin:pass@192.168.1.100/stream",  # or http://ip/stream or 0 for webcam
            stream_type=StreamType.DOWNSIDE_UP,  # or StreamType.UPSIDE_DOWN
            roi_polygon=[[100, 100], [500, 100], [500, 400], [100, 400]],
            detection_line=[200, 250, 400, 250],
            target_fps=3,
            confidence=0.7,
            organization_id=1
        )
    """

    __tablename__ = "cameras"

    # Camera Identification
    name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Human-readable name for the camera (e.g., 'Main Gate Camera')"
    )

    # Video Stream Configuration
    # Supports multiple stream types:
    # - RTSP: rtsp://user:pass@ip:port/stream
    # - HTTP/HTTPS: http://ip:port/stream
    # - IP Camera: http://ip/video.cgi
    # - Webcam: 0, 1, 2 (device index)
    # - Video File: /path/to/video.mp4
    stream_url = Column(
        String(512),
        nullable=False,
        comment="Video stream URL - supports RTSP, HTTP, IP camera, webcam index, or file path"
    )

    # Stream Orientation Type
    # Defines the orientation of the camera stream
    stream_type = Column(
        Enum(StreamType, values_callable=lambda x: [e.value for e in x]),
        default=StreamType.DOWNSIDE_UP,
        nullable=False,
        comment="Stream orientation: upside-down or downside-up (normal)"
    )

    # Region of Interest (ROI) Configuration
    # ROI defines the area where object detection is performed
    # This saves computational resources by not processing the entire frame
    roi_polygon = Column(
        JSON,
        nullable=False,
        comment="Polygon coordinates [[x1,y1], [x2,y2], ...] defining the detection area"
    )

    # Detection Line Configuration
    # Objects are saved only when they cross this line
    # Format: [x1, y1, x2, y2] - two points defining the line
    detection_line = Column(
        JSON,
        nullable=False,
        comment="Line coordinates [x1, y1, x2, y2] - objects are saved when crossing this line"
    )

    # Processing Settings
    target_fps = Column(
        Integer,
        default=3,
        nullable=False,
        comment="Target FPS for processing (lower = less CPU usage, higher = more detections)"
    )

    # Detection Confidence Threshold
    # Only detections with confidence >= this value are considered
    # Range: 0.0 (accept all) to 1.0 (only very confident detections)
    confidence = Column(
        Float,
        default=0.3,
        nullable=False,
        comment="Minimum confidence threshold (0.0-1.0) for accepting detections"
    )

    # Detection Types (YOLO object classes to detect)
    # Stores list of detection type IDs: 0=person, 2=car, 3=motorcycle, 5=bus, 7=truck
    # Default: [0, 2, 3, 5, 7] (all common vehicle types and person)
    detection_types = Column(
        JSON,
        default=lambda: [0, 2, 3, 5, 7],
        nullable=False,
        comment="List of YOLO class IDs to detect: 0=person, 2=car, 3=motorcycle, 5=bus, 7=truck"
    )

    # Organization/Tenant ID for multi-tenancy support
    organization_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="ID of the organization that owns this camera"
    )

    # Relationships
    # One camera can have many detections
    # cascade="all, delete-orphan" ensures detections are deleted when camera is deleted
    detections = relationship(
        "Detection",
        back_populates="camera",
        cascade="all, delete-orphan",
        lazy="dynamic"  # Use dynamic loading for better performance with large datasets
    )

    # Composite Indexes for optimized queries
    __table_args__ = (
        # Index for queries filtering by organization and active status
        Index('idx_camera_org_active', 'organization_id', 'is_active'),
        # Index for searching cameras by name
        Index('idx_camera_name', 'name'),
    )

    def __repr__(self):
        """
        String representation of the Camera instance

        Returns:
            str: A readable representation showing key camera details
        """
        return f"<Camera(id={self.id}, name='{self.name}', org_id={self.organization_id}, active={self.is_active})>"
