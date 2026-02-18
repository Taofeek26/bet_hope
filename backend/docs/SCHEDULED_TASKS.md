# Scheduled Tasks & Background Jobs

This document covers the automated task scheduling system using Celery and Redis.

## Overview

Bet_Hope uses **Celery** with **Redis** as the message broker for:
- Automated data synchronization
- Model training and updates
- Prediction generation
- Performance analytics
- System maintenance

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Celery Beat    │────▶│     Redis       │◀────│  Celery Worker  │
│  (Scheduler)    │     │  (Broker)       │     │  (Executor)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        │           ┌─────────────────┐                 │
        └──────────▶│   Django App    │◀────────────────┘
                    │  (Database)     │
                    └─────────────────┘
```

## Task Schedule

| Task | Schedule | Queue | Description |
|------|----------|-------|-------------|
| `sync_all_leagues` | Daily 4:00 AM UTC | data_sync | Sync current season data and fixtures |
| `sync_historical_data` | Monday 2:00 AM UTC | data_sync | Full historical data sync (last 5 seasons) |
| `update_recent_results` | Every 3 hours | data_sync | Update match results and fixtures |
| `retrain_model` | Daily 5:00 AM UTC | ml | Retrain ML model with latest data |
| `generate_predictions` | Every 6 hours | predictions | Generate predictions for upcoming matches |
| `validate_predictions` | Daily 6:00 AM UTC | predictions | Validate predictions against results |
| `calculate_model_metrics` | Daily 7:00 AM UTC | analytics | Calculate model performance metrics |
| `cleanup_old_data` | Sunday 3:00 AM UTC | default | Clean up old cache files |

## Setup

### Prerequisites

- Docker (for Redis)
- Python virtual environment with dependencies installed

### Starting Services

#### 1. Start Redis (using Docker)

```bash
# Start Docker Desktop (macOS)
open -a Docker

# Run Redis container
docker run -d --name redis-bet-hope -p 6379:6379 redis:alpine

# Or start existing container
docker start redis-bet-hope
```

#### 2. Start Celery Worker + Beat

**Option A: Background (Production)**
```bash
cd backend
source venv/bin/activate

# Start worker with beat scheduler (detached)
celery -A config worker -B -l info \
    --detach \
    --pidfile=/tmp/celery-bet-hope.pid \
    --logfile=/tmp/celery-bet-hope.log
```

**Option B: Foreground (Development)**
```bash
cd backend
source venv/bin/activate

# Terminal 1: Worker
celery -A config worker -l info

# Terminal 2: Beat scheduler
celery -A config beat -l info
```

**Option C: Combined (Development)**
```bash
celery -A config worker -B -l info
```

### Stopping Services

```bash
# Stop Celery
kill $(cat /tmp/celery-bet-hope.pid)

# Stop Redis
docker stop redis-bet-hope
```

## Task Queues

Tasks are routed to specialized queues:

| Queue | Purpose | Tasks |
|-------|---------|-------|
| `data_sync` | Data synchronization | sync_all_leagues, sync_historical_data, update_recent_results |
| `ml` | Machine learning | retrain_model |
| `predictions` | Prediction tasks | generate_predictions, validate_predictions |
| `analytics` | Analytics/metrics | calculate_model_metrics |
| `default` | General tasks | cleanup_old_data, health_check |

## Manual Task Execution

### Via Django Shell

```python
# Sync all leagues now
from tasks.data_sync import sync_all_leagues
sync_all_leagues.delay()

# Sync specific league
from tasks.data_sync import sync_single_league
sync_single_league.delay('E0', '2526')

# Generate predictions
from tasks.predictions import generate_predictions
generate_predictions.delay()

# Generate prediction for specific match
from tasks.predictions import generate_prediction_for_match
generate_prediction_for_match.delay(match_id=123)

# Retrain model
from tasks.training import retrain_model
retrain_model.delay()

# Calculate metrics
from tasks.analytics import calculate_model_metrics
calculate_model_metrics.delay()

# Health check
from tasks.maintenance import health_check
result = health_check.delay()
print(result.get())
```

### Via Management Commands

```bash
# Sync data (same as sync_all_leagues task)
python manage.py sync_real_data --fixtures

# Generate predictions
python manage.py generate_predictions --upcoming --days 14

# Train model
python manage.py train_model
```

## Monitoring

### View Logs

```bash
# Live log stream
tail -f /tmp/celery-bet-hope.log

# Last 100 lines
tail -100 /tmp/celery-bet-hope.log

# Search for errors
grep -i error /tmp/celery-bet-hope.log
```

### Check Worker Status

```bash
# Check if worker is running
ps aux | grep celery

# Check worker stats
celery -A config inspect active
celery -A config inspect stats
```

### Monitor with Flower (optional)

```bash
# Install Flower
pip install flower

# Start Flower web UI
celery -A config flower --port=5555

# Access at http://localhost:5555
```

## Task Files

```
backend/tasks/
├── __init__.py          # Task exports
├── data_sync.py         # Data synchronization tasks
├── training.py          # Model training tasks
├── predictions.py       # Prediction generation tasks
├── analytics.py         # Analytics and metrics tasks
└── maintenance.py       # Cleanup and maintenance tasks
```

## Configuration

### Celery Settings (config/celery.py)

```python
# Beat schedule
app.conf.beat_schedule = {
    'daily-data-sync': {
        'task': 'tasks.data_sync.sync_all_leagues',
        'schedule': crontab(hour=4, minute=0),
        'options': {'queue': 'data_sync'},
    },
    # ... more tasks
}

# Task routing
app.conf.task_routes = {
    'tasks.data_sync.*': {'queue': 'data_sync'},
    'tasks.training.*': {'queue': 'ml'},
    'tasks.predictions.*': {'queue': 'predictions'},
    'tasks.analytics.*': {'queue': 'analytics'},
}
```

### Environment Variables

```bash
# Redis connection
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Troubleshooting

### Worker won't start

1. Check Redis is running:
   ```bash
   docker ps | grep redis
   redis-cli ping  # Should return PONG
   ```

2. Check for existing workers:
   ```bash
   ps aux | grep celery
   kill $(cat /tmp/celery-bet-hope.pid)  # Kill if needed
   ```

### Tasks not executing

1. Check worker is connected:
   ```bash
   celery -A config inspect ping
   ```

2. Check task is registered:
   ```bash
   celery -A config inspect registered
   ```

### High memory usage

1. Restart worker periodically:
   ```bash
   celery -A config worker --max-tasks-per-child=100
   ```

## Production Deployment

For production, use a process manager like **systemd** or **supervisor**:

### Systemd Service Example

```ini
# /etc/systemd/system/celery-bet-hope.service
[Unit]
Description=Bet_Hope Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/bet_hope/backend
Environment="PATH=/var/www/bet_hope/backend/venv/bin"
ExecStart=/var/www/bet_hope/backend/venv/bin/celery -A config worker -B \
    --detach \
    --pidfile=/var/run/celery/bet_hope.pid \
    --logfile=/var/log/celery/bet_hope.log \
    --loglevel=INFO
ExecStop=/bin/kill -TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable celery-bet-hope
sudo systemctl start celery-bet-hope
sudo systemctl status celery-bet-hope
```
