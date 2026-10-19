"""
Fixtures and results for the ESPN-only competitions (Phase 9): Europa
League, J1 League, Chinese Super League, A-League. The daily sync runs this
for the current year; run it once with --history to load 2023 onwards.

    python manage.py sync_espn_leagues --history
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sync Europa League, J1, Chinese Super League and A-League from ESPN'

    def add_arguments(self, parser):
        parser.add_argument('--history', action='store_true', help='Load every year since 2023, not just this one')

    def handle(self, *args, **options):
        from apps.data_ingestion.providers.espn_leagues import sync_all
        sync_all(history=options['history'], stdout=self.stdout)
