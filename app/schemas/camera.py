"""Camera Pydantic schemas"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.models.enums import StreamType, DetectionType
from enum import Enum

class CameraBase(BaseModel):
    """Base camera schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Camera name")
    stream_url: str = Field(..., min_length=1, max_length=512, description="Video stream URL (RTSP, HTTP, IP camera, etc.)")
    stream_type: StreamType = Field(default=StreamType.DOWNSIDE_UP, description="Stream orientation: upside-down or downside-up")
    roi_polygon: List[List[int]] = Field(..., description="Region of Interest polygon coordinates")
    detection_line: List[int] = Field(..., min_length=4, max_length=4, description="Detection line coordinates [x1, y1, x2, y2]")
    target_fps: int = Field(default=3, ge=1, le=30, description="Target FPS for processing")
    confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="Detection confidence threshold")
    detection_types: List[int] = Field(default=[0, 2, 3, 5, 7], description="List of YOLO class IDs to detect (0=person, 2=car, 3=motorcycle, 5=bus, 7=truck)")
    organization_id: int = Field(default=1, ge=1, description="Organization ID")

    @field_validator("roi_polygon")
    @classmethod
    def validate_roi_polygon(cls, v):
        """Validate ROI polygon has at least 3 points"""
        if len(v) < 3:
            raise ValueError("ROI polygon must have at least 3 points")
        for point in v:
            if len(point) != 2:
                raise ValueError("Each point must have exactly 2 coordinates [x, y]")
        return v

    @field_validator("detection_types")
    @classmethod
    def validate_detection_types(cls, v):
        """Validate detection types are valid YOLO class IDs"""
        if not v:
            raise ValueError("At least one detection type must be selected")
        valid_types = [dt.value for dt in DetectionType]
        for dt in v:
            if dt not in valid_types:
                raise ValueError(f"Invalid detection type: {dt}. Valid types: {valid_types}")
        return v


class CameraCreate(CameraBase):
    """Schema for creating a new camera"""
    pass


class CameraUpdate(BaseModel):
    """Schema for updating camera details"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    stream_url: Optional[str] = Field(None, min_length=1, max_length=512)
    stream_type: Optional[StreamType] = None
    roi_polygon: Optional[List[List[int]]] = None
    detection_line: Optional[List[int]] = Field(None, min_length=4, max_length=4)
    target_fps: Optional[int] = Field(None, ge=1, le=30)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    detection_types: Optional[List[int]] = None
    is_active: Optional[bool] = None

    @field_validator("roi_polygon")
    @classmethod
    def validate_roi_polygon(cls, v):
        """Validate ROI polygon if provided"""
        if v is not None:
            if len(v) < 3:
                raise ValueError("ROI polygon must have at least 3 points")
            for point in v:
                if len(point) != 2:
                    raise ValueError("Each point must have exactly 2 coordinates [x, y]")
        return v

    @field_validator("detection_types")
    @classmethod
    def validate_detection_types(cls, v):
        """Validate detection types if provided"""
        if v is not None:
            if not v:
                raise ValueError("At least one detection type must be selected")
            valid_types = [dt.value for dt in DetectionType]
            for dt in v:
                if dt not in valid_types:
                    raise ValueError(f"Invalid detection type: {dt}. Valid types: {valid_types}")
        return v


class CameraInDB(CameraBase):
    """Schema for camera stored in database"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CameraResponse(CameraInDB):
    """
    Schema for camera API response with worker status

    Note: worker_running must be set manually when creating response,
    as it's not a database field
    """
    worker_running: bool = Field(default=False, description="Whether worker is currently running")

    class Config:
        from_attributes = True


class WorkerControl(BaseModel):
    """Schema for controlling worker"""
    action: str = Field(..., pattern="^(start|stop)$", description="Action to perform: start or stop")




class StreamAction(str, Enum):
    """Enum for stream control actions"""
    start = "start"
    stop = "stop"