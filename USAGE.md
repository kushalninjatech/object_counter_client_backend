# ANPR Client Backend - Usage Guide

## Quick Start Commands

### Starting Services

```bash
# Run in foreground (shows live logs, Ctrl+C stops everything including Docker)
./start.sh

# Run in background (daemon mode)
./start.sh -d

# Follow logs after starting in daemon mode
./start.sh -f
# OR
./logs.sh
```

### Viewing Logs

```bash
# View all logs
./logs.sh

# View specific service logs
./logs.sh api      # API logs only
./logs.sh celery   # Celery logs only
./logs.sh flower   # Flower logs only
```

### Checking Status

```bash
./status.sh
```

### Stopping Services

```bash
./stop.sh  # Stops API, Celery, Flower, and Docker services
```

## Typical Workflows

### Development (with live logs)

```bash
# Start everything and see logs in real-time
./start.sh

# Press Ctrl+C to stop everything
```

When you run `./start.sh` without flags:
- ✅ Shows combined API + Celery logs
- ✅ Ctrl+C stops API, Celery, Flower, AND Docker Compose
- ✅ Perfect for development

### Production-like (background mode)

```bash
# Start in background
./start.sh -d

# Check if everything is running
./status.sh

# View logs
./logs.sh

# Or follow specific logs
./logs.sh api

# Stop when done
./stop.sh
```

## Service URLs

- **API**: http://localhost:8000/docs
- **Flower** (Celery monitoring): http://localhost:5555

## Log Files

All logs are stored in the `logs/` directory:
- `logs/api.log` - FastAPI application logs
- `logs/celery.log` - Celery worker logs
- `logs/flower.log` - Flower monitoring logs

## Troubleshooting

### Services won't start

```bash
# Stop everything first
./stop.sh

# Then start again
./start.sh
```

### Check what's running

```bash
./status.sh
```

### View recent errors

```bash
# Last 50 lines of each log
tail -50 logs/api.log
tail -50 logs/celery.log
```

### Clear old logs

```bash
# Truncate logs (keeps files but empties them)
> logs/api.log
> logs/celery.log
> logs/flower.log
```
