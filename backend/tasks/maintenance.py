"""
Maintenance Tasks

Tasks for cleanup and maintenance operations
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_data():
    """
    Clean up old cached data and temporary files.
    Runs weekly on Sunday at 3:00 AM UTC.
    """
    logger.info("Starting weekly cleanup...")

    try:
        from pathlib import Path
        from django.conf import settings
        import os

        cleaned_files = 0
        cleaned_size = 0

        # Clean old CSV cache files (older than 7 days)
        cache_dir = Path(settings.RAW_DATA_DIR) / 'football_data'
        if cache_dir.exists():
            cutoff = timezone.now().timestamp() - (7 * 24 * 3600)
            for file in cache_dir.glob('*.csv'):
                if file.stat().st_mtime < cutoff:
                    size = file.stat().st_size
                    file.unlink()
                    cleaned_files += 1
                    cleaned_size += size

        logger.info(f"Cleanup completed: {cleaned_files} files, {cleaned_size / 1024:.1f} KB freed")

        return {
            'status': 'success',
            'files_cleaned': cleaned_files,
            'bytes_freed': cleaned_size
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_predictions():
    """
    Archive or remove very old predictions.
    Keeps predictions for last 2 years.
    """
    logger.info("Cleaning up old predictions...")

    try:
        from apps.predictions.models import Prediction

        two_years_ago = timezone.now().date() - timedelta(days=730)

        # Delete predictions older than 2 years
        deleted, _ = Prediction.objects.filter(
            match__match_date__lt=two_years_ago
        ).delete()

        logger.info(f"Deleted {deleted} old predictions")

        return {'status': 'success', 'deleted': deleted}

    except Exception as e:
        logger.error(f"Prediction cleanup failed: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def update_team_stats():
    """
    Recalculate team season statistics.
    """
    logger.info("Updating team statistics...")

    try:
        from apps.teams.models import Team, TeamSeasonStats
        from apps.matches.models import Match
        from apps.leagues.models import Season
        from django.db.models import Sum, Count, Q

        # Get current season
        current_seasons = Season.objects.filter(code='2526')

        updated = 0
        for season in current_seasons:
            teams = Team.objects.filter(league=season.league)

            for team in teams:
                # Calculate stats from matches
                home_matches = Match.objects.filter(
                    home_team=team,
                    season=season,
                    status=Match.Status.FINISHED
                )
                away_matches = Match.objects.filter(
                    away_team=team,
                    season=season,
                    status=Match.Status.FINISHED
                )

                # Home stats
                home_stats = home_matches.aggregate(
                    played=Count('id'),
                    wins=Count('id', filter=Q(home_score__gt=models.F('away_score'))),
                    draws=Count('id', filter=Q(home_score=models.F('away_score'))),
                    goals_for=Sum('home_score'),
                    goals_against=Sum('away_score'),
                )

                # Away stats
                away_stats = away_matches.aggregate(
                    played=Count('id'),
                    wins=Count('id', filter=Q(away_score__gt=models.F('home_score'))),
                    draws=Count('id', filter=Q(away_score=models.F('home_score'))),
                    goals_for=Sum('away_score'),
                    goals_against=Sum('home_score'),
                )

                # Combine stats
                matches_played = (home_stats['played'] or 0) + (away_stats['played'] or 0)
                if matches_played == 0:
                    continue

                wins = (home_stats['wins'] or 0) + (away_stats['wins'] or 0)
                draws = (home_stats['draws'] or 0) + (away_stats['draws'] or 0)
                losses = matches_played - wins - draws
                goals_for = (home_stats['goals_for'] or 0) + (away_stats['goals_for'] or 0)
                goals_against = (home_stats['goals_against'] or 0) + (away_stats['goals_against'] or 0)
                points = wins * 3 + draws

                # Update or create stats
                TeamSeasonStats.objects.update_or_create(
                    team=team,
                    season=season,
                    defaults={
                        'matches_played': matches_played,
                        'wins': wins,
                        'draws': draws,
                        'losses': losses,
                        'goals_for': goals_for,
                        'goals_against': goals_against,
                        'points': points,
                    }
                )
                updated += 1

        logger.info(f"Updated stats for {updated} teams")
        return {'status': 'success', 'teams_updated': updated}

    except Exception as e:
        logger.error(f"Team stats update failed: {e}")
        return {'status': 'error', 'message': str(e)}


# Import models for F expression
from django.db import models


@shared_task
def health_check():
    """
    Simple health check task to verify Celery is working.
    """
    return {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat()
    }
