#!/bin/bash
# ANPR Client Backend - Setup Script
# Installs uv and sets up Python virtual environment

set -e

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
    cp .env.example .env
    echo "✓ .env file created (please update with your settings)"
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
echo "1. Edit .env file with your settings"
echo "2. Run 'source .venv/bin/activate' to activate virtual environment"
echo "3. Run './start_api.sh' to start the FastAPI server"
echo "4. Run './start_celery.sh' in another terminal to start Celery worker"
echo ""
echo "API will be available at: http://localhost:8000/docs"
echo "======================================"
