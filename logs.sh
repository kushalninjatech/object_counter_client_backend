#!/bin/bash
# View logs for ANPR Client Backend services
#
# Usage:
#   ./logs.sh           # Show all logs (combined)
#   ./logs.sh api       # Show only API logs
#   ./logs.sh celery    # Show only Celery logs
#   ./logs.sh flower    # Show only Flower logs

LOG_DIR="logs"

# Check if logs directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo "Error: Logs directory not found"
    exit 1
fi

case "${1:-all}" in
    api)
        echo "Following API logs (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/api.log"
        ;;
    celery)
        echo "Following Celery logs (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/celery.log"
        ;;
    flower)
        echo "Following Flower logs (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/flower.log"
        ;;
    all|*)
        echo "Following all logs (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/api.log" "$LOG_DIR/celery.log" "$LOG_DIR/flower.log"
        ;;
esac
