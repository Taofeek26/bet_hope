from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Fetch current bookmaker prices from The Odds API (leagues with fixtures in the next 3 days)'

    def add_arguments(self, parser):
        parser.add_argument('--leagues', nargs='+', default=None, help='League codes (default: all due)')

    def handle(self, *args, **options):
        from apps.data_ingestion.providers.the_odds_api import sync_odds
        sync_odds(leagues=options.get('leagues'), stdout=self.stdout)
