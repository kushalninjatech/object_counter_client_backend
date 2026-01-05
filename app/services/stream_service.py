"""
Stream Service Module

This module provides video streaming functionality for cameras.
It manages live MJPEG streams from RTSP/HTTP cameras to web browsers.

Author: ANPR Team
Created: 2025
"""

import cv2
import threading
import asyncio
import time
from typing import Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.camera_service import CameraService


# Global storage for active streams (shared across all service instances)
# These are module-level to persist across requests
ACTIVE_STREAMS: Dict[int, cv2.VideoCapture] = {}  # {camera_id: VideoCapture}
LATEST_FRAMES: Dict[int, bytes] = {}  # {camera_id: jpeg_bytes}
FRAME_LOCKS: Dict[int, threading.Lock] = {}  # {camera_id: Lock}
STREAM_THREADS: Dict[int, threading.Thread] = {}  # {camera_id: Thread}
STOP_FLAGS: Dict[int, threading.Event] = {}  # {camera_id: Event}


class StreamService:
    """
    Stream Service

    Manages live video streaming from cameras to web browsers using MJPEG format.
    Each camera can have one active stream that runs in a background thread,
    continuously capturing frames and storing them in memory.

    Unlike RTSPWorker (which does AI detection), this service focuses purely
    on video streaming for preview/monitoring purposes.

    Key Features:
        - Multi-camera concurrent streaming
        - Thread-safe frame buffering
        - Automatic reconnection on failure
        - Low memory footprint (stores only latest frame)
        - MJPEG format (browser-compatible)

    Example:
        stream_service = StreamService(db)

        # Start streaming
        stream_service.start_stream(camera_id=1)

        # Get frames for endpoint
        async for frame in stream_service.generate_frames(camera_id=1):
            yield frame

        # Stop streaming
        stream_service.stop_stream(camera_id=1)
    """

    def __init__(self, db: Session):
        """
        Initialize Stream Service

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.camera_service = CameraService(db)

    def is_stream_active(self, camera_id: int) -> bool:
        """
        Check if a stream is currently active for a camera

        Args:
            camera_id: The camera ID

        Returns:
            True if stream is running, False otherwise
        """
        return camera_id in STREAM_THREADS and STREAM_THREADS[camera_id].is_alive()

    def get_stream_status(self, camera_id: int) -> Dict:
        """
        Get status of a specific camera stream

        Args:
            camera_id: The camera ID

        Returns:
            Dictionary with stream status information
        """
        is_active = self.is_stream_active(camera_id)
        has_frames = camera_id in LATEST_FRAMES and len(LATEST_FRAMES[camera_id]) > 0

        return {
            "camera_id": camera_id,
            "stream_active": is_active,
            "has_frames": has_frames
        }

    def get_all_streams_status(self) -> Dict:
        """
        Get status of all active streams

        Returns:
            Dictionary with information about all streams
        """
        active_streams = []

        for camera_id in list(STREAM_THREADS.keys()):
            if self.is_stream_active(camera_id):
                active_streams.append(self.get_stream_status(camera_id))

        return {
            "total_streams": len(active_streams),
            "active_streams": active_streams
        }

    def _capture_frames(self, camera_id: int, rtsp_url: str, target_fps: int = 30):
        """
        Background thread function that continuously captures frames

        This runs in a separate thread and continuously reads frames from
        the camera stream, encodes them as JPEG, and stores in memory.

        Args:
            camera_id: The camera ID
            rtsp_url: The RTSP/HTTP stream URL
            target_fps: Target frame rate for streaming (default: 30)
        """
        # Open video stream with TCP transport (more reliable than UDP for streaming)
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize lag
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)  # 15s timeout
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 15000)

        if not cap.isOpened():
            print(f"[Stream {camera_id}] Failed to open stream: {rtsp_url}")
            return

        ACTIVE_STREAMS[camera_id] = cap

        reconnect_attempts = 0
        max_reconnect_attempts = 5
        frame_delay = 1.0 / target_fps  # Calculate delay for target FPS

        print(f"[Stream {camera_id}] Thread started (target FPS: {target_fps})")

        while not STOP_FLAGS[camera_id].is_set():
            success, frame = cap.read()

            if not success:
                print(f"[Stream {camera_id}] Failed to read frame. Attempting reconnect...")
                cap.release()

                if reconnect_attempts >= max_reconnect_attempts:
                    print(f"[Stream {camera_id}] Max reconnect attempts reached. Waiting 10s...")
                    time.sleep(10)
                    reconnect_attempts = 0

                # Reconnect
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 15000)

                ACTIVE_STREAMS[camera_id] = cap
                reconnect_attempts += 1
                time.sleep(1)
                continue

            # Reset reconnect counter on success
            reconnect_attempts = 0

            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()

            # Update latest frame with thread lock (thread-safe)
            with FRAME_LOCKS[camera_id]:
                LATEST_FRAMES[camera_id] = frame_bytes

            # Control frame rate
            time.sleep(frame_delay)

        # Cleanup when thread stops
        cap.release()
        print(f"[Stream {camera_id}] Thread stopped")

    def start_stream(self, camera_id: int, target_fps: int = 30) -> Dict:
        """
        Start streaming for a specific camera

        Creates a background thread that continuously captures frames
        from the camera stream and stores them in memory.

        Args:
            camera_id: The camera ID
            target_fps: Target frame rate for streaming (default: 30)

        Returns:
            Dictionary with success message

        Raises:
            HTTPException:
                - 404: Camera not found
                - 400: Stream already active or camera inactive
        """
        # Validate camera exists
        camera = self.camera_service.get_camera_by_id(camera_id)

        if not camera.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Camera '{camera.name}' is not active"
            )

        # Check if stream already running
        if self.is_stream_active(camera_id):
            raise HTTPException(
                status_code=400,
                detail=f"Stream already active for camera '{camera.name}'"
            )

        # Initialize lock and stop flag if needed
        if camera_id not in FRAME_LOCKS:
            FRAME_LOCKS[camera_id] = threading.Lock()
        if camera_id not in STOP_FLAGS:
            STOP_FLAGS[camera_id] = threading.Event()

        # Clear previous frame data
        LATEST_FRAMES[camera_id] = b''
        STOP_FLAGS[camera_id].clear()

        # Start background thread
        thread = threading.Thread(
            target=self._capture_frames,
            args=(camera_id, camera.stream_url, target_fps),
            daemon=True
        )
        thread.start()
        STREAM_THREADS[camera_id] = thread

        return {
            "message": f"Stream started successfully for camera '{camera.name}'",
            "camera_id": camera_id,
            "camera_name": camera.name,
            "stream_active": True,
            "target_fps": target_fps
        }

    def stop_stream(self, camera_id: int) -> Dict:
        """
        Stop streaming for a specific camera

        Gracefully stops the background thread and releases resources.

        Args:
            camera_id: The camera ID

        Returns:
            Dictionary with success message

        Raises:
            HTTPException:
                - 404: Camera not found
                - 400: Stream not active
        """
        # Validate camera exists
        camera = self.camera_service.get_camera_by_id(camera_id)

        # Check if stream is running
        if not self.is_stream_active(camera_id):
            raise HTTPException(
                status_code=400,
                detail=f"No active stream for camera '{camera.name}'"
            )

        # Signal thread to stop
        STOP_FLAGS[camera_id].set()

        # Wait for thread to finish (with timeout)
        STREAM_THREADS[camera_id].join(timeout=5)

        # Clean up
        if camera_id in ACTIVE_STREAMS:
            ACTIVE_STREAMS[camera_id].release()
            del ACTIVE_STREAMS[camera_id]

        with FRAME_LOCKS[camera_id]:
            LATEST_FRAMES[camera_id] = b''

        del STREAM_THREADS[camera_id]

        return {
            "message": f"Stream stopped successfully for camera '{camera.name}'",
            "camera_id": camera_id,
            "camera_name": camera.name,
            "stream_active": False
        }

    def stop_all_streams(self) -> Dict:
        """
        Stop all active streams

        Useful for application shutdown or maintenance.

        Returns:
            Dictionary with information about stopped streams
        """
        stopped_count = 0
        stopped_cameras = []

        # Create a copy of camera IDs to avoid modifying dict during iteration
        camera_ids = list(STREAM_THREADS.keys())

        for camera_id in camera_ids:
            try:
                # Signal thread to stop
                STOP_FLAGS[camera_id].set()

                # Wait for thread to finish
                if STREAM_THREADS[camera_id].is_alive():
                    STREAM_THREADS[camera_id].join(timeout=5)

                # Clean up
                if camera_id in ACTIVE_STREAMS:
                    ACTIVE_STREAMS[camera_id].release()
                    del ACTIVE_STREAMS[camera_id]

                with FRAME_LOCKS[camera_id]:
                    LATEST_FRAMES[camera_id] = b''

                del STREAM_THREADS[camera_id]

                stopped_count += 1
                stopped_cameras.append(camera_id)

            except Exception as e:
                print(f"Error stopping stream for camera {camera_id}: {e}")

        return {
            "message": f"Stopped {stopped_count} streams",
            "stopped_count": stopped_count,
            "stopped_camera_ids": stopped_cameras
        }

    async def generate_frames(self, camera_id: int):
        """
        Async generator that yields MJPEG frames for streaming

        This is used by the FastAPI endpoint to create a StreamingResponse.
        It continuously reads the latest frame from memory and yields it
        in MJPEG format.

        Args:
            camera_id: The camera ID

        Yields:
            MJPEG frame bytes in multipart format

        Example:
            return StreamingResponse(
                stream_service.generate_frames(camera_id),
                media_type="multipart/x-mixed-replace; boundary=frame"
            )
        """
        while True:
            # Check if stream is still active
            if not self.is_stream_active(camera_id):
                break

            # Get latest frame from shared memory (thread-safe)
            with FRAME_LOCKS[camera_id]:
                if not LATEST_FRAMES[camera_id]:
                    # No frame available yet, wait and retry
                    await asyncio.sleep(0.1)
                    continue

                frame_bytes = LATEST_FRAMES[camera_id]

            # Yield frame in MJPEG format
            # Format: --frame\r\nContent-Type: image/jpeg\r\n\r\n[JPEG DATA]\r\n
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Control streaming rate (~30 FPS max)
            await asyncio.sleep(0.033)
