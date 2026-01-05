"""
Worker API Endpoints

This module provides REST API endpoints for managing RTSP workers that
process video streams and perform object detection.

Author: ANPR Team
Created: 2025
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.worker_service import WorkerService
from app.schemas.camera import WorkerControl

# Create router for worker endpoints
router = APIRouter(prefix="/workers", tags=["workers"])


@router.post("/cameras/{camera_id}/start", response_model=dict)
def start_worker(camera_id: int, show_window: bool = False, db: Session = Depends(get_db)):
    """
    Start worker for a camera

    Starts a background worker that:
    1. Connects to camera's video stream
    2. Processes frames at target FPS
    3. Detects objects using YOLO with directional counting
    4. Saves detections when objects cross detection line
    5. Queues uploads to central server

    Args:
        camera_id: The camera ID
        show_window: Whether to show detection window for debugging (default: False)

    Raises:
        HTTPException 404: Camera not found
        HTTPException 400: Worker already running or camera inactive
    """
    worker_service = WorkerService(db)
    return worker_service.start_worker(camera_id, show_window=show_window)


@router.post("/cameras/{camera_id}/stop", response_model=dict)
def stop_worker(camera_id: int, db: Session = Depends(get_db)):
    """
    Stop worker for a camera

    Gracefully stops the worker by:
    1. Setting running flag to False
    2. Waiting for current frame to finish
    3. Releasing video capture
    4. Removing from active workers

    Raises:
        HTTPException 404: Camera not found
        HTTPException 400: Worker not running
    """
    worker_service = WorkerService(db)
    return worker_service.stop_worker(camera_id)


@router.post("/cameras/{camera_id}/restart", response_model=dict)
def restart_worker(camera_id: int, db: Session = Depends(get_db)):
    """
    Restart worker for a camera

    Useful when camera settings have been updated.

    Raises:
        HTTPException 404: Camera not found
    """
    worker_service = WorkerService(db)
    return worker_service.restart_worker(camera_id)


@router.post("/cameras/{camera_id}/control", response_model=dict)
def control_worker(camera_id: int, control: WorkerControl, db: Session = Depends(get_db)):
    """
    Control worker (start or stop)

    Request Body:
        action: "start" or "stop"

    Raises:
        HTTPException 404: Camera not found
        HTTPException 400: Invalid action or operation failed
    """
    worker_service = WorkerService(db)

    if control.action == "start":
        return worker_service.start_worker(camera_id)
    elif control.action == "stop":
        return worker_service.stop_worker(camera_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@router.get("/cameras/{camera_id}/status", response_model=dict)
def get_worker_status(camera_id: int, db: Session = Depends(get_db)):
    """
    Get worker status for a camera

    Returns information about whether worker is running and its configuration.
    """
    worker_service = WorkerService(db)
    return worker_service.get_worker_status(camera_id)


@router.get("/status", response_model=dict)
def get_all_workers_status(db: Session = Depends(get_db)):
    """
    Get status of all active workers

    Returns list of all currently running workers with their configurations.
    """
    worker_service = WorkerService(db)
    return worker_service.get_all_workers_status()


@router.post("/stop-all", response_model=dict)
def stop_all_workers(db: Session = Depends(get_db)):
    """
    Stop all active workers

    Useful for system shutdown or maintenance.
    Gracefully stops all running workers.
    """
    worker_service = WorkerService(db)
    return worker_service.stop_all_workers()
