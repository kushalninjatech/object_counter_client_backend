"""
Worker Service Module

This module provides business logic for managing RTSP workers that process
video streams and perform object detection.

Author: ANPR Team
Created: 2025
"""

from typing import Dict, Optional
from threading import Thread
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.camera_service import CameraService


# Global dictionary to store active workers
# Key: camera_id, Value: RTSPWorker instance
ACTIVE_WORKERS: Dict[int, any] = {}


class WorkerService:
    """
    Worker Service

    Manages the lifecycle of RTSP workers that process video streams.
    Each worker runs in a separate thread and performs object detection
    on frames from the camera's video stream.

    Responsibilities:
        - Start/stop workers for specific cameras
        - Track active workers
        - Validate worker operations
        - Handle worker lifecycle events

    Note:
        Workers are imported dynamically to avoid circular dependencies.
        The actual RTSPWorker class is in app/workers/rtsp_worker.py

    Example:
        worker_service = WorkerService(db)

        # Start worker for camera
        result = worker_service.start_worker(camera_id=1)

        # Stop worker
        result = worker_service.stop_worker(camera_id=1)

        # Check if worker is running
        is_running = worker_service.is_worker_running(camera_id=1)
    """

    def __init__(self, db: Session):
        """
        Initialize the Worker Service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.camera_service = CameraService(db)

    def is_worker_running(self, camera_id: int) -> bool:
        """
        Check if a worker is currently running for a camera

        Args:
            camera_id: The camera ID

        Returns:
            True if worker is running, False otherwise
        """
        return camera_id in ACTIVE_WORKERS

    def get_worker_status(self, camera_id: int) -> Dict[str, any]:
        """
        Get worker status for a camera

        Args:
            camera_id: The camera ID

        Returns:
            Dictionary with worker status information
        """
        is_running = self.is_worker_running(camera_id)

        result = {
            "camera_id": camera_id,
            "worker_running": is_running
        }

        if is_running:
            worker = ACTIVE_WORKERS[camera_id]
            result["worker_info"] = {
                "running": worker.running,
                "camera_name": worker.camera_name,
                "target_fps": worker.fps,
                "confidence": worker.conf
            }

        return result

    def get_all_workers_status(self) -> Dict[str, any]:
        """
        Get status of all active workers

        Returns:
            Dictionary with information about all active workers
        """
        active_workers = []

        for camera_id, worker in ACTIVE_WORKERS.items():
            active_workers.append({
                "camera_id": camera_id,
                "camera_name": worker.camera_name,
                "running": worker.running,
                "target_fps": worker.fps,
                "confidence": worker.conf
            })

        return {
            "total_workers": len(ACTIVE_WORKERS),
            "active_workers": active_workers
        }

    def start_worker(self, camera_id: int, show_window: bool = False) -> Dict[str, any]:
        """
        Start a worker for a specific camera

        Creates an RTSPWorker instance and starts it in a separate thread.
        The worker will:
        1. Connect to the camera's video stream
        2. Process frames at the target FPS
        3. Detect objects using YOLO with directional counting
        4. Save detections when objects cross the detection line
        5. Queue uploads to central server via Celery

        Args:
            camera_id: The camera ID
            show_window: Whether to show detection window for debugging (default: False)

        Returns:
            Dictionary with success message and worker info

        Raises:
            HTTPException:
                - 404: Camera not found
                - 400: Worker already running
                - 500: Failed to start worker
        """
        # Validate camera exists and is active
        camera = self.camera_service.get_camera_by_id(camera_id)

        if not camera.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Camera '{camera.name}' is not active"
            )

        # Check if worker is already running
        if self.is_worker_running(camera_id):
            raise HTTPException(
                status_code=400,
                detail=f"Worker already running for camera '{camera.name}'"
            )

        # Import RTSPWorker here to avoid circular imports
        from app.workers.rtsp_worker import RTSPWorker

        # Create worker instance
        worker = RTSPWorker(
            camera_id=camera.id,
            camera_name=camera.name,
            stream_url=camera.stream_url,
            roi=camera.roi_polygon,
            line=camera.detection_line,
            fps=camera.target_fps,
            conf=camera.confidence,
            org_id=camera.organization_id,
            stream_type=camera.stream_type,
            show_window=show_window
        )

        # Store worker in global dictionary
        ACTIVE_WORKERS[camera_id] = worker

        # Start worker in a separate daemon thread
        # Daemon thread will automatically terminate when main thread exits
        thread = Thread(target=worker.start, daemon=True)
        thread.start()

        return {
            "message": f"Worker started successfully for camera '{camera.name}'",
            "camera_id": camera_id,
            "camera_name": camera.name,
            "worker_running": True,
            "show_window": show_window
        }

    def stop_worker(self, camera_id: int) -> Dict[str, any]:
        """
        Stop a running worker for a specific camera

        Gracefully stops the worker by:
        1. Setting the worker's running flag to False
        2. Removing from active workers (worker thread will cleanup on its own)

        Args:
            camera_id: The camera ID

        Returns:
            Dictionary with success message

        Raises:
            HTTPException:
                - 404: Camera not found
                - 400: Worker not running
        """
        # Validate camera exists
        camera = self.camera_service.get_camera_by_id(camera_id)

        # Check if worker is running
        if not self.is_worker_running(camera_id):
            raise HTTPException(
                status_code=400,
                detail=f"No worker running for camera '{camera.name}'"
            )

        # Get worker instance
        worker = ACTIVE_WORKERS[camera_id]

        # Remove from active workers first (prevents new operations on this worker)
        del ACTIVE_WORKERS[camera_id]

        # Stop the worker (sets running flag to False)
        # The worker thread will cleanup resources naturally when loop exits
        worker.stop()

        return {
            "message": f"Worker stopped successfully for camera '{camera.name}'",
            "camera_id": camera_id,
            "camera_name": camera.name,
            "worker_running": False
        }

    def restart_worker(self, camera_id: int) -> Dict[str, any]:
        """
        Restart a worker (stop if running, then start)

        Useful when camera settings have been updated and need to be applied.

        Args:
            camera_id: The camera ID

        Returns:
            Dictionary with success message

        Raises:
            HTTPException: If camera not found or restart fails
        """
        # Stop worker if running
        was_running = self.is_worker_running(camera_id)
        if was_running:
            self.stop_worker(camera_id)

        # Start worker
        result = self.start_worker(camera_id)

        result["message"] = f"Worker restarted successfully for camera '{result['camera_name']}'"
        result["was_running"] = was_running

        return result

    def stop_all_workers(self) -> Dict[str, any]:
        """
        Stop all active workers

        Useful when shutting down the application or performing maintenance.

        Returns:
            Dictionary with information about stopped workers
        """
        stopped_count = 0
        stopped_cameras = []

        # Create a copy of workers to avoid modifying dict during iteration
        workers_copy = dict(ACTIVE_WORKERS)

        # Clear ACTIVE_WORKERS first
        ACTIVE_WORKERS.clear()

        # Now stop each worker
        for camera_id, worker in workers_copy.items():
            try:
                worker.stop()
                stopped_count += 1
                stopped_cameras.append({
                    "camera_id": camera_id,
                    "camera_name": worker.camera_name
                })
            except Exception as e:
                print(f"Error stopping worker for camera {camera_id}: {e}")

        return {
            "message": f"Stopped {stopped_count} workers",
            "stopped_count": stopped_count,
            "stopped_cameras": stopped_cameras
        }

    def get_worker(self, camera_id: int) -> Optional[any]:
        """
        Get the worker instance for a camera

        Args:
            camera_id: The camera ID

        Returns:
            RTSPWorker instance if running, None otherwise
        """
        return ACTIVE_WORKERS.get(camera_id)
