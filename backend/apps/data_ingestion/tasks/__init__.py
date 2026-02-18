# Data Ingestion Celery Tasks
from .sync_tasks import (
    sync_football_data,
    sync_football_data_league,
    sync_understat_xg,
    sync_all_data,
    update_team_form,
    daily_data_sync,
)

__all__ = [
    'sync_football_data',
    'sync_football_data_league',
    'sync_understat_xg',
    'sync_all_data',
    'update_team_form',
    'daily_data_sync',
]
