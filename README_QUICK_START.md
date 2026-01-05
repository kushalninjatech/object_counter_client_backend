# ANPR Client Backend - Quick Start Guide

Complete industry-standard backend with proper separation of concerns.

## 🚀 Quick Setup (5 minutes)

### 1. Install Prerequisites

```bash
# macOS
brew install python@3.11 docker

# Ubuntu/Debian
sudo apt-get install python3.11 python3.11-venv docker-compose
```

### 2. Run Setup

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup (installs uv, creates venv, downloads YOLO model, starts Docker)
./setup.sh
```

### 3. Configure Environment

```bash
# Edit .env file with your settings
nano .env

# Important settings:
# - CENTRAL_SERVER_URL: Your central server endpoint
# - CENTRAL_SERVER_API_KEY: Your API key
```

### 4. Start Application

```bash
# Start all services (API + Celery + Flower)
./start.sh
```

**That's it!** 🎉

- **API Docs**: http://localhost:8000/docs
- **Flower (Celery Monitoring)**: http://localhost:5555

## 📝 Available Commands

```bash
./setup.sh      # Initial setup
./start.sh      # Start all services
./stop.sh       # Stop all services
./status.sh     # Check service status
```

## 🎯 Next Steps

### 1. Add a Camera

```bash
curl -X POST "http://localhost:8000/api/v1/cameras" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gate Camera 1",
    "stream_url": "rtsp://admin:password@192.168.1.100:554/stream",
    "roi_polygon": [[100, 100], [500, 100], [500, 400], [100, 400]],
    "detection_line": [200, 250, 400, 250],
    "target_fps": 3,
    "confidence": 0.7
  }'
```

### 2. Start Worker for Camera

```bash
# Start worker for camera ID 1
curl -X POST "http://localhost:8000/api/v1/workers/cameras/1/start"
```

### 3. View Detections

```bash
# Get all detections
curl "http://localhost:8000/api/v1/detections"

# Or visit: http://localhost:8000/docs
```

## 📊 Architecture Overview

```
┌─────────────────────────────────────────┐
│         Application Layer               │
├─────────────────────────────────────────┤
│  FastAPI (Port 8000)                    │
│  - Camera Management API                │
│  - Detection Query API                  │
│  - Worker Control API                   │
├─────────────────────────────────────────┤
│  Celery Worker                          │
│  - Upload detections to central server  │
│  - Progressive retry (5s, 1m, 5m, 1h)  │
├─────────────────────────────────────────┤
│  Flower (Port 5555)                     │
│  - Celery monitoring UI                 │
└─────────────────────────────────────────┘
           ↓                   ↓
┌────────────────┐    ┌────────────────┐
│  PostgreSQL    │    │     Redis      │
│  (Port 5432)   │    │  (Port 6379)   │
│  - Docker      │    │  - Docker      │
└────────────────┘    └────────────────┘
```

## 🗂️ Project Structure

```
app/
├── api/v1/endpoints/    # API routes
│   ├── cameras.py       # Camera CRUD
│   ├── detections.py    # Detection queries
│   └── workers.py       # Worker control
├── core/                # Configuration
├── db/                  # Database setup
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
├── repositories/        # Data access layer
├── services/            # Business logic
├── tasks/               # Celery tasks
└── workers/             # RTSP workers
```

## 🔍 Service Details

### FastAPI (Port 8000)
- Camera CRUD operations
- Detection queries with filtering
- Worker start/stop control
- Frame capture for ROI configuration
- Statistics and analytics

### Celery Worker
- Background upload tasks
- Progressive retry: 5s → 1m → 5m → 1h
- Automatic failure tracking
- Batch retry support

### Flower (Port 5555)
- Monitor Celery tasks
- View task history
- Check worker status
- Inspect failed tasks

### PostgreSQL (Port 5432)
- Stores cameras and detections
- Optimized with indexes
- Connection pooling

### Redis (Port 6379)
- Celery message broker
- Task result backend
- Fast in-memory caching

## 📋 Common Tasks

### View Logs

```bash
# API logs (shown in terminal)
# Celery logs
tail -f logs/celery.log

# Flower logs
tail -f logs/flower.log

# Docker logs
docker-compose logs -f
```

### Check Status

```bash
./status.sh
```

### Restart Services

```bash
./stop.sh
./start.sh
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U anpr_user -d anpr_client_db

# Backup
docker-compose exec postgres pg_dump -U anpr_user anpr_client_db > backup.sql
```

### Redis Access

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# View all keys
docker-compose exec redis redis-cli KEYS '*'
```

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check if ports are in use
lsof -i :8000  # API
lsof -i :5555  # Flower
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Stop and retry
./stop.sh
./start.sh
```

### Worker Can't Connect to Camera

```bash
# Test RTSP stream
ffmpeg -i "rtsp://camera-url" -frames:v 1 test.jpg

# Check network
ping camera-ip
```

### Database Connection Failed

```bash
# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

## 📚 Documentation

- **Full Architecture**: [README.md](README.md)
- **Implementation Status**: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
- **API Documentation**: http://localhost:8000/docs

## 🆘 Support

1. Check logs: `./status.sh`
2. Review documentation
3. Check [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
4. Create GitHub issue with logs

---

**Version**: 1.0.0
**Author**: ANPR Team
**License**: MIT
