#!/bin/bash
# Start ANPR Client Backend (API + Celery + Flower)
#
# Usage:
#   ./start.sh          # Run in foreground (shows live logs, Ctrl+C stops everything)
#   ./start.sh -d       # Run in background (detached mode)
#   ./start.sh -f       # Follow logs (use after starting with -d)

set -e

# Parse arguments
DAEMON_MODE=false
FOLLOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--daemon)
            DAEMON_MODE=true
            shift
            ;;
        -f|--follow)
            FOLLOW_LOGS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./start.sh [-d|--daemon] [-f|--follow]"
            exit 1
            ;;
    esac
done

echo "======================================"
echo "ANPR Client Backend - Starting All Services"
echo "======================================"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "✗ Virtual environment not found. Run ./setup.sh first"
    exit 1
fi

# Stop any existing processes
echo ""
echo "Checking for existing processes..."

# Stop API (uvicorn)
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "Stopping existing API..."
    pkill -f "uvicorn app.main:app" || true
    sleep 2
fi

# Stop Celery worker
if pgrep -f "celery.*worker" > /dev/null; then
    echo "Stopping existing Celery worker..."
    pkill -f "celery.*worker" || true
    sleep 2
fi

# Stop Flower
if pgrep -f "celery.*flower" > /dev/null; then
    echo "Stopping existing Flower..."
    pkill -f "celery.*flower" || true
    sleep 2
fi

echo "✓ Old processes stopped"

# Start Docker services (PostgreSQL + Redis)
echo ""
echo "Starting Docker services (PostgreSQL + Redis)..."
if ! docker-compose ps | grep -q "Up"; then
    docker-compose up -d
    echo "Waiting for services to be ready..."
    sleep 5
fi
echo "✓ Docker services running"

# Create log directory
mkdir -p logs

# Start services in background
echo ""
echo "======================================"
echo "Starting Services..."
echo "======================================"

# 1. Start Celery Worker
echo ""
echo "[1/3] Starting Celery Worker..."
nohup celery -A app.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --max-tasks-per-child=1000 \
    > logs/celery.log 2>&1 &
CELERY_PID=$!
echo "✓ Celery Worker started (PID: $CELERY_PID)"
echo "  Log: logs/celery.log"
sleep 2

# 2. Start Flower (Celery Monitoring)
echo ""
echo "[2/3] Starting Flower (Celery Monitoring)..."
nohup celery -A app.tasks.celery_app flower \
    --port=5555 \
    > logs/flower.log 2>&1 &
FLOWER_PID=$!
echo "✓ Flower started (PID: $FLOWER_PID)"
echo "  URL: http://localhost:5555"
echo "  Log: logs/flower.log"
sleep 2

# 3. Start FastAPI
echo ""
echo "[3/3] Starting FastAPI API..."

# Handle -f (follow logs) mode
if [ "$FOLLOW_LOGS" = true ]; then
    echo ""
    echo "======================================"
    echo "Following logs (Ctrl+C to stop viewing)"
    echo "======================================"
    echo ""
    echo "Press Ctrl+C to stop viewing logs (services will keep running)"
    echo "To stop all services, run: ./stop.sh"
    echo ""

    # Tail both API and Celery logs
    tail -f logs/api.log logs/celery.log
    exit 0
fi

# Cleanup function to stop all services
cleanup() {
    echo ""
    echo "======================================"
    echo "Stopping all services..."
    echo "======================================"

    # Stop API
    if ps -p $API_PID > /dev/null 2>&1; then
        echo "Stopping FastAPI..."
        kill $API_PID 2>/dev/null || true
    fi

    # Stop Celery
    if ps -p $CELERY_PID > /dev/null 2>&1; then
        echo "Stopping Celery Worker..."
        kill $CELERY_PID 2>/dev/null || true
    fi

    # Stop Flower
    if ps -p $FLOWER_PID > /dev/null 2>&1; then
        echo "Stopping Flower..."
        kill $FLOWER_PID 2>/dev/null || true
    fi

    # Cleanup any remaining processes
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "celery.*worker" 2>/dev/null || true
    pkill -f "celery.*flower" 2>/dev/null || true

    # Stop Docker services
    echo "Stopping Docker services..."
    docker-compose down

    echo "✓ All services stopped"
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup SIGINT SIGTERM

if [ "$DAEMON_MODE" = true ]; then
    # Daemon mode: Start API in background
    nohup uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir app \
        --log-level info \
        > logs/api.log 2>&1 &
    API_PID=$!
    echo "✓ FastAPI started (PID: $API_PID)"
    echo "  URL: http://localhost:8000/docs"
    echo "  Log: logs/api.log"

    echo ""
    echo "======================================"
    echo "✓ All services started in background"
    echo "======================================"
    echo ""
    echo "Service URLs:"
    echo "  - API:    http://localhost:8000/docs"
    echo "  - Flower: http://localhost:5555"
    echo ""
    echo "Commands:"
    echo "  ./start.sh -f     # Follow logs"
    echo "  ./status.sh       # Check status"
    echo "  ./stop.sh         # Stop all services"
    echo ""
else
    # Foreground mode: Start API in background but show combined logs
    echo "  URL: http://localhost:8000/docs"
    echo "  Logs will be shown below (API + Celery combined)"
    echo "  Press Ctrl+C to stop all services"
    echo "======================================"
    echo ""

    uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir app \
        --log-level info \
        > logs/api.log 2>&1 &
    API_PID=$!

    # Give API a moment to start
    sleep 2

    # Tail both logs in foreground
    tail -f logs/api.log logs/celery.log
fi
