#!/bin/bash
# ============================================
# Stop all ANPR Client Backend services
# ============================================
#
# USAGE:
#   ./scripts/stop.sh
#
# DESCRIPTION:
#   Stops all running services for the ANPR Client Backend:
#   - FastAPI server
#   - Celery Worker
#   - Flower (Celery monitoring)
#   - Docker services (PostgreSQL + Redis)
#
# NOTES:
#   - Script must be run from project root: ./scripts/stop.sh
#   - Safe to run multiple times (won't error if services already stopped)
#   - Docker services will be stopped and containers removed
#
# ============================================

# Change to project root directory (parent of scripts/)
cd "$(dirname "$0")/.."

echo "======================================"
echo "Stopping ANPR Client Backend"
echo "======================================"

# Stop API (uvicorn)
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "Stopping API..."
    pkill -f "uvicorn app.main:app" || true
else
    echo "✓ API not running"
fi

# Stop Celery worker
if pgrep -f "celery.*worker" > /dev/null; then
    echo "Stopping Celery worker..."
    pkill -f "celery.*worker" || true
else
    echo "✓ Celery not running"
fi

# Stop Flower
if pgrep -f "celery.*flower" > /dev/null; then
    echo "Stopping Flower..."
    pkill -f "celery.*flower" || true
else
    echo "✓ Flower not running"
fi

# Stop Docker services
echo ""
echo "Stopping Docker services..."
docker-compose down

echo ""
echo "======================================"
echo "✓ All services stopped"
echo "======================================"
