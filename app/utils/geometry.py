"""Utility functions for geometric operations."""

import cv2
import numpy as np
from typing import Tuple, List


def point_in_polygon(point: Tuple[int, int], polygon: List[Tuple[int, int]]) -> bool:
    """Check if a point is inside a polygon using ray casting algorithm.

    Args:
        point: (x, y) coordinates of the point
        polygon: List of (x, y) coordinates forming the polygon

    Returns:
        True if point is inside polygon, False otherwise
    """
    x, y = point
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Check if three points are in counter-clockwise order.

    Args:
        A, B, C: Points as (x, y) tuples

    Returns:
        True if counter-clockwise, False otherwise
    """
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def line_segments_intersect(A: Tuple[float, float], B: Tuple[float, float],
                            C: Tuple[float, float], D: Tuple[float, float]) -> bool:
    """Check if line segment AB intersects with line segment CD.

    Args:
        A, B: Endpoints of first line segment
        C, D: Endpoints of second line segment

    Returns:
        True if segments intersect, False otherwise
    """
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)


def get_centroid(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Get centroid of a bounding box.

    Args:
        bbox: Bounding box as (x1, y1, x2, y2)

    Returns:
        Centroid as (x, y)
    """
    x1, y1, x2, y2 = bbox
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    return cx, cy


def get_bottom_center(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Get bottom center point of a bounding box (useful for vehicle tracking).

    Args:
        bbox: Bounding box as (x1, y1, x2, y2)

    Returns:
        Bottom center point as (x, y)
    """
    x1, y1, x2, y2 = bbox
    cx = int((x1 + x2) / 2)
    cy = int(y2)  # Bottom of the box
    return cx, cy


def get_roi_bounding_box(roi_polygon: List[Tuple[int, int]]) -> Tuple[int, int, int, int]:
    """Get the bounding box that contains the ROI polygon.

    Args:
        roi_polygon: List of (x, y) coordinates forming the polygon

    Returns:
        Bounding box as (x1, y1, x2, y2)
    """
    xs = [p[0] for p in roi_polygon]
    ys = [p[1] for p in roi_polygon]
    return min(xs), min(ys), max(xs), max(ys)


def crop_frame_to_roi(frame: np.ndarray, roi_polygon: List[Tuple[int, int]]) -> Tuple[np.ndarray, Tuple[int, int]]:
    """Crop frame to ROI bounding box for faster detection.

    Args:
        frame: Full video frame
        roi_polygon: ROI polygon points

    Returns:
        Tuple of (cropped_frame, (offset_x, offset_y))
        offset_x, offset_y are needed to map coordinates back to full frame
    """
    x1, y1, x2, y2 = get_roi_bounding_box(roi_polygon)

    # Add padding to ensure we don't miss vehicles at edges
    h, w = frame.shape[:2]
    padding = 50
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)

    cropped = frame[y1:y2, x1:x2]
    return cropped, (x1, y1)
