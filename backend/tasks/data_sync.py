"""
Data Synchronization Tasks

Tasks for syncing match data from:
- Football-Data.co.uk (CSV historical data)
- API-Football API (real-time fixtures and results)
"""
import logging
from celery import shared_task
from django.core.management import call_command
from django.conf import settings

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


# ============================================================================
# API-Football API Tasks (Real-time fixtures and results)
# ============================================================================

@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def sync_fixtures_api(self, days: int = 14):
    """
    Sync upcoming fixtures from configured API provider.
    Runs every 6 hours to keep fixtures up to date.

    Uses Football-Data.org (preferred) or API-Football as fallback.

    Args:
        days: Number of days ahead to sync (default 14)
    """
    from apps.data_ingestion.providers import get_fixtures_provider

    provider = get_fixtures_provider()
    if not provider:
        logger.warning("No fixtures API configured. Skipping sync.")
        return {'status': 'skipped', 'message': 'No API key configured'}

    provider_name = provider.__class__.__name__
    logger.info(f"Syncing fixtures from {provider_name} for next {days} days...")

    try:
        created, updated = provider.sync_fixtures_to_database(days=days)

        logger.info(f"Fixtures sync completed: {created} created, {updated} updated")
        return {
            'status': 'success',
            'provider': provider_name,
            'created': created,
            'updated': updated,
        }

    except Exception as e:
        logger.error(f"Fixtures sync failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def sync_results_api(self, days: int = 3):
    """
    Sync recent results from configured API provider.
    Runs every 3 hours to get latest results.

    Uses Football-Data.org (preferred) or API-Football as fallback.

    Args:
        days: Number of days back to sync (default 3)
    """
    from apps.data_ingestion.providers import get_fixtures_provider

    provider = get_fixtures_provider()
    if not provider:
        logger.warning("No results API configured. Skipping sync.")
        return {'status': 'skipped', 'message': 'No API key configured'}

    provider_name = provider.__class__.__name__
    logger.info(f"Syncing results from {provider_name} for last {days} days...")

    try:
        created, updated = provider.sync_results_to_database(days=days)

        # Validate predictions against new results
        if updated > 0:
            call_command('generate_predictions', validate=True, verbosity=1)

        logger.info(f"Results sync completed: {created} created, {updated} updated")
        return {
            'status': 'success',
            'provider': provider_name,
            'created': created,
            'updated': updated,
        }

    except Exception as e:
        logger.error(f"Results sync failed: {e}")
        raise self.retry(exc=e)


@shared_task
def sync_live_scores():
    """
    Update live match scores from API.
    Can be called frequently during match days.

    Note: Live scores only available with API-Football, not Football-Data.org free tier.
    """
    from apps.data_ingestion.providers import FootballDataAPIProvider

    if not settings.API_FOOTBALL_KEY:
        return {'status': 'skipped', 'message': 'API key not configured (live scores require API-Football)'}

    logger.info("Updating live scores from API...")

    try:
        provider = FootballDataAPIProvider()
        updated = provider.sync_live_matches()

        return {
            'status': 'success',
            'updated': updated,
        }

    except Exception as e:
        logger.error(f"Live scores update failed: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def check_api_status():
    """
    Check if fixtures API is configured and working.
    """
    from apps.data_ingestion.providers import get_fixtures_provider, FootballDataOrgProvider, FootballDataAPIProvider

    provider = get_fixtures_provider()

    if not provider:
        return {
            'status': 'not_configured',
            'message': 'No fixtures API configured',
            'help': 'Set FOOTBALL_DATA_ORG_KEY (free at football-data.org) or API_FOOTBALL_KEY'
        }

    try:
        provider_name = provider.__class__.__name__
        account_status = provider.get_status()

        if account_status:
            return {
                'status': 'ok',
                'provider': provider_name,
                'account': account_status,
                'supported_leagues': list(provider.LEAGUES.keys()),
            }
        else:
            return {
                'status': 'error',
                'provider': provider_name,
                'message': 'Could not fetch account status'
            }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def sync_teams_with_logos(self, league_code: str = None):
    """
    Sync teams with logos from configured API provider.
    This should be run once to populate all team logos.

    Args:
        league_code: Optional league code to filter
    """
    from apps.data_ingestion.providers import get_fixtures_provider

    provider = get_fixtures_provider()
    if not provider:
        logger.warning("No API configured. Skipping teams sync.")
        return {'status': 'skipped', 'message': 'No API key configured'}

    provider_name = provider.__class__.__name__
    logger.info(f"Syncing teams with logos from {provider_name} for {league_code or 'all leagues'}...")

    try:
        created, updated = provider.sync_teams_with_logos(league_code)

        logger.info(f"Teams sync completed: {created} created, {updated} updated")
        return {
            'status': 'success',
            'provider': provider_name,
            'created': created,
            'updated': updated,
        }

    except Exception as e:
        logger.error(f"Teams sync failed: {e}")
        raise self.retry(exc=e)
