"""Vehicle detection service with YOLOv8 tracking and directional counting."""

import cv2
import numpy as np
import uuid
import os
import time
from typing import List, Tuple, Dict, Optional
from collections import deque
from ultralytics import YOLO

from app.utils.geometry import (
    point_in_polygon,
    get_centroid,
    get_bottom_center,
    crop_frame_to_roi
)
from app.utils.line_crossing import SingleLineCrossingDetector
from app.models.enums import StreamType


class VehicleState:
    """Represents the state of a tracked vehicle."""

    def __init__(self, track_id: int):
        """Initialize vehicle state.

        Args:
            track_id: Tracking ID from the tracker
        """
        self.uuid = str(uuid.uuid4())
        self.track_id = track_id
        self.line_crossed = False
        self.crossed_timestamp: Optional[float] = None
        self.counted = False
        self.direction: Optional[str] = None  # "in" or "out"
        self.trajectory = deque(maxlen=30)  # Store last 30 positions
        self.crossing_image: Optional[str] = None

    def get_last_position(self) -> Optional[Tuple[int, int]]:
        """Get the last known position.

        Returns:
            Last position as (x, y) or None if no trajectory
        """
        return self.trajectory[-1] if self.trajectory else None

    def add_position(self, position: Tuple[int, int]):
        """Add a new position to trajectory.

        Args:
            position: Position as (x, y)
        """
        self.trajectory.append(position)


