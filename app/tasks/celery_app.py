"""
Celery Application Configuration

This module configures the Celery application for asynchronous task processing.
Celery is used to handle background jobs like uploading detections to the central server.

Features:
    - Automatic retry with progressive backoff
    - Task result storage in Redis
    - JSON serialization for task arguments
    - UTC timezone for consistency

Author: ANPR Team
Created: 2025
"""

from celery import Celery
from app.core.config import settings

# Create Celery application instance
# broker: Redis URL for task queue
# backend: Redis URL for storing task results
celery_app = Celery(
    'anpr_client',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery settings
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Task tracking
    task_track_started=True,  # Track when tasks start
    task_acks_late=True,      # Acknowledge task after completion (not before)

    # Worker settings
    worker_prefetch_multiplier=1,  # Worker processes one task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)

    # Task execution
    task_soft_time_limit=300,  # Soft limit: 5 minutes (raises exception)
    task_time_limit=360,       # Hard limit: 6 minutes (kills task)

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Broker settings
    broker_connection_retry_on_startup=True,  # Retry connection on startup
)

# Import task modules to register tasks with Celery
# This must be done after celery_app is created
from app.tasks import upload_tasks  # noqa: E402, F401
