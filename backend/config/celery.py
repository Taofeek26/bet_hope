"""
Bet_Hope Celery Configuration
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('bet_hope')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Also include tasks from the top-level tasks module
app.autodiscover_tasks(['tasks'])

# Celery Beat Schedule - Automated tasks
app.conf.beat_schedule = {
    # Daily data sync - Download latest CSV data
    'daily-data-sync': {
        'task': 'tasks.data_sync.sync_all_leagues',
        'schedule': crontab(hour=4, minute=0),  # 4:00 AM UTC
        'options': {'queue': 'data_sync'},
    },

    # Weekly full historical sync
    'weekly-historical-sync': {
        'task': 'tasks.data_sync.sync_historical_data',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Monday 2:00 AM
        'options': {'queue': 'data_sync'},
    },

    # Daily model retraining
    'daily-model-training': {
        'task': 'tasks.training.retrain_model',
        'schedule': crontab(hour=5, minute=0),  # 5:00 AM UTC (after data sync)
        'options': {'queue': 'ml'},
    },

    # Generate predictions every 6 hours
    'generate-predictions': {
        'task': 'tasks.predictions.generate_predictions',
        'schedule': crontab(hour='*/6', minute=15),  # Every 6 hours at :15
        'options': {'queue': 'predictions'},
    },

    # Update match results - Check for completed matches
    'update-match-results': {
        'task': 'tasks.data_sync.update_recent_results',
        'schedule': crontab(hour='*/3', minute=30),  # Every 3 hours at :30
        'options': {'queue': 'data_sync'},
    },

    # Validate predictions against results
    'validate-predictions': {
        'task': 'tasks.predictions.validate_predictions',
        'schedule': crontab(hour=6, minute=0),  # 6:00 AM UTC
        'options': {'queue': 'predictions'},
    },

    # Calculate model performance metrics
    'calculate-metrics': {
        'task': 'tasks.analytics.calculate_model_metrics',
        'schedule': crontab(hour=7, minute=0),  # 7:00 AM UTC
        'options': {'queue': 'analytics'},
    },

    # Cleanup old data
    'cleanup-old-data': {
        'task': 'tasks.maintenance.cleanup_old_data',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Sunday 3:00 AM
        'options': {'queue': 'default'},
    },
}

# Task routing
app.conf.task_routes = {
    'tasks.data_sync.*': {'queue': 'data_sync'},
    'tasks.training.*': {'queue': 'ml'},
    'tasks.predictions.*': {'queue': 'predictions'},
    'tasks.analytics.*': {'queue': 'analytics'},
}

# Task settings
app.conf.task_default_queue = 'default'
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')
