# Vehicle Detection Implementation

This document describes the implementation of the POC vehicle detection system into the backend worker.

## Overview

The vehicle detection system from the POC has been successfully integrated into the backend worker. It now features:

- **Directional counting** using cross-product algorithm
- **ROI-based detection** with polygon filtering
- **Trajectory tracking** for each vehicle
- **Optional visualization window** for debugging
- **Automatic image saving** when vehicles cross the detection line

## New Features

### 1. VehicleDetectionService

A new service class that encapsulates all detection logic:

**Location**: `app/services/vehicle_detection_service.py`

**Key Features**:
- YOLOv8 detection with BoT-SORT tracking
- Single-line directional counting (IN/OUT)
- ROI polygon filtering using ray-casting algorithm
- Trajectory visualization (last 30 positions)
- Optional OpenCV window display
- Automatic vehicle image cropping and saving

### 2. Geometry Utilities

**Location**: `app/utils/geometry.py`

Provides geometric operations:
- `point_in_polygon()` - Ray casting algorithm
- `get_centroid()` - Calculate bounding box center
- `get_bottom_center()` - Calculate bottom-center point
- `crop_frame_to_roi()` - Optimize detection area

### 3. Line Crossing Detection

**Location**: `app/utils/line_crossing.py`

Implements the `SingleLineCrossingDetector` class:
- Cross-product method for line crossing detection
- Direction determination (IN vs OUT)
- Works with any line orientation

## How It Works

### Detection Pipeline

```
Video Frame
    ↓
Crop to ROI (optimization)
    ↓
YOLOv8 Detection + Tracking
    ↓
Filter by ROI Polygon
    ↓
Track Vehicle Position
    ↓
Check Line Crossing
    ↓
Determine Direction (IN/OUT)
    ↓
Save Detection + Image
    ↓
Store in Database + Queue Upload
```

### Key Algorithms

#### 1. Cross Product Line Crossing

```python
# Determine which side of line a point is on
cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)

# If cross > 0: left side
# If cross < 0: right side
# If signs differ between prev and curr: crossing occurred
```

#### 2. Ray Casting (Point in Polygon)

```python
# Cast horizontal ray from point
# Count polygon edge intersections
# Odd count = inside, Even count = outside
```

## Usage

### Starting a Worker with Visualization

**API Endpoint**: `POST /api/v1/workers/cameras/{camera_id}/start`

**Parameters**:
- `camera_id` (required): The camera ID
- `show_window` (optional): Show detection window (default: false)

**Example 1: Start worker without window**
```bash
curl -X POST "http://localhost:8000/api/v1/workers/cameras/1/start"
```

**Example 2: Start worker with visualization window (for debugging)**
```bash
curl -X POST "http://localhost:8000/api/v1/workers/cameras/1/start?show_window=true"
```

**Example 3: Using Python requests**
```python
import requests

# Start with window display
response = requests.post(
    "http://localhost:8000/api/v1/workers/cameras/1/start",
    params={"show_window": True}
)
print(response.json())
```

### Response Format

```json
{
    "message": "Worker started successfully for camera 'Gate Camera'",
    "camera_id": 1,
    "camera_name": "Gate Camera",
    "worker_running": true,
    "show_window": true
}
```

## Visualization Window

When `show_window=true`, an OpenCV window displays:

- **Bounding boxes** with tracking IDs
- **ROI polygon** (green, semi-transparent)
- **Detection line** (blue, thick)
- **Vehicle trajectories** (orange polylines)
- **Count statistics** (IN/OUT at top)
- **Vehicle states**:
  - Yellow box: Not yet counted
  - Green box + [IN]: Counted as entering
  - Orange box + [OUT]: Counted as exiting

### Closing the Window

The window will automatically close when the worker stops.

**Stop worker**:
```bash
curl -X POST "http://localhost:8000/api/v1/workers/cameras/1/stop"
```

## Differences from POC

| Feature | POC | Backend Worker |
|---------|-----|----------------|
| **Input** | MP4 file | RTSP/HTTP stream |
| **Tracking** | BoT-SORT | BoT-SORT (same) |
| **Counting** | Instant on crossing | Instant on crossing (same) |
| **Direction** | Cross product | Cross product (same) |
| **Saving** | 1 image per vehicle | 1 image per vehicle (same) |
| **UI** | Always displays | Optional (show_window param) |
| **Storage** | Local files only | Database + Celery upload queue |
| **Threading** | Main thread | Daemon thread per camera |
| **Reconnection** | None | Auto-reconnect on failure |

## Configuration

All settings are managed through the camera configuration in the database:

- `roi_polygon`: List of [x, y] coordinates defining detection area
- `detection_line`: [x1, y1, x2, y2] - line for counting
- `target_fps`: Frames per second to process
- `confidence`: Detection confidence threshold (0.0-1.0)

## Output Files

### Vehicle Images

**Location**: `detections/` directory

**Filename Format**: `{uuid}_{direction}.jpg`

**Example**: `550e8400-e29b-41d4-a716-446655440000_in.jpg`

**Content**: Cropped bounding box of the detected vehicle

## Database Storage

Each detection is stored with:
- `camera_id` and `camera_name`
- `object_track_id` (UUID)
- `object_class` (car, motorcycle, etc.)
- `image_path`
- `uploaded` status

## Console Output

The worker prints detailed logs:

```
✅ Vehicle ID:45 COUNTED as IN at position (640, 360)
   📊 Total IN: 12 | Total OUT: 8
```

```
[Gate Camera] Frame 120 | IN: 12 | OUT: 8
```

```
[Gate Camera] ✓ SAVED: car [IN] - 550e8400 | Queued for upload
```

## Performance Optimizations

1. **ROI Cropping**: Only process region of interest (~50-70% speedup)
2. **Frame Skipping**: Process at target FPS instead of full stream FPS
3. **Efficient Tracking**: Deque-based trajectory storage (O(1) operations)
4. **Vectorized Operations**: NumPy for batch processing

## Troubleshooting

### Window Not Showing

- Ensure you're running the backend on a system with display (not headless server)
- Check that `show_window=true` is passed in the request
- Verify OpenCV is installed with GUI support: `pip install opencv-python`

### No Detections

- Check ROI polygon covers the area of interest
- Verify detection line is positioned correctly
- Lower confidence threshold if needed
- Check camera stream is working

### Worker Crashes

- Check logs for error messages
- Verify YOLO model file exists at `MODEL_PATH`
- Ensure sufficient memory for YOLO inference
- Check stream URL is accessible

## Testing

To test the implementation:

1. **Create a camera** with ROI and detection line configured
2. **Start the worker** with window display:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/workers/cameras/1/start?show_window=true"
   ```
3. **Verify the window opens** showing the live feed
4. **Observe vehicles being detected** and counted
5. **Check the database** for saved detections
6. **Stop the worker**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/workers/cameras/1/stop"
   ```

## Future Enhancements

Potential improvements:

- [ ] Web-based visualization (WebSocket streaming)
- [ ] Configurable trajectory length
- [ ] Multiple detection lines per camera
- [ ] Speed estimation based on trajectory
- [ ] Vehicle type classification refinement
- [ ] Heatmap generation for traffic analysis

## Support

For issues or questions, refer to:
- Vehicle Counter POC README: `vehicle counter poc/README.md`
- Backend API documentation: Swagger UI at `/docs`
- Geometry utilities: `app/utils/geometry.py`
- Detection service: `app/services/vehicle_detection_service.py`
