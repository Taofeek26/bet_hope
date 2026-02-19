"""
Celery Tasks for Bet_Hope

This module contains all scheduled tasks for:
- Data synchronization
- Model training
- Prediction generation
- Analytics and metrics
- Maintenance and cleanup
- Document scraping and embedding
"""

from .data_sync import (
    sync_all_leagues,
    sync_historical_data,
    update_recent_results,
    sync_single_league,
    sync_fixtures_api,
    sync_results_api,
    sync_live_scores,
    check_api_status,
    sync_teams_with_logos,
)
from .training import retrain_model
from .predictions import generate_predictions, validate_predictions
from .analytics import calculate_model_metrics
from .maintenance import cleanup_old_data
from .documents import (
    scrape_documentation,
    update_strategy_documents,
    embed_documents,
    refresh_all_documents,
    cleanup_old_embeddings,
    scrape_football_news,
    cleanup_old_news,
)

__all__ = [
    # Data sync tasks
    'sync_all_leagues',
    'sync_historical_data',
    'update_recent_results',
    'sync_single_league',
    # API-Football tasks
    'sync_fixtures_api',
    'sync_results_api',
    'sync_live_scores',
    'check_api_status',
    'sync_teams_with_logos',
    # ML tasks
    'retrain_model',
    'generate_predictions',
    'validate_predictions',
    'calculate_model_metrics',
    'cleanup_old_data',
    # Document tasks
    'scrape_documentation',
    'update_strategy_documents',
    'embed_documents',
    'refresh_all_documents',
    'cleanup_old_embeddings',
    'scrape_football_news',
    'cleanup_old_news',
]
