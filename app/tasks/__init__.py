"""
Tasks Module

This module provides Celery task definitions for asynchronous operations.
Tasks are background jobs that run independently of the main application.

Available Tasks:
    - upload_detection_task: Upload detection with image to central server

Usage:
    from app.tasks import upload_detection_task

    # Queue task for background processing
    upload_detection_task.delay(detection_id, camera_id, ...)

Author: ANPR Team
Created: 2025
"""

from app.tasks.celery_app import celery_app
from app.tasks.upload_tasks import upload_detection_task

__all__ = ["celery_app", "upload_detection_task"]