class VehicleDetectionService:
    """Service for vehicle detection, tracking, and counting."""

    def __init__(
        self,
        model_path: str,
        roi_polygon: List[List[int]],
        detection_line: List[int],
        confidence: float = 0.5,
        vehicle_classes: List[int] = None,
        output_dir: str = "detections",
        camera_name: str = "camera",
        stream_type: StreamType = StreamType.DOWNSIDE_UP,
        show_window: bool = True, ## change here to false to stop showing the window
        window_name: str = "Vehicle Detection"
    ):
        """Initialize vehicle detection service.

        Args:
            model_path: Path to YOLO model
            roi_polygon: ROI polygon as [[x1,y1], [x2,y2], ...]
            detection_line: Detection line as [x1, y1, x2, y2]
            confidence: Detection confidence threshold
            vehicle_classes: List of vehicle class IDs (default: [2, 3] for car, motorcycle)
            output_dir: Directory to save detected vehicle images
            camera_name: Camera name for folder structure
            stream_type: Camera stream orientation (upside-down or downside-up)
            show_window: Whether to show detection window for debugging
            window_name: Name of the detection window
        """
        print(f"[VehicleDetectionService] Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        print("[VehicleDetectionService] Model loaded successfully!")

        # Convert ROI polygon to list of tuples
        self.roi_polygon = [tuple(point) for point in roi_polygon]

        # Convert detection line to list of tuples [(x1, y1), (x2, y2)]
        self.detection_line = [(detection_line[0], detection_line[1]),
                               (detection_line[2], detection_line[3])]

        self.confidence = confidence
        self.vehicle_classes = vehicle_classes if vehicle_classes else [2, 3]  # car, motorcycle
        self.output_dir = output_dir
        self.camera_name = camera_name
        self.stream_type = stream_type
        self.show_window = False#show_window
        self.window_name = window_name

        # Debug logging
        print(f"[VehicleDetectionService] Window display: {'ENABLED' if self.show_window else 'DISABLED'}")
        print(f"[VehicleDetectionService] Stream type: {stream_type.value}")
        if show_window:
            print(f"[VehicleDetectionService] Window name: '{window_name}'")

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize line crossing detector
        self.line_detector = SingleLineCrossingDetector(self.detection_line)

        # Vehicle tracking state
        self.vehicles: Dict[int, VehicleState] = {}
        self.in_count = 0
        self.out_count = 0
        self.counted_vehicles: List[VehicleState] = []

        # Colors for visualization (BGR format)
        self.COLOR_ROI = (0, 255, 0)  # Green
        self.COLOR_LINE = (255, 0, 0)  # Blue
        self.COLOR_BBOX_UNCOUNTED = (0, 255, 255)  # Yellow
        self.COLOR_BBOX_IN = (0, 255, 0)  # Green
        self.COLOR_BBOX_OUT = (0, 100, 255)  # Orange
        self.COLOR_TRAJECTORY = (255, 165, 0)  # Orange
        self.COLOR_TEXT = (255, 255, 255)  # White

    def detect_and_track(self, frame: np.ndarray) -> List[Dict]:
        """Detect and track vehicles in a frame.

        Args:
            frame: Input video frame

        Returns:
            List of detections with tracking info
        """
        # Crop frame to ROI for faster detection
        cropped_frame, (offset_x, offset_y) = crop_frame_to_roi(frame, self.roi_polygon)

        # Run YOLO tracking on cropped frame
        results = self.model.track(
            cropped_frame,
            persist=True,
            conf=self.confidence,
            classes=self.vehicle_classes,
            verbose=False
        )

        detections = []

        if results[0].boxes is not None and results[0].boxes.id is not None:
            # Extract detection data
            boxes = results[0].boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
            confidences = results[0].boxes.conf.cpu().numpy()
            class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, conf, class_id, track_id in zip(boxes, confidences, class_ids, track_ids):
                x1, y1, x2, y2 = map(int, box)

                # Map coordinates back to full frame
                x1_full = x1 + offset_x
                y1_full = y1 + offset_y
                x2_full = x2 + offset_x
                y2_full = y2 + offset_y
                bbox = (x1_full, y1_full, x2_full, y2_full)

                # Calculate position points (in full frame coordinates)
                centroid = get_centroid(bbox)
                bottom_center = get_bottom_center(bbox)

                # Filter by ROI polygon - only include vehicles inside ROI
                # Using centroid (middle of bounding box) for detection
                if not point_in_polygon(centroid, self.roi_polygon):
                    continue  # Skip this vehicle, it's outside ROI polygon

                # Get class name
                class_name = self.model.names[class_id]

                detection = {
                    "track_id": track_id,
                    "bbox": bbox,
                    "confidence": float(conf),
                    "class_id": class_id,
                    "class_name": class_name,
                    "centroid": centroid,
                    "bottom_center": bottom_center
                }

                detections.append(detection)

        return detections

    def update_tracker(self, track_id: int, position: Tuple[int, int],
                      frame: Optional[np.ndarray] = None,
                      bbox: Optional[Tuple[int, int, int, int]] = None,
                      class_name: Optional[str] = None) -> Optional[Dict]:
        """Update vehicle state and check for line crossings.

        Args:
            track_id: Tracking ID
            position: Current position (x, y)
            frame: Current video frame (for image capture)
            bbox: Bounding box (x1, y1, x2, y2) for cropping
            class_name: Detected object class name (e.g., 'car', 'person')

        Returns:
            Detection info dict if vehicle was counted, None otherwise
        """
        # Create new vehicle if not exists
        if track_id not in self.vehicles:
            self.vehicles[track_id] = VehicleState(track_id)

        vehicle = self.vehicles[track_id]

        # Skip if already counted
        if vehicle.counted:
            return None

        # Get previous position
        prev_position = vehicle.get_last_position()

        # Add current position
        vehicle.add_position(position)

        # Check line crossing and determine direction
        if prev_position is not None and not vehicle.counted:
            # Get raw direction from line crossing detector
            raw_direction = self.line_detector.get_crossing_direction(prev_position, position)

            if raw_direction is not None:
                # Apply stream_type logic to determine final direction
                # For upside-down cameras: swap in/out (towards camera = IN, away = OUT)
                # For downside-up cameras: keep original (away from camera = IN, towards = OUT)
                if self.stream_type == StreamType.UPSIDE_DOWN:
                    # Invert direction for upside-down cameras
                    direction = "out" if raw_direction == "in" else "in"
                    print(f"[VehicleDetectionService] UPSIDE-DOWN camera: raw={raw_direction} → final={direction}")
                else:
                    # Keep original direction for downside-up cameras
                    direction = raw_direction

                # Line was crossed! Count immediately
                vehicle.line_crossed = True
                vehicle.crossed_timestamp = time.time()
                vehicle.direction = direction
                vehicle.counted = True

                # Save vehicle image
                if frame is not None and bbox is not None:
                    vehicle.crossing_image = self._save_vehicle_image(vehicle, frame, bbox, class_name)

                # Update counts
                if direction == "in":
                    self.in_count += 1
                    print(f"✅ Vehicle ID:{track_id} COUNTED as IN at position {position}")
                    print(f"   📊 Total IN: {self.in_count} | Total OUT: {self.out_count}")
                else:
                    self.out_count += 1
                    print(f"✅ Vehicle ID:{track_id} COUNTED as OUT at position {position}")
                    print(f"   📊 Total IN: {self.in_count} | Total OUT: {self.out_count}")

                self.counted_vehicles.append(vehicle)

                # Return detection info for database storage
                return {
                    "uuid": vehicle.uuid,
                    "track_id": track_id,
                    "direction": direction,
                    "image_path": vehicle.crossing_image,
                    "timestamp": vehicle.crossed_timestamp
                }

        return None

    def _save_vehicle_image(self, vehicle: VehicleState, frame: np.ndarray,
                           bbox: Tuple[int, int, int, int], class_name: str = None) -> str:
        """Save full frame with bounding box and detection info.

        Args:
            vehicle: Vehicle state
            frame: Current video frame
            bbox: Bounding box (x1, y1, x2, y2)
            class_name: Detected object class name

        Returns:
            Path to saved image (relative path from output_dir)
        """
        from datetime import datetime

        # Get current date and time
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        time_str = now.strftime("%H-%M-%S")

        # Create folder structure: camera_name/year/month/date/
        camera_folder = os.path.join(self.output_dir, self.camera_name)
        year_folder = os.path.join(camera_folder, year)
        month_folder = os.path.join(year_folder, month)
        date_folder = os.path.join(month_folder, day)
        os.makedirs(date_folder, exist_ok=True)

        # Generate filename with time prefix: HH-MM-SS_uuid_direction.jpg
        filename = f"{time_str}_{vehicle.uuid}_{vehicle.direction}.jpg"
        filepath = os.path.join(date_folder, filename)

        # Generate relative path for database storage: camera_name/year/month/day/filename
        relative_path = os.path.join(self.camera_name, year, month, day, filename)

        # Create a copy of the frame to draw on
        annotated_frame = frame.copy()

        # Extract bounding box coordinates
        x1, y1, x2, y2 = bbox

        # Draw bounding box
        color = (0, 255, 0) if vehicle.direction == "in" else (0, 165, 255)  # Green for IN, Orange for OUT
        thickness = 3
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)

        # Prepare label text
        label_parts = []
        if class_name:
            label_parts.append(class_name.upper())
        if vehicle.direction:
            label_parts.append(vehicle.direction.upper())

        label = " - ".join(label_parts) if label_parts else "DETECTED"

        # Draw label background
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)

        # Position label above the bounding box
        label_y = y1 - 10 if y1 - 10 > text_height else y1 + text_height + 10

        # Draw filled rectangle for label background
        cv2.rectangle(
            annotated_frame,
            (x1, label_y - text_height - baseline),
            (x1 + text_width, label_y + baseline),
            color,
            -1  # Filled
        )

        # Draw label text
        cv2.putText(
            annotated_frame,
            label,
            (x1, label_y),
            font,
            font_scale,
            (255, 255, 255),  # White text
            font_thickness,
            cv2.LINE_AA
        )

        # Save annotated frame
        cv2.imwrite(filepath, annotated_frame)

        # Return relative path for database storage
        return relative_path

    def cleanup_old_vehicles(self, active_track_ids: List[int]):
        """Remove vehicles that are no longer active and already counted.

        Args:
            active_track_ids: List of currently active tracking IDs
        """
        # Only delete counted vehicles that are no longer active
        inactive_ids = [tid for tid in self.vehicles.keys()
                       if tid not in active_track_ids and self.vehicles[tid].counted]

        for tid in inactive_ids:
            del self.vehicles[tid]

    def get_counts(self) -> Tuple[int, int]:
        """Get current counts.

        Returns:
            Tuple of (in_count, out_count)
        """
        return self.in_count, self.out_count

    def draw_visualization(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Draw bounding boxes, ROI, line, and statistics on frame.

        Args:
            frame: Input frame
            detections: List of detections from detect_and_track

        Returns:
            Frame with drawn annotations
        """
        annotated_frame = frame.copy()

        # Draw ROI polygon
        roi_points = np.array(self.roi_polygon, dtype=np.int32)
        cv2.polylines(annotated_frame, [roi_points], True, self.COLOR_ROI, 2)

        # Draw filled ROI with transparency
        overlay = annotated_frame.copy()
        cv2.fillPoly(overlay, [roi_points], self.COLOR_ROI)
        cv2.addWeighted(overlay, 0.15, annotated_frame, 0.85, 0, annotated_frame)

        # Draw detection line
        (x1, y1), (x2, y2) = self.detection_line
        cv2.line(annotated_frame, (x1, y1), (x2, y2), self.COLOR_LINE, 3)
        cv2.circle(annotated_frame, (x1, y1), 8, self.COLOR_LINE, -1)
        cv2.circle(annotated_frame, (x2, y2), 8, self.COLOR_LINE, -1)

        # Draw detections
        for det in detections:
            track_id = det["track_id"]
            x1, y1, x2, y2 = det["bbox"]
            class_name = det["class_name"]
            centroid = det["centroid"]  # Use centroid (middle) instead of bottom_center

            # Get vehicle state
            bbox_color = self.COLOR_BBOX_UNCOUNTED
            state_text = ""

            if track_id in self.vehicles:
                vehicle = self.vehicles[track_id]
                if vehicle.counted:
                    state_text = f" [{vehicle.direction.upper()}]"
                    bbox_color = self.COLOR_BBOX_IN if vehicle.direction == "in" else self.COLOR_BBOX_OUT

            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), bbox_color, 2)

            # Draw label
            label = f"ID:{track_id} {class_name}{state_text}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            label_y = max(y1 - 10, label_size[1] + 10)

            # Draw label background
            cv2.rectangle(annotated_frame,
                         (x1, label_y - label_size[1] - 5),
                         (x1 + label_size[0] + 5, label_y + 5),
                         bbox_color, -1)

            # Draw label text
            cv2.putText(annotated_frame, label, (x1 + 2, label_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

            # Draw center point (centroid - middle of bounding box)
            cv2.circle(annotated_frame, centroid, 4, bbox_color, -1)

            # Draw trajectory
            if track_id in self.vehicles:
                trajectory = list(self.vehicles[track_id].trajectory)
                if len(trajectory) > 1:
                    points = np.array(trajectory, dtype=np.int32)
                    cv2.polylines(annotated_frame, [points], False, self.COLOR_TRAJECTORY, 2)

        # Draw statistics
        in_count, out_count = self.get_counts()

        # Large count display at top center
        cv2.putText(annotated_frame, f"IN: {in_count}", (50, 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 2.5, self.COLOR_BBOX_IN, 5)
        cv2.putText(annotated_frame, f"OUT: {out_count}", (50, 160),
                   cv2.FONT_HERSHEY_SIMPLEX, 2.5, self.COLOR_BBOX_OUT, 5)

        return annotated_frame

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """Process a single frame: detect, track, and visualize.

        Args:
            frame: Input video frame

        Returns:
            Tuple of (annotated_frame, new_detections)
            new_detections: List of vehicles that were just counted
        """
        # Detect and track vehicles
        detections = self.detect_and_track(frame)

        # Update tracker and collect new detections
        new_detections = []
        active_track_ids = []

        for det in detections:
            track_id = det["track_id"]
            active_track_ids.append(track_id)

            # Use centroid (middle of bounding box) for line crossing detection
            detection_info = self.update_tracker(
                track_id,
                det["centroid"],
                frame,
                det["bbox"],
                det["class_name"]  # Pass class name for annotation
            )

            if detection_info:
                # Add class info to detection
                detection_info["class_id"] = det["class_id"]
                detection_info["class_name"] = det["class_name"]
                new_detections.append(detection_info)

        # Cleanup old vehicles
        self.cleanup_old_vehicles(active_track_ids)

        # Draw visualization
        annotated_frame = self.draw_visualization(frame, detections)

        # Show window if enabled
        if self.show_window:
            try:
                cv2.imshow(self.window_name, annotated_frame)
                cv2.waitKey(1)
            except Exception as e:
                print(f"[VehicleDetectionService] Error displaying window: {e}")
                print(f"[VehicleDetectionService] Make sure you're running on a system with display")

        return annotated_frame, new_detections

    def close_window(self):
        """Close the display window if it's open."""
        if self.show_window:
            cv2.destroyWindow(self.window_name)
