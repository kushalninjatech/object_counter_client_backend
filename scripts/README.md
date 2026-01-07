# ANPR Client Backend - Scripts

This directory contains shell scripts for managing the ANPR Client Backend services.

## 📋 Available Scripts

### 🚀 setup.sh
**Initial setup and installation**

```bash
./scripts/setup.sh
```

**What it does:**
- Checks Python installation
- Installs `uv` (fast Python package installer)
- Creates virtual environment
- Installs all dependencies
- Downloads YOLOv8 model
- Creates required directories (logs, detections)
- Sets up `.env` configuration file
- Starts Docker services (PostgreSQL + Redis)

**When to use:** Run once during initial project setup, or if dependencies change.

---

### ▶️ start.sh
**Start all services**

```bash
# Foreground mode (shows logs, Ctrl+C stops everything)
./scripts/start.sh

# Background/daemon mode
./scripts/start.sh -d

# Follow logs (after starting in daemon mode)
./scripts/start.sh -f
```

**What it does:**
- Activates virtual environment
- Stops any existing processes
- Starts Docker services (PostgreSQL + Redis)
- Starts Celery Worker (background task processing)
- Starts Flower (Celery monitoring at http://localhost:5555)
- Starts FastAPI (API server at http://localhost:8000)

**Options:**
- `-d, --daemon` - Run in background mode
- `-f, --follow` - Follow logs (use after starting with `-d`)

---

### ⏹️ stop.sh
**Stop all services**

```bash
./scripts/stop.sh
```

**What it does:**
- Stops FastAPI server
- Stops Celery Worker
- Stops Flower
- Stops Docker services (PostgreSQL + Redis)

**When to use:** To cleanly shut down all services.

---

### 📊 status.sh
**Check service status**

```bash
./scripts/status.sh
```

**What it does:**
- Shows status of Docker services
- Shows status of FastAPI (with PID and URL)
- Shows status of Celery Worker (with PID)
- Shows status of Flower (with PID and URL)
- Performs API health check

**Output example:**
```
✓ FastAPI Running (PID: 12345)
  URL: http://localhost:8000/docs
✓ Celery Worker Running (PID: 12346)
✓ API is healthy
```

---

### 📝 logs.sh
**View service logs**

```bash
# View all logs (combined)
./scripts/logs.sh

# View specific service logs
./scripts/logs.sh api
./scripts/logs.sh celery
./scripts/logs.sh flower
```

**What it does:**
- Displays real-time logs using `tail -f`
- Press Ctrl+C to stop viewing (services keep running)

**Log files location:** `logs/` directory
- `logs/api.log` - FastAPI server logs
- `logs/celery.log` - Celery worker logs
- `logs/flower.log` - Flower dashboard logs

---

## 🎯 Common Workflows

### First Time Setup
```bash
# 1. Run setup
./scripts/setup.sh

# 2. Edit configuration
nano .env

# 3. Start services
./scripts/start.sh
```

### Daily Development
```bash
# Start services in background
./scripts/start.sh -d

# Check everything is running
./scripts/status.sh

# View logs if needed
./scripts/logs.sh api

# Stop when done
./scripts/stop.sh
```

### Debugging Issues
```bash
# Check service status
./scripts/status.sh

# View all logs in real-time
./scripts/logs.sh

# Restart services
./scripts/stop.sh
./scripts/start.sh
```

---

## 🔧 Technical Details

### Script Execution
All scripts automatically change to the project root directory, so they work correctly when called from anywhere:

```bash
# All of these work
./scripts/start.sh
cd scripts && ./start.sh
bash scripts/start.sh
```

### Dependencies
- **Python 3.8+** - Application runtime
- **Docker & docker-compose** - Database and cache services
- **uv** - Fast Python package installer (auto-installed by setup.sh)
- **Virtual environment** - Isolated Python environment

### Service URLs
- **API Documentation:** http://localhost:8000/docs
- **API Health Check:** http://localhost:8000/health
- **Flower Dashboard:** http://localhost:5555

### Ports Used
- `8000` - FastAPI server
- `5555` - Flower (Celery monitoring)
- `5432` - PostgreSQL (Docker)
- `6379` - Redis (Docker)

---

## 🚨 Troubleshooting

### Services won't start
```bash
# Check if ports are already in use
lsof -i :8000
lsof -i :5555

# Stop any existing processes
./scripts/stop.sh

# Try starting again
./scripts/start.sh
```

### Virtual environment not found
```bash
# Re-run setup
./scripts/setup.sh
```

### Docker services not starting
```bash
# Check Docker is running
docker ps

# Check docker-compose status
docker-compose ps

# Restart Docker services
docker-compose down
docker-compose up -d
```

### Permission denied
```bash
# Make scripts executable
chmod +x scripts/*.sh
```

---

## 📚 Additional Resources

- **Main README:** See project root for application documentation
- **API Documentation:** http://localhost:8000/docs (when running)
- **.env Configuration:** See `.env.example` for all available settings

---

## 💡 Tips

1. **Always use foreground mode during development** to see logs immediately
2. **Use daemon mode for production** to run services in background
3. **Check status regularly** to ensure all services are healthy
4. **Review logs** if you encounter errors or unexpected behavior
5. **Edit .env file** to configure RTSP transport (udp/tcp) and other settings
