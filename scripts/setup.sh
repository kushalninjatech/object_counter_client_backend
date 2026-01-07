#!/bin/bash
# ============================================
# ANPR Client Backend - Setup Script
# ============================================
#
# USAGE:
#   ./scripts/setup.sh
#
# DESCRIPTION:
#   Initial setup script that:
#   1. Checks Python installation
#   2. Installs uv (fast Python package installer)
#   3. Creates Python virtual environment
#   4. Installs all dependencies
#   5. Downloads YOLO model
#   6. Creates required directories
#   7. Sets up .env configuration file
#   8. Starts Docker services (PostgreSQL + Redis)
#
# REQUIREMENTS:
#   - Python 3.8+ installed
#   - Docker and docker-compose installed
#   - Internet connection (for downloading dependencies)
#
# NOTES:
#   - Script must be run from project root: ./scripts/setup.sh
#   - Run this script ONCE during initial setup
#   - Safe to re-run if setup was interrupted
#   - After setup, use ./scripts/start.sh to run services
#
# ============================================

set -e

# Change to project root directory (parent of scripts/)
cd "$(dirname "$0")/.."

echo "======================================"
echo "ANPR Client Backend - Setup"
echo "======================================"

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"

# Install uv (fast Python package installer)
echo ""
echo "Installing uv..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✓ uv installed"
else
    echo "✓ uv already installed"
fi

# Create virtual environment using uv
echo ""
echo "Creating virtual environment..."
uv venv .venv
echo "✓ Virtual environment created"

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies using uv (much faster than pip)
echo ""
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt
echo "✓ Dependencies installed"

# Download YOLO model
echo ""
echo "Downloading YOLO model..."
mkdir -p models
if [ ! -f "models/yolov8n.pt" ]; then
    curl -L https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -o models/yolov8n.pt
    echo "✓ YOLOv8 nano model downloaded"
else
    echo "✓ YOLO model already exists"
fi

# Create directories
echo ""
echo "Creating required directories..."
mkdir -p detections
mkdir -p logs
echo "✓ Directories created"

# Copy environment file
echo ""
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ .env file created from .env.example"
        echo "  Please update .env with your settings"
    else
        echo "⚠ .env.example not found, please create .env manually"
    fi
else
    echo "✓ .env file already exists"
fi

# Start Docker services
echo ""
echo "Starting PostgreSQL and Redis..."
docker-compose up -d
echo "✓ Docker services started"

# Wait for services to be healthy
echo ""
echo "Waiting for services to be healthy..."
sleep 5

# Check PostgreSQL
echo "Checking PostgreSQL..."
docker-compose exec -T postgres pg_isready -U anpr_user || echo "⚠ PostgreSQL not ready yet, please wait..."

# Check Redis
echo "Checking Redis..."
docker-compose exec -T redis redis-cli ping || echo "⚠ Redis not ready yet, please wait..."

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "   - Update CENTRAL_SERVER_URL and CENTRAL_SERVER_API_KEY"
echo "   - Set ORGANIZATION_ID"
echo "   - Configure RTSP_TRANSPORT (udp or tcp)"
echo ""
echo "2. Activate virtual environment:"
echo "   source .venv/bin/activate"
echo ""
echo "3. Start all services:"
echo "   ./scripts/start.sh"
echo ""
echo "Service URLs:"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Flower Dashboard:  http://localhost:5555"
echo ""
echo "Other commands:"
echo "  ./scripts/status.sh  # Check service status"
echo "  ./scripts/logs.sh    # View logs"
echo "  ./scripts/stop.sh    # Stop all services"
echo ""
echo "======================================"
