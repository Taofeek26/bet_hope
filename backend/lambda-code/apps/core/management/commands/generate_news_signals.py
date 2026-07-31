"""
Generate LLM-derived news signals (injury mentions, sentiment) for teams
with recent tagged news, feeding the 'ai_signals' ML feature group.

Run after sync_football_news has tagged fresh articles to teams.
"""
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate news-derived injury/sentiment signals for teams with recent tagged news'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            default=None,
            help='AI provider to use (default: settings.DEFAULT_AI_PROVIDER)',
        )

    def handle(self, *args, **options):
        from django.utils import timezone
        from datetime import timedelta
        from apps.teams.models import Team
        from apps.documents.services.news_signal_service import NewsSignalExtractionService

        try:
            service = NewsSignalExtractionService(provider=options.get('provider'))
        except (ImportError, ValueError) as e:
            self.stdout.write(self.style.ERROR(f'Could not initialize AI provider: {e}'))
            return

        since = timezone.now() - timedelta(days=service.LOOKBACK_DAYS)
        teams_with_news = Team.objects.filter(
            documents__document_type='news',
            documents__created_at__gte=since,
        ).distinct()

        generated = 0
        for team in teams_with_news:
            result = service.generate_for_team(team)
            if result:
                generated += 1
                self.stdout.write(
                    f"{team.name}: injury={result['injury_mention_score']:.2f} "
                    f"sentiment={result['sentiment_score']:.2f} "
                    f"(from {result['source_count']} articles)"
                )

        self.stdout.write(self.style.SUCCESS(
            f'Generated {generated} news signals from {teams_with_news.count()} candidate teams'
        ))
