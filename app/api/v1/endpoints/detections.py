"""
Detection API Endpoints

This module provides REST API endpoints for querying detections with
advanced filtering, statistics, and analytics.

Author: ANPR Team
Created: 2025
"""

from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from app.core.dependencies import get_db
from app.core.config import settings
from app.services.detection_service import DetectionService
from app.schemas.detection import DetectionResponse, DetectionFilter
from app.repositories.detection_repository import DetectionRepository

# Create router for detection endpoints
router = APIRouter(prefix="/detections", tags=["detections"])


@router.get("", response_model=List[DetectionResponse])
def list_detections(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all detections with pagination"""
    detection_service = DetectionService(db)
    detections = detection_service.get_all_detections(skip, limit)
    return [DetectionResponse.model_validate(d) for d in detections]


@router.get("/{detection_id}", response_model=DetectionResponse)
def get_detection(detection_id: int, db: Session = Depends(get_db)):
    """Get detection by ID"""
    detection_service = DetectionService(db)
    detection = detection_service.get_detection_by_id(detection_id)
    return DetectionResponse.model_validate(detection)


@router.get("/camera/{camera_id}", response_model=List[DetectionResponse])
def get_detections_by_camera(
    camera_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all detections for a specific camera"""
    detection_service = DetectionService(db)
    detections = detection_service.get_detections_by_camera(camera_id, skip, limit)
    return [DetectionResponse.model_validate(d) for d in detections]


@router.get("/object-class/{object_class}", response_model=List[DetectionResponse])
def get_detections_by_class(
    object_class: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all detections for a specific object class (car, truck, person, etc.)"""
    detection_service = DetectionService(db)
    detections = detection_service.get_detections_by_object_class(object_class, skip, limit)
    return [DetectionResponse.model_validate(d) for d in detections]


@router.get("/track/{track_id}", response_model=List[DetectionResponse])
def get_detections_by_track(track_id: str, db: Session = Depends(get_db)):
    """Get all detections for a specific tracked object (all images of same object)"""
    detection_service = DetectionService(db)
    detections = detection_service.get_detections_by_track_id(track_id)
    return [DetectionResponse.model_validate(d) for d in detections]


@router.get("/failed-uploads", response_model=List[DetectionResponse])
def get_failed_uploads(
    max_retry_count: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db)
):
    """Get all detections that failed to upload"""
    detection_service = DetectionService(db)
    detections = detection_service.get_failed_uploads(max_retry_count)
    return [DetectionResponse.model_validate(d) for d in detections]


@router.get("/uploaded", response_model=List[DetectionResponse])
def get_uploaded_detections(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all successfully uploaded detections"""
    detection_service = DetectionService(db)
    detections = detection_service.get_uploaded_detections(skip, limit)
    return [DetectionResponse.model_validate(d) for d in detections]


@router.post("/filter", response_model=List[DetectionResponse])
def filter_detections(filters: DetectionFilter, db: Session = Depends(get_db)):
    """
    Filter detections by multiple criteria

    Supports filtering by:
    - camera_id
    - tracker_id (partial match)
    - object_class
    - uploaded status
    - retry count range
    - date range
    """
    detection_service = DetectionService(db)
    detections = detection_service.filter_detections(filters)
    return [DetectionResponse.model_validate(d) for d in detections]


@router.post("/count", response_model=dict)
def count_detections(filters: Optional[DetectionFilter] = None, db: Session = Depends(get_db)):
    """Count detections matching filters"""
    detection_service = DetectionService(db)
    count = detection_service.count_detections(filters)
    return {"total": count}


@router.get("/statistics/overview", response_model=dict)
def get_detection_statistics(db: Session = Depends(get_db)):
    """Get overall detection statistics"""
    detection_service = DetectionService(db)
    return detection_service.get_detection_statistics()


@router.get("/statistics/by-camera/{camera_id}", response_model=dict)
def get_camera_detection_statistics(camera_id: int, db: Session = Depends(get_db)):
    """Get detection statistics for a specific camera"""
    detection_service = DetectionService(db)
    return detection_service.get_detection_statistics_by_camera(camera_id)


@router.get("/statistics/by-object-class", response_model=List[dict])
def get_detection_statistics_by_class(db: Session = Depends(get_db)):
    """Get detection statistics grouped by object class"""
    detection_service = DetectionService(db)
    return detection_service.get_detection_statistics_by_object_class()


@router.get("/search/track-id", response_model=List[DetectionResponse])
def search_by_track_id(
    track_id: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search detections by partial track ID"""
    detection_service = DetectionService(db)
    detections = detection_service.search_detections_by_track_id(track_id, limit)
    return [DetectionResponse.model_validate(d) for d in detections]


@router.get("/export/csv")
def export_detections_csv(
    from_datetime: Optional[str] = Query(None, description="Start date and time (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    to_datetime: Optional[str] = Query(None, description="End date and time (ISO format: YYYY-MM-DDTHH:MM:SS)"),
    camera_id: Optional[int] = Query(None, description="Filter by camera ID"),
    object_class: Optional[str] = Query(None, description="Filter by object class (e.g., car, person)"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (in/out)"),
    db: Session = Depends(get_db)
):
    """
    Export detections to Excel file based on date/time range and filters

    **Query Parameters:**
    - `from_datetime`: Start date/time in ISO format (e.g., 2026-01-01T00:00:00)
    - `to_datetime`: End date/time in ISO format (e.g., 2026-01-31T23:59:59)
    - `camera_id`: Optional camera ID filter
    - `object_class`: Optional object class filter
    - `activity_type`: Optional activity type filter (in/out)

    **Returns:**
    - Excel file download with detection data in "Detection details" sheet

    **Example:**
    ```
    GET /detections/export/csv?from_datetime=2026-01-01T00:00:00&to_datetime=2026-01-02T23:59:59
    ```
    """
    detection_repo = DetectionRepository(db)

    # Parse datetime strings
    start_date = None
    end_date = None

    if from_datetime:
        try:
            start_date = datetime.fromisoformat(from_datetime)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid from_datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
            )

    if to_datetime:
        try:
            end_date = datetime.fromisoformat(to_datetime)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid to_datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS"
            )

    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="from_datetime must be before to_datetime"
        )

    # Fetch detections with filters
    detections = detection_repo.filter_detections(
        camera_id=camera_id,
        object_class=object_class,
        start_date=start_date,
        end_date=end_date,
        limit=100000  # Large limit for export
    )

    # Filter by activity_type if provided (not in repository method)
    if activity_type:
        detections = [d for d in detections if d.activity_type == activity_type]

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Detection details"  # Sheet name

    # Write header with styling
    headers = ['Date', 'Time', 'Camera ID', 'Camera Name', 'Object Class', 'Activity Type']
    ws.append(headers)

    # Style header row
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    # Write data rows
    for detection in detections:
        # Convert UTC to IST (UTC+5:30) for display
        date_str = 'N/A'
        time_str = 'N/A'
        if detection.detected_at:
            detected_at_ist = detection.detected_at + timedelta(hours=5, minutes=30)
            date_str = detected_at_ist.strftime('%d/%m/%Y')  # 02/01/2026
            time_str = detected_at_ist.strftime('%H:%M')     # 09:54 (without seconds)

        # Format activity type to show only the value (IN/OUT)
        activity_str = 'N/A'
        if detection.activity_type:
            activity_str = detection.activity_type.upper() if isinstance(detection.activity_type, str) else str(detection.activity_type.value).upper()

        ws.append([
            date_str,
            time_str,
            detection.camera_id,
            detection.camera_name,
            detection.object_class or 'N/A',
            activity_str
        ])

    # Adjust column widths
    ws.column_dimensions['A'].width = 12  # Date
    ws.column_dimensions['B'].width = 8   # Time
    ws.column_dimensions['C'].width = 10  # Camera ID
    ws.column_dimensions['D'].width = 20  # Camera Name
    ws.column_dimensions['E'].width = 15  # Object Class
    ws.column_dimensions['F'].width = 15  # Activity Type

    # Generate filename with current date and time
    now = datetime.now()
    timestamp = now.strftime('%d-%m-%Y-%H-%M-%S')
    filename = f"detection-{timestamp}.xlsx"

    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    # Return Excel file as downloadable
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
