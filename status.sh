#!/bin/bash
# Check status of all services

echo "======================================"
echo "ANPR Client Backend - Service Status"
echo "======================================"

# Check Docker services
echo ""
echo "Docker Services:"
echo "----------------"
docker-compose ps

# Check API
echo ""
echo "FastAPI:"
echo "--------"
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    PID=$(pgrep -f "uvicorn app.main:app")
    echo "✓ Running (PID: $PID)"
    echo "  URL: http://localhost:8000/docs"
else
    echo "✗ Not running"
fi

# Check Celery
echo ""
echo "Celery Worker:"
echo "--------------"
if pgrep -f "celery.*worker" > /dev/null; then
    PID=$(pgrep -f "celery.*worker")
    echo "✓ Running (PID: $PID)"
    echo "  Log: logs/celery.log"
else
    echo "✗ Not running"
fi

# Check Flower
echo ""
echo "Flower:"
echo "-------"
if pgrep -f "celery.*flower" > /dev/null; then
    PID=$(pgrep -f "celery.*flower")
    echo "✓ Running (PID: $PID)"
    echo "  URL: http://localhost:5555"
    echo "  Log: logs/flower.log"
else
    echo "✗ Not running"
fi

# Health check
echo ""
echo "API Health Check:"
echo "-----------------"
if command -v curl &> /dev/null; then
    response=$(curl -s http://localhost:8000/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✓ API is healthy"
        echo "  Response: $response"
    else
        echo "✗ API not responding"
    fi
else
    echo "⚠ curl not found, cannot check API health"
fi

echo ""
echo "======================================"
