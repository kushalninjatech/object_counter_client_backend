# Stream Type Implementation

This document describes the implementation of the `stream_type` enum field for camera orientation support.

## Overview

The `stream_type` field has been added to the camera model to support different camera mounting orientations. This allows the system to properly handle cameras that are mounted upside-down or in normal orientation.

## Changes Made

### 1. Database Model (`app/models/camera.py`)

**Added StreamType Enum**:
```python
class StreamType(str, enum.Enum):
    """Enum for camera stream orientation type"""
    UPSIDE_DOWN = "upside-down"
    DOWNSIDE_UP = "downside-up"
```

**Added Column to Camera Model**:
```python
stream_type = Column(
    Enum(StreamType),
    default=StreamType.DOWNSIDE_UP,
    nullable=False,
    comment="Stream orientation: upside-down or downside-up (normal)"
)
```

### 2. API Schemas (`app/schemas/camera.py`)

**Updated CameraBase**:
```python
stream_type: StreamType = Field(
    default=StreamType.DOWNSIDE_UP,
    description="Stream orientation: upside-down or downside-up"
)
```

**Updated CameraUpdate**:
```python
stream_type: Optional[StreamType] = None
```

### 3. Camera Service (`app/services/camera_service.py`)

**Updated create_camera method**:
- Added `stream_type` parameter with default value `StreamType.DOWNSIDE_UP`
- Passes `stream_type` to repository create method

**Method Signature**:
```python
def create_camera(
    self,
    name: str,
    stream_url: str,
    roi_polygon: List[List[int]],
    detection_line: List[int],
    stream_type: StreamType = StreamType.DOWNSIDE_UP,  # NEW
    target_fps: int = 3,
    confidence: float = 0.3,
    organization_id: int = 1
) -> Camera:
```

### 4. Database Migration

**Migration Files Created**:
- `migrations/add_stream_type_to_cameras.sql` - SQL migration script
- `migrations/run_migration.py` - Python migration runner
- `migrations/README.md` - Migration documentation

**Migration Contents**:
1. Creates `streamtype` PostgreSQL enum
2. Adds `stream_type` column to `cameras` table
3. Sets default value to 'downside-up'
4. Updates existing records

## Usage

### Creating a Camera with Stream Type

**Example 1: Normal orientation (default)**
```python
from app.models.camera import StreamType

camera = camera_service.create_camera(
    name="Gate Camera",
    stream_url="rtsp://admin:pass@192.168.1.100/stream",
    roi_polygon=[[100, 100], [500, 100], [500, 400], [100, 400]],
    detection_line=[200, 250, 400, 250],
    stream_type=StreamType.DOWNSIDE_UP,  # Normal orientation
    target_fps=3,
    confidence=0.7,
    organization_id=1
)
```

**Example 2: Upside-down camera**
```python
camera = camera_service.create_camera(
    name="Ceiling Camera",
    stream_url="rtsp://admin:pass@192.168.1.101/stream",
    roi_polygon=[[100, 100], [500, 100], [500, 400], [100, 400]],
    detection_line=[200, 250, 400, 250],
    stream_type=StreamType.UPSIDE_DOWN,  # Mounted upside-down
    target_fps=3,
    confidence=0.7,
    organization_id=1
)
```

### API Requests

**Create Camera**:
```bash
curl -X POST "http://localhost:8000/api/v1/cameras" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gate Camera",
    "stream_url": "rtsp://admin:pass@192.168.1.100/stream",
    "stream_type": "downside-up",
    "roi_polygon": [[100, 100], [500, 100], [500, 400], [100, 400]],
    "detection_line": [200, 250, 400, 250],
    "target_fps": 3,
    "confidence": 0.7,
    "organization_id": 1
  }'
```

**Update Camera Stream Type**:
```bash
curl -X PATCH "http://localhost:8000/api/v1/cameras/1" \
  -H "Content-Type: application/json" \
  -d '{
    "stream_type": "upside-down"
  }'
```

### Swagger UI

1. Navigate to `http://localhost:8000/docs`
2. Find `POST /api/v1/cameras`
3. In the request body, set `stream_type` to either:
   - `"upside-down"`
   - `"downside-up"`

## Enum Values

| Value | Description | Use Case |
|-------|-------------|----------|
| `downside-up` | Normal camera orientation | Standard mounted cameras, ground-level cameras |
| `upside-down` | Inverted camera orientation | Ceiling-mounted cameras, inverted installations |

## Running the Migration

### Step 1: Backup Database (Recommended)

```bash
pg_dump -U your_username anpr_client_db > backup_before_stream_type.sql
```

### Step 2: Run Migration

```bash
cd /home/user/Documents/Projects/anpr_client_v2_fe_be/anpr_client_backend
python migrations/run_migration.py
```

### Step 3: Verify Migration

```bash
# Connect to database
psql -U your_username -d anpr_client_db

# Check enum type
SELECT * FROM pg_type WHERE typname = 'streamtype';

# Check column
\d cameras

# Check data
SELECT id, name, stream_type FROM cameras;
```

Expected output:
- All existing cameras will have `stream_type = 'downside-up'`

## Implementation Notes

### Default Behavior

- **Default value**: `downside-up` (normal orientation)
- **Required**: Yes (NOT NULL constraint)
- **Backward compatibility**: All existing cameras default to `downside-up`

### Future Enhancements

The stream_type field enables future functionality:
- Automatic frame rotation for upside-down cameras
- Proper orientation of ROI polygons
- Correct detection line positioning
- Accurate vehicle counting direction

### Database Schema

```sql
-- Enum type
CREATE TYPE streamtype AS ENUM ('upside-down', 'downside-up');

-- Column definition
stream_type streamtype DEFAULT 'downside-up' NOT NULL
```

## Troubleshooting

### Error: "type streamtype already exists"

The migration is idempotent. This is normal if running the migration multiple times.

### Error: "column stream_type already exists"

The migration includes `IF NOT EXISTS` checks. This error shouldn't occur, but if it does, the column already exists.

### Verifying the Implementation

```python
# Test in Python
from app.models.camera import Camera, StreamType

# Check if enum works
print(StreamType.UPSIDE_DOWN)  # Output: upside-down
print(StreamType.DOWNSIDE_UP)  # Output: downside-up

# Create a camera (will use default: downside-up)
camera = Camera(
    name="Test Camera",
    stream_url="rtsp://test",
    roi_polygon=[[0,0], [100,0], [100,100]],
    detection_line=[50, 0, 50, 100],
    organization_id=1
)

print(camera.stream_type)  # Output: StreamType.DOWNSIDE_UP
```

## Rollback

If you need to remove this feature:

```sql
-- Remove column
ALTER TABLE cameras DROP COLUMN stream_type;

-- Drop enum type
DROP TYPE streamtype;
```

Then revert the code changes in:
- `app/models/camera.py`
- `app/schemas/camera.py`
- `app/services/camera_service.py`

## Summary

The stream_type field implementation is now complete:

✅ Database model updated with StreamType enum
✅ API schemas include stream_type field
✅ Camera service handles stream_type on create/update
✅ Database migration scripts created
✅ Documentation provided
✅ Default value set for backward compatibility

The system is now ready to support cameras with different mounting orientations!
