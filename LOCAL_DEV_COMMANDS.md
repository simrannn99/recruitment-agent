# Quick Start Commands - Local Development

## Step 1: Start PostgreSQL in Docker

```bash
docker-compose -f docker-compose.local.yml up -d postgres
```

## Step 2: Run Services Locally

### Option A: Using the start_services.py script (FastAPI + Django only)

```bash
python scripts/start_services.py
```

This will:
- Start FastAPI on port 8000 (background)
- Start Django on port 8001 (foreground)
- Press Ctrl+C to stop both

### Option B: Manual start (for more control)

**Terminal 1 - FastAPI:**
```bash
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Django (with WebSocket support):**
```bash
daphne -b 0.0.0.0 -p 8001 recruitment_backend.asgi:application
```

## Step 3: (Optional) Start Celery for Background Jobs

If you need background jobs, also start RabbitMQ and Redis:

```bash
# Start RabbitMQ and Redis
docker-compose -f docker-compose.local.yml up -d rabbitmq redis

# Terminal 3 - Celery Worker
celery -A recruitment_backend worker -l info

# Terminal 4 - Flower (optional monitoring)
celery -A recruitment_backend flower --port=5555
```

## Stop Everything

```bash
# Stop Docker services
docker-compose -f docker-compose.local.yml down

# Stop local services: Ctrl+C in each terminal
```

## Verify Setup

```bash
# Check Docker services
docker-compose -f docker-compose.local.yml ps

# Access services:
# - Django Admin: http://localhost:8001/admin
# - WebSocket Test: http://localhost:8001/ws-test
# - FastAPI Docs: http://localhost:8000/docs
# - RabbitMQ UI: http://localhost:15672 (guest/guest)
# - Flower: http://localhost:5555
```
