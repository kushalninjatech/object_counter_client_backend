#!/bin/bash
# ============================================
# View logs for ANPR Client Backend services
# ============================================
#
# USAGE:
#   ./scripts/logs.sh           # Show all logs (combined)
#   ./scripts/logs.sh api       # Show only API logs
#   ./scripts/logs.sh celery    # Show only Celery logs
#   ./scripts/logs.sh flower    # Show only Flower logs
#
# DESCRIPTION:
#   Displays real-time logs from running services using tail -f.
#   Press Ctrl+C to stop viewing logs.
#
# NOTES:
#   - Script must be run from project root: ./scripts/logs.sh
#   - Services must be running and logs directory must exist
#   - Logs are stored in logs/ directory
#
# EXAMPLES:
#   ./scripts/logs.sh           # View all logs together
#   ./scripts/logs.sh api       # View only API logs
#   ./scripts/logs.sh celery    # View only Celery worker logs
#
# ============================================

# Change to project root directory (parent of scripts/)
cd "$(dirname "$0")/.."

LOG_DIR="logs"

# Check if logs directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo "Error: Logs directory not found"
    echo "Make sure services have been started at least once."
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
