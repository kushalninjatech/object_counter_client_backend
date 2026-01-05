"""
Upload Tasks Module

This module defines the Celery task for uploading detections to the central server.
The task handles retry logic with progressive backoff and updates detection status.

Note: Celery tasks run in separate worker processes, so they create their own
      database sessions using SessionLocal (not the FastAPI dependency injection).

Author: ANPR Team
Created: 2025
"""

from pathlib import Path
import httpx

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.detection_repository import DetectionRepository


@celery_app.task(
    bind=True,
    max_retries=settings.MAX_RETRIES,
    default_retry_delay=5,
    name='app.tasks.upload_detection'
)
def upload_detection_task(
    self,
    detection_id: int,
    camera_id: int,
    camera_name: str,
    object_track_id: str,
    object_class: str,
    image_path: str,
    organization_id: int,
    activity_type: str = None,
    created_at: str = None
):
    """
    Upload detection with image to central server

    This is the main upload task that runs in the background (Celery worker).
    When a detection is created by the RTSP worker, this task is queued to
    upload it to the central server.

    Progressive Retry Strategy:
    - Retry 1: Wait 5 seconds before retry
    - Retry 2: Wait 1 minute before retry
    - Retry 3: Wait 5 minutes before retry
    - Retry 4: Wait 1 hour before retry

    After all retries fail, the detection stays in database as "not uploaded"
    and can be retried later.

    Args:
        detection_id: The detection ID in local database
        camera_id: The camera ID
        camera_name: The camera name
        object_track_id: Unique object tracking UUID
        object_class: Object class (car, truck, person, etc.)
        image_path: Full path to the detection image file
        organization_id: Organization ID
        activity_type: Activity direction ('in' or 'out')
        created_at: Detection timestamp (string format)

    Returns:
        dict: Upload result with central server detection ID

    Raises:
        Exception: If upload fails, triggers automatic retry

    Example:
        # Queue upload task (called by RTSP worker after detection)
        upload_detection_task.delay(
            detection_id=123,
            camera_id=1,
            camera_name="Gate Camera",
            object_track_id="550e8400-...",
            object_class="car",
            image_path="/detections/image.jpg",
            organization_id=1,
            activity_type="in",
            created_at="2025-01-02 12:30:45.123456"  # Sent as 'detected_at' in payload
        )
    """
    # Check if central server uploads are enabled
    if not settings.CENTRAL_SERVER_ENABLED:
        print(f"⊘ Central server uploads disabled - skipping detection {detection_id}")
        return {"skipped": True, "reason": "Central server uploads disabled"}

    # Create database session for this task
    # (Celery workers run in separate processes, need their own sessions)
    db = SessionLocal()

    try:
        detection_repo = DetectionRepository(db)

        # Step 1: Validate detection exists in database
        detection = detection_repo.get_by_id(detection_id)
        if not detection:
            print(f"✗ Detection {detection_id} not found in database")
            return {"error": "Detection not found"}

        # Step 2: Check if already uploaded (avoid duplicate uploads)
        if detection.uploaded:
            print(f"✓ Detection {detection_id} already uploaded (Central ID: {detection.central_detection_id})")
            return {
                "already_uploaded": True,
                "central_id": detection.central_detection_id
            }

        # Step 3: Validate image file exists on disk
        image_file = Path(image_path)
        if not image_file.exists():
            error_msg = f"Image file not found: {image_path}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)

        # Step 4: Prepare multipart upload request
        with open(image_path, 'rb') as f:
            files = {
                'image': (image_file.name, f, 'image/jpeg')
            }
            # Map fields to match central server API expectations
            data = {
                'client_detection_id': f"{camera_id}-{detection_id}",
                'camera_id': str(camera_id),
                'camera_name': camera_name,
                'vehicle_class': object_class,  # Central server uses vehicle_class
                'vehicle_track_id': object_track_id,  # Central server uses vehicle_track_id
                'organization_id': str(organization_id),
                'activity_type': activity_type if activity_type else 'in',  # Activity direction: 'in' or 'out'
                'detected_at': created_at  # Detection timestamp
            }
            headers = {
                'x-api-token': settings.CENTRAL_SERVER_API_KEY
            }

            # Step 5: Upload to central server
            response = httpx.post(
                settings.CENTRAL_SERVER_URL,
                files=files,
                data=data,
                headers=headers,
                timeout=settings.CENTRAL_SERVER_TIMEOUT
            )

        # Step 6: Handle response
        if response.status_code in [200, 201]:
            # Success! Parse response to get central server's detection ID
            result = response.json()
            central_detection_id = result.get('detection_id') or result.get('id')

            # Update local detection as uploaded
            detection_repo.mark_as_uploaded(
                detection_id=detection_id,
                central_detection_id=central_detection_id
            )

            print(f"✓ Uploaded detection {detection_id} to central server (Central ID: {central_detection_id})")

            return {
                "success": True,
                "detection_id": detection_id,
                "central_detection_id": central_detection_id
            }
        else:
            # Upload failed - raise exception to trigger retry
            error_msg = f"Upload failed: {response.status_code} - {response.text}"
            raise Exception(error_msg)

    except Exception as e:
        # Upload failed - handle retry logic

        # Increment retry count in database for tracking
        if 'detection_repo' in locals():
            detection_repo.increment_retry_count(detection_id)

        # Calculate progressive retry delay
        retry_attempt = self.request.retries
        delay = (
            settings.retry_delays[retry_attempt]
            if retry_attempt < len(settings.retry_delays)
            else settings.retry_delays[-1]
        )

        print(f"✗ Upload failed for detection {detection_id} (attempt {retry_attempt + 1}/{settings.MAX_RETRIES + 1}): {e}")
        print(f"  → Retrying in {delay}s...")

        # Retry with progressive backoff
        raise self.retry(exc=e, countdown=delay)

    finally:
        # Always close the database session
        db.close()
