"""
Export training data to JSON for external training (GitHub Actions).
"""
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Export match data for ML training'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='training_data.json',
            help='Output file path',
        )
        parser.add_argument(
            '--seasons',
            type=int,
            default=5,
            help='Number of recent seasons to include',
        )

    def handle(self, *args, **options):
        from apps.matches.models import Match
        from apps.leagues.models import Season
        from apps.teams.models import TeamSeasonStats

        output_path = options['output']
        num_seasons = options['seasons']

        self.stdout.write('Exporting training data...')

        # Get recent seasons
        recent_seasons = Season.objects.order_by('-start_date')[:num_seasons * 20]
        season_ids = list(recent_seasons.values_list('id', flat=True))

        # Get finished matches with scores
        matches = Match.objects.filter(
            season_id__in=season_ids,
            status='finished',
            home_score__isnull=False,
            away_score__isnull=False,
        ).select_related(
            'home_team', 'away_team', 'season', 'season__league'
        ).order_by('-match_date')

        self.stdout.write(f'Found {matches.count()} finished matches')

        # Build training data
        training_data = []

        for match in matches:
            # Get team stats for the season
            home_stats = TeamSeasonStats.objects.filter(
                team=match.home_team,
                season=match.season
            ).first()

            away_stats = TeamSeasonStats.objects.filter(
                team=match.away_team,
                season=match.season
            ).first()

            match_data = {
                'match_id': match.id,
                'match_date': match.match_date.isoformat(),
                'league': match.season.league.code,
                'season': match.season.name,
                'home_team': match.home_team.name,
                'away_team': match.away_team.name,
                'home_score': match.home_score,
                'away_score': match.away_score,
                'home_halftime_score': match.home_halftime_score,
                'away_halftime_score': match.away_halftime_score,
            }

            # Add team stats if available
            if home_stats:
                match_data['home_stats'] = {
                    'wins': home_stats.wins,
                    'draws': home_stats.draws,
                    'losses': home_stats.losses,
                    'goals_for': home_stats.goals_for,
                    'goals_against': home_stats.goals_against,
                    'form': home_stats.form,
                }

            if away_stats:
                match_data['away_stats'] = {
                    'wins': away_stats.wins,
                    'draws': away_stats.draws,
                    'losses': away_stats.losses,
                    'goals_for': away_stats.goals_for,
                    'goals_against': away_stats.goals_against,
                    'form': away_stats.form,
                }

            # Add odds if available
            if hasattr(match, 'odds') and match.odds:
                match_data['odds'] = {
                    'home': float(match.odds.home_odds) if match.odds.home_odds else None,
                    'draw': float(match.odds.draw_odds) if match.odds.draw_odds else None,
                    'away': float(match.odds.away_odds) if match.odds.away_odds else None,
                }

            training_data.append(match_data)

        # Save to file
        with open(output_path, 'w') as f:
            json.dump({
                'exported_at': timezone.now().isoformat(),
                'total_matches': len(training_data),
                'matches': training_data,
            }, f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f'Exported {len(training_data)} matches to {output_path}'
        ))
