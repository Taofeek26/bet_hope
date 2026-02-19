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

    # Document scraping and embedding tasks
    'daily-document-refresh': {
        'task': 'tasks.documents.refresh_all_documents',
        'schedule': crontab(hour=4, minute=30),  # 4:30 AM UTC (after data sync starts)
        'options': {'queue': 'default'},
    },

    # Scrape external documentation
    'daily-scrape-docs': {
        'task': 'tasks.documents.scrape_documentation',
        'schedule': crontab(hour=4, minute=15),  # 4:15 AM UTC
        'options': {'queue': 'default'},
    },

    # Update built-in strategy documents
    'daily-update-strategies': {
        'task': 'tasks.documents.update_strategy_documents',
        'schedule': crontab(hour=4, minute=20),  # 4:20 AM UTC
        'options': {'queue': 'default'},
    },

    # Embed new documents
    'daily-embed-documents': {
        'task': 'tasks.documents.embed_documents',
        'schedule': crontab(hour=4, minute=45),  # 4:45 AM UTC (after updates)
        'options': {'queue': 'default'},
    },

    # Weekly cleanup of old embeddings
    'weekly-cleanup-embeddings': {
        'task': 'tasks.documents.cleanup_old_embeddings',
        'schedule': crontab(day_of_week=0, hour=3, minute=30),  # Sunday 3:30 AM
        'options': {'queue': 'default'},
    },

    # Scrape football news twice daily
    'morning-football-news': {
        'task': 'tasks.documents.scrape_football_news',
        'schedule': crontab(hour=6, minute=0),  # 6:00 AM UTC
        'options': {'queue': 'default'},
    },

    'evening-football-news': {
        'task': 'tasks.documents.scrape_football_news',
        'schedule': crontab(hour=18, minute=0),  # 6:00 PM UTC
        'options': {'queue': 'default'},
    },

    # Clean up old news daily
    'daily-cleanup-old-news': {
        'task': 'tasks.documents.cleanup_old_news',
        'schedule': crontab(hour=5, minute=30),  # 5:30 AM UTC
        'options': {'queue': 'default'},
    },

    # =========================================================================
    # Football-Data.org API Tasks (Real-time fixtures and results)
    # =========================================================================

    # Sync upcoming fixtures from API every 6 hours
    'sync-fixtures-api': {
        'task': 'tasks.data_sync.sync_fixtures_api',
        'schedule': crontab(hour='*/6', minute=0),  # Every 6 hours at :00
        'options': {'queue': 'data_sync'},
    },

    # Sync recent results from API every 3 hours
    'sync-results-api': {
        'task': 'tasks.data_sync.sync_results_api',
        'schedule': crontab(hour='*/3', minute=45),  # Every 3 hours at :45
        'options': {'queue': 'data_sync'},
    },

    # Sync live scores during peak match times (weekends)
    'sync-live-scores-weekend': {
        'task': 'tasks.data_sync.sync_live_scores',
        'schedule': crontab(day_of_week='0,6', hour='12-23', minute='*/15'),  # Every 15 min on weekends
        'options': {'queue': 'data_sync'},
    },

    # Sync live scores on weekday evenings
    'sync-live-scores-weekday': {
        'task': 'tasks.data_sync.sync_live_scores',
        'schedule': crontab(day_of_week='1-5', hour='18-23', minute='*/15'),  # Every 15 min weekday evenings
        'options': {'queue': 'data_sync'},
    },
}

# Task routing
app.conf.task_routes = {
    'tasks.data_sync.*': {'queue': 'data_sync'},
    'tasks.training.*': {'queue': 'ml'},
    'tasks.predictions.*': {'queue': 'predictions'},
    'tasks.analytics.*': {'queue': 'analytics'},
    'tasks.documents.*': {'queue': 'default'},
}

# Task settings
app.conf.task_default_queue = 'default'
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')
