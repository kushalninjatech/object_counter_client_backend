"""Enums used across models"""
import enum


class StreamType(str, enum.Enum):
    """Enum for camera stream orientation type"""
    UPSIDE_DOWN = "upside-down"
    DOWNSIDE_UP = "downside-up"


class DetectionType(int, enum.Enum):
    """Enum for YOLO object detection classes (COCO dataset)"""
    PERSON = 0
    CAR = 2
    MOTORCYCLE = 3
    BUS = 5
    TRUCK = 7


class ActivityType(str, enum.Enum):
    """Enum for detection activity direction"""
    IN = "in"
    OUT = "out"
