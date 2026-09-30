"""
Fill in one queued AIRecommendation row. Invoked asynchronously in the
manage Lambda by POST /ai-recommendations/generate/ (Phase 1): the LLM
call regularly takes longer than API Gateway's 29s limit, so the web
request only creates a pending row and the browser polls it.
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Generate the AI recommendation for a pending AIRecommendation row'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, required=True, help='AIRecommendation id')
        parser.add_argument('--no-rag', action='store_true', help='Skip knowledge-base retrieval')

    def handle(self, *args, **opts):
        from apps.documents.models import AIRecommendation
        from apps.documents.services import AIRecommendationService

        try:
            record = AIRecommendation.objects.get(id=opts['id'])
        except AIRecommendation.DoesNotExist:
            raise CommandError(f"AIRecommendation {opts['id']} not found")

        if record.status == AIRecommendation.Status.COMPLETED:
            self.stdout.write('Already completed, nothing to do.')
            return

        record.status = AIRecommendation.Status.PROCESSING
        record.save(update_fields=['status', 'updated_at'])

        try:
            service = AIRecommendationService(provider=record.provider)
            service.generate_recommendation(
                prediction_id=record.prediction_id,
                include_rag=not opts['no_rag'],
                model=record.model_name or None,
                record=record,
            )
        except Exception as e:
            record.status = AIRecommendation.Status.FAILED
            record.error_message = str(e)[:2000]
            record.save(update_fields=['status', 'error_message', 'updated_at'])
            raise CommandError(f'AI generation failed: {e}')

        self.stdout.write(self.style.SUCCESS(f"AIRecommendation {record.id} completed"))
