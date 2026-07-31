"""
Sync current injuries/suspensions from API-Football.

Feeds the 'injuries' feature group in the ML pipeline (see
apps/ml_pipeline/features/match_features.py::_get_injury_features).
"""
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync current injuries/suspensions from API-Football for the given leagues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--leagues',
            nargs='+',
            default=None,
            help='League codes to sync (default: all leagues API-Football covers)',
        )

    def handle(self, *args, **options):
        from apps.data_ingestion.providers.football_data_api import FootballDataAPIProvider

        provider = FootballDataAPIProvider()
        if not provider.is_configured():
            self.stdout.write(self.style.ERROR('API_FOOTBALL_KEY not configured'))
            return

        leagues = options.get('leagues') or list(provider.LEAGUES.keys())
        total = 0

        for league_code in leagues:
            try:
                saved = provider.sync_injuries_to_database(league_code)
                self.stdout.write(f'{league_code}: {saved} injury records')
                total += saved
            except Exception as e:
                logger.error(f"Error syncing injuries for {league_code}: {e}")
                self.stdout.write(self.style.WARNING(f'{league_code}: failed ({e})'))

        self.stdout.write(self.style.SUCCESS(f'Total injury records saved: {total}'))
