"""
Fill missing final scores from ESPN, then settle what they finish (Phase 8).

The daily sync (04:15 UTC) and the hourly live-score check already do this;
run it by hand to catch up at once:

    python manage.py sync_results_espn --days 60
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Fill scores of played matches that have none from ESPN, then validate/settle'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=60, help='How far back to look (default 60)')

    def handle(self, *args, **options):
        from apps.data_ingestion.providers.espn import sync_stale_results
        res = sync_stale_results(days_back=options['days'], stdout=self.stdout)
        if res['finished'] or res['postponed'] or res['cancelled']:
            call_command('generate_predictions', validate=True)
