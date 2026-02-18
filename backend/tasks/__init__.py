"""
Celery Tasks for Bet_Hope

This module contains all scheduled tasks for:
- Data synchronization
- Model training
- Prediction generation
- Analytics and metrics
- Maintenance and cleanup
"""

from .data_sync import sync_all_leagues, sync_historical_data, update_recent_results
from .training import retrain_model
from .predictions import generate_predictions, validate_predictions
from .analytics import calculate_model_metrics
from .maintenance import cleanup_old_data

__all__ = [
    'sync_all_leagues',
    'sync_historical_data',
    'update_recent_results',
    'retrain_model',
    'generate_predictions',
    'validate_predictions',
    'calculate_model_metrics',
    'cleanup_old_data',
]
