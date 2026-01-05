"""
Camera API Endpoints

This module provides REST API endpoints for camera management including
CRUD operations, statistics, and frame capture.

Author: ANPR Team
Created: 2025
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import cv2
import io
import os

from app.core.dependencies import get_db
from app.services.camera_service import CameraService
from app.services.worker_service import WorkerService
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse,StreamAction
from app.services.stream_service import StreamService
# Create router for camera endpoints
router = APIRouter(prefix="/cameras", tags=["cameras"])


def _to_response(camera, worker_service: WorkerService) -> CameraResponse:
    """Build CameraResponse from model with worker status"""
    response = CameraResponse.model_validate(camera)
    response.worker_running = worker_service.is_worker_running(camera.id)
    return response


@router.get("", response_model=List[CameraResponse])
def list_cameras(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    active_only: bool = Query(True, description="Return only active cameras"),
    db: Session = Depends(get_db)
):
    """
    Get all cameras

    Returns list of all cameras with their worker status.

    **Query Parameters:**
    - `skip`: Pagination offset
    - `limit`: Max results per page
    - `active_only`: Filter for active cameras only

    **Returns:**
    - List of cameras with worker_running status
    """
    camera_service = CameraService(db)
    worker_service = WorkerService(db)
    cameras = camera_service.get_all_cameras(skip, limit, active_only)
    return [_to_response(cam, worker_service) for cam in cameras]


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """
    Get camera by ID

    **Path Parameters:**
    - `camera_id`: Camera ID

    **Returns:**
    - Camera details with worker status

    **Raises:**
    - `404`: Camera not found
    """
    camera_service = CameraService(db)
    worker_service = WorkerService(db)
    camera = camera_service.get_camera_by_id(camera_id)
    return _to_response(camera, worker_service)


@router.post("", response_model=dict, status_code=201)
def create_camera(
    camera_data: CameraCreate,
    db: Session = Depends(get_db)
):
    """
    Create new camera

    **Request Body:**
    - `name`: Camera name (required)
    - `stream_url`: Video stream URL - RTSP, HTTP, IP camera, etc. (required)
    - `roi_polygon`: ROI polygon coordinates [[x1,y1], [x2,y2], ...] (required)
    - `detection_line`: Detection line [x1, y1, x2, y2] (required)
    - `target_fps`: Target FPS for processing (default: 3)
    - `confidence`: Confidence threshold 0.0-1.0 (default: 0.3)
    - `organization_id`: Organization ID (default: 1)

    **Returns:**
    - Camera ID and success message

    **Raises:**
    - `400`: Invalid data or duplicate camera name
    """
    camera_service = CameraService(db)
    camera = camera_service.create_camera(**camera_data.model_dump())
    return {
        "id": camera.id,
        "message": f"Camera '{camera.name}' created successfully"
    }


@router.put("/{camera_id}", response_model=dict)
def update_camera(
    camera_id: int,
    camera_data: CameraUpdate,
    db: Session = Depends(get_db)
):
    """
    Update camera details

    **Note:** If worker is running, it will be stopped before update.
    You must restart the worker manually to apply new settings.

    **Path Parameters:**
    - `camera_id`: Camera ID

    **Request Body (all optional):**
    - `name`: New camera name
    - `stream_url`: New stream URL
    - `roi_polygon`: New ROI polygon
    - `detection_line`: New detection line
    - `target_fps`: New target FPS
    - `confidence`: New confidence threshold
    - `is_active`: Active status

    **Returns:**
    - Success message and camera ID

    **Raises:**
    - `404`: Camera not found
    - `400`: Invalid data or duplicate name
    """
    from threading import Thread

    camera_service = CameraService(db)
    worker_service = WorkerService(db)

    # Stop worker if running (non-blocking)
    worker_was_running = worker_service.is_worker_running(camera_id)
    if worker_was_running:
        # Stop worker in background thread to avoid blocking
        def stop_worker_async():
            try:
                worker_service.stop_worker(camera_id)
            except Exception as e:
                print(f"Error stopping worker for camera {camera_id}: {e}")

        thread = Thread(target=stop_worker_async, daemon=True)
        thread.start()
        # No need to wait - worker will cleanup gracefully on its own

    # Update camera
    update_data = camera_data.model_dump(exclude_unset=True)
    updated_camera = camera_service.update_camera(camera_id, **update_data)

    message = f"Camera '{updated_camera.name}' updated successfully"
    if worker_was_running:
        message += " (worker stopping in background, restart manually to apply changes)"

    return {
        "id": updated_camera.id,
        "message": message,
        "worker_was_running": worker_was_running
    }


@router.delete("/{camera_id}", response_model=dict)
def delete_camera(
    camera_id: int,
    soft_delete: bool = Query(True, description="Soft delete (deactivate) vs hard delete"),
    db: Session = Depends(get_db)
):
    """
    Delete camera

    **Note:** Worker will be stopped before deletion if running.

    **Path Parameters:**
    - `camera_id`: Camera ID

    **Query Parameters:**
    - `soft_delete`: If True (default), marks camera as inactive. If False, permanently deletes.

    **Returns:**
    - Success message

    **Raises:**
    - `404`: Camera not found
    """
    camera_service = CameraService(db)
    worker_service = WorkerService(db)

    # Stop worker if running
    if worker_service.is_worker_running(camera_id):
        worker_service.stop_worker(camera_id)

    # Delete camera
    return camera_service.delete_camera(camera_id, soft_delete)


@router.get("/{camera_id}/statistics", response_model=dict)
def get_camera_statistics(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """
    Get camera statistics

    **Path Parameters:**
    - `camera_id`: Camera ID

    **Returns:**
    - Camera statistics including:
        - Total detection count
        - Worker running status
        - Camera metadata

    **Raises:**
    - `404`: Camera not found
    """
    camera_service = CameraService(db)
    worker_service = WorkerService(db)

    stats = camera_service.get_camera_statistics(camera_id)
    stats["worker_running"] = worker_service.is_worker_running(camera_id)

    return stats


@router.get("/{camera_id}/frame")
def get_camera_frame(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """
    Get single frame from camera stream

    Captures and returns a single frame from the camera's video stream.
    Useful for previewing the stream or configuring ROI/detection line.

    **Path Parameters:**
    - `camera_id`: Camera ID

    **Returns:**
    - JPEG image stream

    **Raises:**
    - `404`: Camera not found
    - `500`: Cannot open stream or capture frame
    """
    camera_service = CameraService(db)
    camera = camera_service.get_camera_by_id(camera_id)

    # Use TCP for single frame capture (more reliable than UDP)
    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'

    cap = cv2.VideoCapture(camera.stream_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)  # 15s timeout
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 15000)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        raise HTTPException(
            status_code=500,
            detail=f"Cannot open video stream: {camera.stream_url}"
        )

    try:
        # Try reading frame multiple times (first frame sometimes fails)
        frame = None
        for attempt in range(3):
            ret, frame = cap.read()
            if ret and frame is not None:
                break

        if not ret or frame is None:
            raise HTTPException(
                status_code=500,
                detail="Cannot read frame from stream after 3 attempts"
            )

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            raise HTTPException(status_code=500, detail="Cannot encode frame as JPEG")

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(buffer.tobytes()),
            media_type="image/jpeg"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error capturing frame: {str(e)}"
        )
    finally:
        cap.release()


@router.get("/search/by-name", response_model=List[CameraResponse])
def search_cameras(
    name: str = Query(..., min_length=1, description="Search pattern (case-insensitive)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Search cameras by name

    Performs case-insensitive partial match search on camera names.

    **Query Parameters:**
    - `name`: Search pattern
    - `limit`: Maximum number of results

    **Returns:**
    - List of matching cameras with worker status
    """
    camera_service = CameraService(db)
    worker_service = WorkerService(db)

    cameras = camera_service.search_cameras(name, limit)
    return [_to_response(cam, worker_service) for cam in cameras]


