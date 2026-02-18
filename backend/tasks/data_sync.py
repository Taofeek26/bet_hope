"""
Data Synchronization Tasks

Tasks for syncing match data from Football-Data.co.uk
"""
import logging
from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_all_leagues(self):
    """
    Sync current season data and fixtures for all leagues.
    Runs daily at 4:00 AM UTC.
    """
    logger.info("Starting daily data sync for all leagues...")

    try:
        # Sync current season data with fixtures
        call_command(
            'sync_real_data',
            seasons=['2526'],  # Current season
            fixtures=True,
            verbosity=1
        )
        logger.info("Daily data sync completed successfully")
        return {'status': 'success', 'message': 'Daily sync completed'}

    except Exception as e:
        logger.error(f"Daily data sync failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def sync_historical_data(self):
    """
    Full historical data sync for all leagues.
    Runs weekly on Monday at 2:00 AM UTC.
    """
    logger.info("Starting weekly historical data sync...")

    try:
        # Sync last 5 seasons of historical data
        call_command(
            'sync_real_data',
            recent_only=True,
            verbosity=1
        )
        logger.info("Weekly historical sync completed successfully")
        return {'status': 'success', 'message': 'Historical sync completed'}

    except Exception as e:
        logger.error(f"Historical data sync failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=180)
def update_recent_results(self):
    """
    Update recent match results and sync fixtures.
    Runs every 3 hours to catch completed matches.
    """
    logger.info("Updating recent match results...")

    try:
        # Sync fixtures only (includes result updates)
        call_command(
            'sync_real_data',
            fixtures_only=True,
            verbosity=1
        )

        # Validate predictions against new results
        call_command(
            'generate_predictions',
            validate=True,
            verbosity=1
        )

        logger.info("Recent results update completed")
        return {'status': 'success', 'message': 'Results updated'}

    except Exception as e:
        logger.error(f"Results update failed: {e}")
        raise self.retry(exc=e)


@shared_task
def sync_single_league(league_code: str, season: str = '2526'):
    """
    Sync data for a single league.
    Can be triggered manually for specific leagues.
    """
    logger.info(f"Syncing {league_code} for season {season}...")

    try:
        call_command(
            'sync_real_data',
            leagues=[league_code],
            seasons=[season],
            fixtures=True,
            verbosity=1
        )
        return {'status': 'success', 'league': league_code, 'season': season}

    except Exception as e:
        logger.error(f"Single league sync failed: {e}")
        return {'status': 'error', 'message': str(e)}
