"""
Celery Tasks for Data Synchronization

Handles scheduled and on-demand data syncing from:
- Football-Data.co.uk (CSV match data)
- Understat (xG statistics)
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from celery import shared_task, group, chain
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Avg, Count, Sum, F

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def sync_football_data(
    self,
    seasons: Optional[List[str]] = None,
    leagues: Optional[List[str]] = None
) -> dict:
    """
    Sync all match data from Football-Data.co.uk.

    Args:
        seasons: List of season codes (e.g., ['2324', '2223'])
        leagues: List of league codes (e.g., ['E0', 'SP1'])

    Returns:
        Dict with sync statistics
    """
    from apps.data_ingestion.providers import FootballDataProvider

    logger.info("Starting Football-Data.co.uk sync...")

    provider = FootballDataProvider()

    # Use configured defaults if not specified
    if not seasons:
        seasons = getattr(settings, 'HISTORICAL_SEASONS', provider.SEASONS)
    if not leagues:
        leagues = list(getattr(settings, 'SUPPORTED_LEAGUES', provider.LEAGUES).keys())

    try:
        stats = provider.sync_all(seasons=seasons, leagues=leagues)
        logger.info(f"Football-Data sync complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Football-Data sync failed: {e}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def sync_football_data_league(
    self,
    league_code: str,
    season: str
) -> dict:
    """
    Sync a single league/season from Football-Data.co.uk.

    Args:
        league_code: League code (e.g., 'E0')
        season: Season code (e.g., '2324')

    Returns:
        Dict with sync statistics
    """
    from apps.data_ingestion.providers import FootballDataProvider

    logger.info(f"Syncing Football-Data: {league_code}/{season}")

    provider = FootballDataProvider()

    try:
        df = provider.download_csv(league_code, season, use_cache=False)
        if df is not None and not df.empty:
            created, updated = provider.sync_to_database(league_code, season, df)
            return {
                'league': league_code,
                'season': season,
                'created': created,
                'updated': updated,
            }
        return {'league': league_code, 'season': season, 'created': 0, 'updated': 0}

    except Exception as e:
        logger.error(f"League sync failed {league_code}/{season}: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    autoretry_for=(Exception,),
)
def sync_understat_xg(
    self,
    seasons: Optional[List[int]] = None,
    leagues: Optional[List[str]] = None
) -> dict:
    """
    Sync xG data from Understat.

    Args:
        seasons: List of season years (e.g., [2023, 2022])
        leagues: List of understat league names

    Returns:
        Dict with sync statistics
    """
    from apps.data_ingestion.providers import UnderstatProvider

    logger.info("Starting Understat xG sync...")

    try:
        provider = UnderstatProvider()
        stats = provider.sync_all(seasons=seasons, leagues=leagues)
        logger.info(f"Understat sync complete: {stats}")
        return stats

    except ImportError as e:
        logger.warning(f"Understat sync skipped (package not installed): {e}")
        return {'skipped': True, 'reason': str(e)}
    except Exception as e:
        logger.error(f"Understat sync failed: {e}")
        raise


@shared_task(bind=True)
def sync_all_data(self) -> dict:
    """
    Full data sync: Football-Data + Understat.

    Runs both sync tasks in parallel.

    Returns:
        Dict with combined statistics
    """
    logger.info("Starting full data sync...")

    # Run sync tasks in parallel
    job = group([
        sync_football_data.s(),
        sync_understat_xg.s(),
    ])

    result = job.apply_async()
    results = result.get(timeout=3600)  # 1 hour timeout

    combined = {
        'football_data': results[0] if len(results) > 0 else {},
        'understat': results[1] if len(results) > 1 else {},
        'completed_at': timezone.now().isoformat(),
    }

    logger.info(f"Full sync complete: {combined}")
    return combined


@shared_task(bind=True)
def update_team_form(
    self,
    league_code: Optional[str] = None,
    num_matches: int = 5
) -> dict:
    """
    Update team form statistics based on recent matches.

    Args:
        league_code: Optional league to update (all if None)
        num_matches: Number of recent matches to consider

    Returns:
        Dict with update statistics
    """
    from apps.teams.models import Team, TeamSeasonStats
    from apps.matches.models import Match
    from apps.leagues.models import Season

    logger.info(f"Updating team form (last {num_matches} matches)...")

    updated = 0

    # Get current seasons
    current_season_code = settings.HISTORICAL_SEASONS[0] if hasattr(settings, 'HISTORICAL_SEASONS') else '2425'

    teams_query = Team.objects.all()
    if league_code:
        teams_query = teams_query.filter(league__code=league_code)

    for team in teams_query:
        try:
            # Get recent matches
            recent_matches = Match.objects.filter(
                season__code=current_season_code,
                status=Match.Status.FINISHED,
            ).filter(
                models.Q(home_team=team) | models.Q(away_team=team)
            ).order_by('-match_date')[:num_matches]

            if not recent_matches.exists():
                continue

            # Calculate form metrics
            form_data = calculate_team_form(team, list(recent_matches))

            # Update team season stats
            try:
                season = Season.objects.get(
                    league=team.league,
                    code=current_season_code
                )
                stats, _ = TeamSeasonStats.objects.get_or_create(
                    team=team,
                    season=season
                )

                stats.form_points = form_data['points']
                stats.form_goals_for = form_data['goals_for']
                stats.form_goals_against = form_data['goals_against']
                stats.form_xg = form_data.get('xg')
                stats.form_string = form_data['form_string']
                stats.save()

                updated += 1

            except Season.DoesNotExist:
                continue

        except Exception as e:
            logger.error(f"Error updating form for {team}: {e}")
            continue

    logger.info(f"Updated form for {updated} teams")
    return {'teams_updated': updated}


def calculate_team_form(team, matches: list) -> dict:
    """
    Calculate form metrics from recent matches.

    Args:
        team: Team model instance
        matches: List of recent Match instances

    Returns:
        Dict with form metrics
    """
    from django.db import models

    points = 0
    goals_for = 0
    goals_against = 0
    xg_total = 0
    form_chars = []

    for match in matches:
        is_home = match.home_team_id == team.id

        if is_home:
            gf = match.home_score or 0
            ga = match.away_score or 0
            xg = float(match.home_xg or 0)
        else:
            gf = match.away_score or 0
            ga = match.home_score or 0
            xg = float(match.away_xg or 0)

        goals_for += gf
        goals_against += ga
        xg_total += xg

        # Determine result
        if gf > ga:
            points += 3
            form_chars.append('W')
        elif gf == ga:
            points += 1
            form_chars.append('D')
        else:
            form_chars.append('L')

    return {
        'points': points,
        'goals_for': goals_for,
        'goals_against': goals_against,
        'xg': xg_total if xg_total > 0 else None,
        'form_string': ''.join(form_chars),
    }


@shared_task(bind=True)
def daily_data_sync(self) -> dict:
    """
    Daily sync task - updates current season data and recalculates form.

    This is scheduled to run daily via Celery Beat.

    Returns:
        Dict with sync statistics
    """
    logger.info("Starting daily data sync...")

    current_season = getattr(settings, 'HISTORICAL_SEASONS', ['2425'])[0]
    current_year = int(f"20{current_season[:2]}")

    # Chain of tasks for daily sync
    workflow = chain(
        # 1. Sync current season match data
        sync_football_data.s(
            seasons=[current_season],
            leagues=None  # All leagues
        ),
        # 2. Sync xG data for current season
        sync_understat_xg.s(
            seasons=[current_year],
            leagues=None
        ),
        # 3. Update team form
        update_team_form.s(),
    )

    result = workflow.apply_async()

    return {
        'task_id': result.id,
        'status': 'started',
        'started_at': timezone.now().isoformat(),
    }


@shared_task(bind=True)
def sync_upcoming_matches(self) -> dict:
    """
    Sync upcoming fixture data for predictions.

    Returns:
        Dict with sync statistics
    """
    from apps.matches.models import Match
    from apps.leagues.models import Season

    logger.info("Syncing upcoming matches...")

    # Get matches scheduled for next 7 days
    today = timezone.now().date()
    week_ahead = today + timedelta(days=7)

    upcoming = Match.objects.filter(
        match_date__gte=today,
        match_date__lte=week_ahead,
        status=Match.Status.SCHEDULED,
    ).count()

    logger.info(f"Found {upcoming} upcoming matches in next 7 days")

    return {
        'upcoming_matches': upcoming,
        'date_range': f"{today} to {week_ahead}",
    }


@shared_task(bind=True)
def cleanup_old_cache(self, days: int = 30) -> dict:
    """
    Clean up old cached CSV files.

    Args:
        days: Delete cache files older than this many days

    Returns:
        Dict with cleanup statistics
    """
    from pathlib import Path
    from django.conf import settings

    cache_dir = Path(settings.RAW_DATA_DIR) / 'football_data'

    if not cache_dir.exists():
        return {'deleted': 0, 'reason': 'cache dir not found'}

    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0

    for file in cache_dir.glob('*.csv'):
        if datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            file.unlink()
            deleted += 1

    logger.info(f"Cleaned up {deleted} old cache files")
    return {'deleted': deleted}


# Import models for the update_team_form task
from django.db import models
