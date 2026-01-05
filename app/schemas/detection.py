"""Detection Pydantic schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.enums import ActivityType


class DetectionBase(BaseModel):
    """Base detection schema"""
    camera_id: int = Field(..., ge=1, description="Camera ID")
    camera_name: str = Field(..., max_length=255, description="Camera name")
    object_track_id: str = Field(..., max_length=100, description="Unique object tracking ID")
    object_class: Optional[str] = Field(None, max_length=50, description="Object class (car, truck, person, etc.)")
    activity_type: Optional[ActivityType] = Field(None, description="Detection direction: 'in' or 'out'")
    detected_at: datetime = Field(..., description="Detection timestamp (UTC)")


class DetectionCreate(BaseModel):
    """Schema for creating a new detection"""
    camera_id: int = Field(..., ge=1, description="Camera ID")
    camera_name: str = Field(..., max_length=255, description="Camera name")
    object_track_id: str = Field(..., max_length=100, description="Unique object tracking ID")
    object_class: Optional[str] = Field(None, max_length=50, description="Object class (car, truck, person, etc.)")
    activity_type: Optional[ActivityType] = Field(None, description="Detection direction: 'in' or 'out'")
    image_path: str = Field(..., max_length=512, description="Path to detection image")


class DetectionInDB(DetectionBase):
    """Schema for detection stored in database"""
    id: int
    uploaded: bool
    upload_retry_count: int
    central_detection_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class DetectionResponse(DetectionInDB):
    """Schema for detection API response"""
    image_url: str = Field(..., description="URL to access the detection image")

    class Config:
        from_attributes = True


class DetectionFilter(BaseModel):
    """Schema for filtering detections"""
    camera_id: Optional[int] = Field(None, description="Filter by camera ID")
    tracker_id: Optional[str] = Field(None, description="Filter by object tracker ID (partial match)")
    object_class: Optional[str] = Field(None, description="Filter by object class")
    activity_type: Optional[ActivityType] = Field(None, description="Filter by activity direction")
    uploaded: Optional[bool] = Field(None, description="Filter by upload status")
    min_retry_count: Optional[int] = Field(None, ge=0, description="Minimum retry count")
    max_retry_count: Optional[int] = Field(None, ge=0, description="Maximum retry count")
    start_date: Optional[datetime] = Field(None, description="Filter detections from this date/time")
    end_date: Optional[datetime] = Field(None, description="Filter detections until this date/time")
    limit: int = Field(50, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")
