# ANPR Client Backend - Industry Standard Architecture

A professionally structured FastAPI application for Automatic Number Plate Recognition (ANPR) client system with object detection capabilities.

## 🏗️ Architecture Overview

This application follows industry-standard layered architecture with clear separation of concerns:

```
app/
├── api/               # API layer (FastAPI routes)
│   └── v1/
│       ├── endpoints/ # Individual route modules
│       └── router.py  # Main API router
├── core/              # Core configurations
│   ├── config.py      # Application settings
│   ├── dependencies.py # Dependency injection
│   └── security.py    # Security utilities
├── db/                # Database layer
│   ├── base.py        # Base model imports
│   ├── session.py     # Session management
│   └── init_db.py     # Database initialization
├── models/            # SQLAlchemy ORM models
│   ├── base.py        # Abstract base model
│   ├── camera.py      # Camera model
│   └── detection.py   # Detection model
├── schemas/           # Pydantic schemas (validation)
│   ├── camera.py      # Camera request/response schemas
│   └── detection.py   # Detection request/response schemas
├── repositories/      # Data access layer
│   ├── base.py        # Base repository
│   ├── camera_repository.py
│   └── detection_repository.py
├── services/          # Business logic layer
│   ├── camera_service.py
│   ├── detection_service.py
│   └── worker_service.py
├── tasks/             # Celery tasks
│   ├── celery_app.py  # Celery configuration
│   └── upload_tasks.py # Upload task definitions
├── workers/           # Background workers
│   └── rtsp_worker.py # RTSP stream processing
└── main.py            # Application entrypoint
```

## 📋 Layer Responsibilities

### 1. **API Layer** (`app/api/`)
- Defines HTTP endpoints and routes
- Request validation using Pydantic schemas
- Response formatting
- **Depends on**: Services, Schemas

### 2. **Service Layer** (`app/services/`)
- Contains business logic
- Orchestrates between repositories and external services
- Handles complex workflows
- **Depends on**: Repositories, Schemas, Tasks

### 3. **Repository Layer** (`app/repositories/`)
- Data access abstraction
- Database queries and operations
- No business logic
- **Depends on**: Models

### 4. **Model Layer** (`app/models/`)
- SQLAlchemy ORM models
- Database table definitions
- Relationships between entities

### 5. **Schema Layer** (`app/schemas/`)
- Pydantic models for validation
- Request/response data structures
- Separate from database models

### 6. **Core Layer** (`app/core/`)
- Application configuration
- Dependency injection
- Security utilities

### 7. **Database Layer** (`app/db/`)
- Database connection management
- Session handling
- Initialization scripts

### 8. **Tasks Layer** (`app/tasks/`)
- Celery async tasks
- Background job definitions
- Upload retry logic

### 9. **Workers Layer** (`app/workers/`)
- RTSP stream processing
- Object detection
- Real-time video analysis

## 🔄 Data Flow

```
HTTP Request
    ↓
API Endpoint (FastAPI)
    ↓
Pydantic Schema Validation
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Data Access)
    ↓
SQLAlchemy Model
    ↓
PostgreSQL Database
    ↓
Response (back through layers)
```

## 🚀 Key Features

### Separation of Concerns
- Each layer has a single responsibility
- Easy to test and maintain
- Clear dependency flow

### Type Safety
- Full type hints throughout
- Pydantic validation
- SQLAlchemy typed models

### Scalability
- Connection pooling
- Async task processing (Celery)
- Indexed database queries

### Maintainability
- Comprehensive documentation
- Clear naming conventions
- Industry best practices

## 📦 Technology Stack

- **Web Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Validation**: Pydantic
- **Task Queue**: Celery + Redis
- **Object Detection**: YOLO (Ultralytics)
- **Video Processing**: OpenCV

## 🔧 Configuration

Configuration is managed through environment variables and Pydantic Settings:

```python
# app/core/config.py
class Settings(BaseSettings):
    DB_URL: str
    REDIS_URL: str
    MODEL_PATH: str
    # ... more settings
```

## 📝 Usage Examples

### Creating a Camera

```python
# Service Layer
camera_service = CameraService(db)
camera = camera_service.create_camera(
    name="Gate Camera 1",
    stream_url="rtsp://...",
    roi_polygon=[[0,0], [100,0], [100,100], [0,100]],
    detection_line=[50, 0, 50, 100]
)
```

### Querying Detections

```python
# Repository Layer
detection_repo = DetectionRepository(db)
failed_uploads = detection_repo.get_failed_uploads(max_retry_count=3)
```

## 🎯 Design Patterns Used

1. **Repository Pattern**: Abstracts data access
2. **Service Pattern**: Encapsulates business logic
3. **Dependency Injection**: Loose coupling between layers
4. **Factory Pattern**: Application creation
5. **Strategy Pattern**: Configurable behavior

## 📚 Further Reading

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/14/orm/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [YOLO Object Detection](https://docs.ultralytics.com/)

---

**Author**: ANPR Team
**Created**: 2025
**Version**: 1.0.0
