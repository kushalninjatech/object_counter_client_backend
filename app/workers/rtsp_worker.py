"""
RTSP Worker Module

This module provides the RTSPWorker class that processes video streams and
performs real-time object detection using YOLO.

Author: ANPR Team
Created: 2025
"""

import cv2
import numpy as np
import uuid
import os
from datetime import datetime, timezone
from ultralytics import YOLO

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.detection_repository import DetectionRepository
from app.tasks.upload_tasks import upload_detection_task
from app.services.vehicle_detection_service import VehicleDetectionService
from app.models.enums import StreamType


class RTSPWorker:
    """
    RTSP Stream Worker for Object Detection

    Processes video streams in real-time, detects objects within ROI,
    and triggers detection events when objects cross the detection line.

    The worker:
    1. Connects to video stream (RTSP, HTTP, IP camera, etc.)
    2. Processes frames at target FPS
    3. Detects objects using YOLO within ROI
    4. Tracks objects across frames
    5. Saves detections when objects cross detection line
    6. Queues uploads to central server via Celery

    Attributes:
        camera_id: Camera ID
        camera_name: Camera name
        stream_url: Video stream URL
        roi: Region of Interest polygon coordinates
        line: Detection line coordinates
        fps: Target FPS for processing
        conf: Confidence threshold for detections
        org_id: Organization ID
        running: Whether worker is currently running
        model: YOLO model instance
        cap: OpenCV video capture
        tracked: Dict mapping YOLO IDs to UUIDs
        track_save_count: Dict tracking number of saves per object
    """

    def __init__(
        self,
        camera_id: int,
        camera_name: str,
        stream_url: str,
        roi: list,
        line: list,
        fps: int,
        conf: float,
        org_id: int,
        stream_type: StreamType = StreamType.DOWNSIDE_UP,
        show_window: bool = False
    ):
        """
        Initialize RTSP Worker

        Args:
            camera_id: Camera ID
            camera_name: Camera name
            stream_url: Video stream URL
            roi: ROI polygon [[x1,y1], [x2,y2], ...]
            line: Detection line [x1, y1, x2, y2]
            fps: Target FPS
            conf: Confidence threshold
            org_id: Organization ID
            stream_type: Camera stream orientation (upside-down or downside-up)
            show_window: Whether to show detection window for debugging
        """
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.stream_url = stream_url
        self.roi = roi
        self.line = line
        self.fps = fps
        self.conf = conf
        self.org_id = org_id
        self.stream_type = stream_type
        self.show_window = show_window

        self.running = False
        self.cap = None

        # Initialize vehicle detection service
        self.detection_service = None

    def start(self):
        """
        Start the worker

        Connects to video stream, initializes YOLO model, and begins
        processing frames. Runs in infinite loop until stop() is called.
        """
        # Initialize vehicle detection service
        self.detection_service = VehicleDetectionService(
            model_path=settings.MODEL_PATH,
            roi_polygon=self.roi,
            detection_line=self.line,
            confidence=self.conf,
            vehicle_classes=settings.detection_classes,
            output_dir=str(settings.DETECTIONS_DIR),
            camera_name=self.camera_name,
            stream_type=self.stream_type,
            show_window=self.show_window,
            window_name=f"Camera {self.camera_id} - {self.camera_name}"
        )

        # Configure OpenCV to use UDP for RTSP (better for real-time)
        os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'

        # Open video stream
        self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            raise Exception(f"Cannot open video stream: {self.stream_url}")

        # Optimize stream settings
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize lag
        self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)

        self.running = True
        source_fps = self.cap.get(cv2.CAP_PROP_FPS)
        skip = max(1, int(source_fps / self.fps))
        frame_num = 0

        # Track consecutive failures for reconnection
        consecutive_failures = 0
        max_consecutive_failures = 30

        print(f"[{self.camera_name}] Worker started (UDP transport, target FPS: {self.fps})")

        while self.running:
            ret, frame = self.cap.read()

            if not ret:
                consecutive_failures += 1

                if not self.running:
                    break

                if consecutive_failures % 10 == 0:
                    print(f"[{self.camera_name}] Frame read failed ({consecutive_failures}/{max_consecutive_failures})")

                # Attempt reconnection
                if consecutive_failures >= max_consecutive_failures:
                    print(f"[{self.camera_name}] Reconnecting...")
                    self.cap.release()

                    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
                    self.cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                    self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)

                    consecutive_failures = 0

                    if not self.cap.isOpened():
                        print(f"[{self.camera_name}] Reconnection failed, stopping")
                        break

                    print(f"[{self.camera_name}] Reconnected successfully")
                continue

            # Reset failure counter on success
            if consecutive_failures > 0:
                print(f"[{self.camera_name}] Connection recovered after {consecutive_failures} failures")
                consecutive_failures = 0

            frame_num += 1
            if frame_num % skip != 0:
                continue

            self.process(frame, frame_num)

        # Cleanup on loop exit
        if self.cap:
            self.cap.release()
        if self.show_window and self.detection_service:
            self.detection_service.close_window()
            cv2.destroyAllWindows()
        print(f"[{self.camera_name}] Worker stopped")

    def process(self, frame, frame_num):
        """
        Process a single frame using VehicleDetectionService

        Detects vehicles, tracks them, and saves detections when they
        cross the detection line with directional counting.

        Args:
            frame: Video frame (numpy array)
            frame_num: Frame number
        """
        # Process frame with vehicle detection service
        annotated_frame, new_detections = self.detection_service.process_frame(frame)

        # Save new detections to database
        if new_detections:
            for detection_info in new_detections:
                self._save_detection_to_db(detection_info)

        # Log progress
        if frame_num % 30 == 0:
            in_count, out_count = self.detection_service.get_counts()
            print(f"[{self.camera_name}] Frame {frame_num} | IN: {in_count} | OUT: {out_count}")

    def _save_detection_to_db(self, detection_info: dict):
        """
        Save detection to database and queue upload task

        Args:
            detection_info: Detection info dict with uuid, track_id, direction, image_path, class_name
        """
        uid = detection_info["uuid"]
        direction = detection_info["direction"]
        image_path = detection_info["image_path"]  # Relative path
        class_name = detection_info["class_name"]

        # Save to database
        db = SessionLocal()
        try:
            detection_repo = DetectionRepository(db)
            detection = detection_repo.create(
                camera_id=self.camera_id,
                camera_name=self.camera_name,
                object_track_id=uid,
                object_class=class_name,
                activity_type=direction,  # Save activity direction (in/out)
                image_path=image_path
            )
            det_id = detection.id

            # Convert relative path to absolute path for upload task
            from pathlib import Path
            from app.core.config import settings
            absolute_image_path = str(Path(settings.DETECTIONS_DIR) / image_path)

            # Convert datetime to string for upload task
            created_at_str = str(detection.created_at) if detection.created_at else None

            # Queue upload task
            upload_detection_task.delay(
                detection_id=det_id,
                camera_id=self.camera_id,
                camera_name=self.camera_name,
                object_track_id=uid,
                object_class=class_name,
                image_path=absolute_image_path,  # Send absolute path
                organization_id=self.org_id,
                activity_type=direction,
                created_at=created_at_str  # Send as string
            )

            print(f"[{self.camera_name}] ✓ SAVED: {class_name} [{direction.upper()}] - {uid[:8]} | Queued for upload")

        finally:
            db.close()

    def stop(self):
        """
        Stop the worker

        Sets running flag to False, causing the main loop to exit gracefully.
        The main loop's finally block will handle resource cleanup to avoid race conditions.
        """
        print(f"[{self.camera_name}] Stopping worker...")
        self.running = False
        # Don't release resources here - let the main loop's finally block handle it
        # This avoids race conditions with cap.read() calls