@router.post("/{camera_id}/stream/{action}", response_model=dict)
def control_stream(
    camera_id: int,
    action: StreamAction,
    target_fps: int = Query(30, ge=5, le=30, description="Target FPS for streaming"),
    db: Session = Depends(get_db)
):
    """
    Start or stop video stream for a camera

    **Path Parameters:**
    - `camera_id`: Camera ID
    - `action`: Action to perform (start or stop)

    **Query Parameters:**
    - `target_fps`: Target frame rate for streaming (5-30 FPS, default: 30)

    **Returns:**
    - Success message and stream status

    **Raises:**
    - `404`: Camera not found
    - `400`: Invalid action or stream state

    **Example Usage:**
    ```
    # Start stream
    POST /api/v1/cameras/1/stream/start?target_fps=20

    # Stop stream
    POST /api/v1/cameras/1/stream/stop
    ```

    **Notes:**
    - Stream runs independently from detection worker
    - Only one stream per camera allowed
    - Stream automatically reconnects on connection loss
    - Uses MJPEG format (browser-compatible)
    """
    stream_service = StreamService(db)

    if action == StreamAction.start:
        result = stream_service.start_stream(camera_id, target_fps)
    else:
        result = stream_service.stop_stream(camera_id)

    return result


@router.get("/{camera_id}/stream")
async def video_stream(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """
    Get live MJPEG video stream from camera

    Returns a continuous stream of JPEG frames in MJPEG format.
    Can be displayed directly in HTML using <img> tag.

    **Path Parameters:**
    - `camera_id`: Camera ID

    **Returns:**
    - MJPEG video stream (multipart/x-mixed-replace)

    **Raises:**
    - `404`: Camera not found
    - `503`: Stream not active (start it first)

    **Example Usage:**
    ```html
    <!-- Display in browser -->
    <img src="http://localhost:8000/api/v1/cameras/1/stream" />
    ```

    ```python
    # Start stream first
    POST /api/v1/cameras/1/stream/start

    # Then access video feed
    GET /api/v1/cameras/1/stream
    ```

    **Notes:**
    - Stream must be started first using POST /{camera_id}/stream/start
    - Returns MJPEG format (Motion JPEG)
    - Works directly in <img> tags, no JavaScript needed
    - Stream continues until explicitly stopped or app shutdown
    """
    stream_service = StreamService(db)

    # Check if camera exists
    camera_service = CameraService(db)
    camera = camera_service.get_camera_by_id(camera_id)

    # Check if stream is active
    if not stream_service.is_stream_active(camera_id):
        raise HTTPException(
            status_code=503,
            detail=f"Stream not active for camera '{camera.name}'. "
                   f"Start it first using POST /cameras/{camera_id}/stream/start"
        )

    # Return streaming response
    return StreamingResponse(
        stream_service.generate_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/streams/status", response_model=dict)
def get_all_streams_status(db: Session = Depends(get_db)):
    """
    Get status of all active streams

    Returns information about all currently active video streams.

    **Returns:**
    - Dictionary with:
        - `total_streams`: Number of active streams
        - `active_streams`: List of stream details

    **Example Response:**
    ```json
    {
        "total_streams": 2,
        "active_streams": [
            {
                "camera_id": 1,
                "stream_active": true,
                "has_frames": true
            },
            {
                "camera_id": 2,
                "stream_active": true,
                "has_frames": true
            }
        ]
    }
    ```
    """
    stream_service = StreamService(db)
    return stream_service.get_all_streams_status()