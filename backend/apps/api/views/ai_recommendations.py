"""
AI Recommendation Views
"""
import json
import logging
from datetime import timedelta

import boto3
from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.throttling import ScopedRateThrottle

from apps.documents.models import AIRecommendation, Document
from apps.api.serializers.ai_recommendations import (
    AIRecommendationSerializer,
    AIRecommendationRequestSerializer,
    AIProvidersSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
)

logger = logging.getLogger(__name__)


class AIRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AI recommendations.

    Provides:
    - List recommendations
    - Get recommendation details
    - Generate new recommendation
    - Get available providers
    """

    queryset = AIRecommendation.objects.all()
    serializer_class = AIRecommendationSerializer
    permission_classes = [AllowAny]

    def get_throttles(self):
        # generate costs an LLM call: its own strict per-visitor limit on
        # top of the normal read limit (settings THROTTLE_AI_GENERATE).
        if self.action == 'generate':
            self.throttle_scope = 'ai_generate'
            return [ScopedRateThrottle(), *super().get_throttles()]
        return super().get_throttles()

    def get_queryset(self):
        queryset = AIRecommendation.objects.select_related(
            'prediction', 'prediction__match',
            'prediction__match__home_team',
            'prediction__match__away_team'
        )

        # Filter by prediction
        prediction_id = self.request.query_params.get('prediction_id')
        if prediction_id:
            queryset = queryset.filter(prediction_id=prediction_id)

        # Filter by provider
        provider = self.request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider=provider)

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate AI recommendation for a prediction.

        POST /api/v1/ai-recommendations/generate/
        {
            "prediction_id": 123,
            "provider": "openai",  // or "anthropic", "google"
            "include_rag": true
        }
        """
        serializer = AIRecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Phase 0 (SEC-01): this endpoint is public and every call costs
        # money, so reuse a recent result and enforce a daily ceiling.
        reuse_after = timezone.now() - timedelta(hours=settings.AI_REUSE_HOURS)
        recent_done = AIRecommendation.objects.filter(
            prediction_id=data['prediction_id'],
            status=AIRecommendation.Status.COMPLETED,
            created_at__gte=reuse_after,
        ).order_by('-created_at').first()
        if recent_done:
            return Response({**AIRecommendationSerializer(recent_done).data, 'reused': True})

        day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        started_today = AIRecommendation.objects.filter(created_at__gte=day_start).count()
        if started_today >= settings.AI_DAILY_GENERATION_LIMIT:
            return Response(
                {'error': 'The daily AI analysis limit has been reached. Please try again tomorrow.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if getattr(settings, 'MANAGE_FUNCTION_NAME', ''):
            return self._generate_async(data)

        # Local development (no manage Lambda): run inline as before.
        try:
            from apps.documents.services import AIRecommendationService

            service = AIRecommendationService(provider=data['provider'])
            result = service.generate_recommendation(
                prediction_id=data['prediction_id'],
                include_rag=data['include_rag'],
            )

            return Response({
                'status': 'success',
                'recommendation': result.recommendation,
                'confidence_assessment': result.confidence_assessment,
                'risk_analysis': result.risk_analysis,
                'key_factors': result.key_factors,
                'provider': result.provider,
                'model': result.model,
                'tokens_used': result.tokens_used,
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _generate_async(self, data):
        """
        Queue the LLM call in the manage Lambda and return 202 immediately.
        The LLM (a reasoning model via OpenRouter) often needs longer than
        API Gateway's 29s limit, which used to surface as a 504 while the
        call kept running and billing. The browser polls
        GET /ai-recommendations/{id}/ until status is completed/failed.
        """
        from apps.documents.services import AIRecommendationService

        # A double click (or two tabs) shouldn't pay for two LLM calls.
        recent = timezone.now() - timedelta(minutes=5)
        in_flight = AIRecommendation.objects.filter(
            prediction_id=data['prediction_id'],
            status__in=[AIRecommendation.Status.PENDING, AIRecommendation.Status.PROCESSING],
            created_at__gte=recent,
        ).first()
        if in_flight:
            return Response({'status': in_flight.status, 'id': in_flight.id},
                            status=status.HTTP_202_ACCEPTED)

        record = AIRecommendation.objects.create(
            prediction_id=data['prediction_id'],
            provider=data['provider'],
            model_name=AIRecommendationService.MODELS.get(data['provider'], ''),
            prompt='',
            status=AIRecommendation.Status.PENDING,
        )
        args = ['--id', str(record.id)]
        if not data['include_rag']:
            args.append('--no-rag')
        try:
            boto3.client('lambda').invoke(
                FunctionName=settings.MANAGE_FUNCTION_NAME,
                InvocationType='Event',
                Payload=json.dumps({'command': 'generate_ai_recommendation', 'args': args}).encode(),
            )
        except Exception as e:
            logger.exception('Failed to queue AI recommendation %s', record.id)
            record.status = AIRecommendation.Status.FAILED
            record.error_message = f'Failed to start: {e}'
            record.save(update_fields=['status', 'error_message', 'updated_at'])
            return Response({'status': 'failed', 'id': record.id, 'error': 'Could not start AI analysis'},
                            status=status.HTTP_502_BAD_GATEWAY)

        return Response({'status': record.status, 'id': record.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'])
    def providers(self, request):
        """Get available AI providers."""
        from apps.documents.services import AIRecommendationService

        available = AIRecommendationService.get_available_providers()

        return Response({
            'providers': available,
            'default': available[0] if available else None,
        })

    @action(detail=False, methods=['get'], url_path='for-prediction/(?P<prediction_id>[^/.]+)')
    def for_prediction(self, request, prediction_id=None):
        """Get AI recommendation for a specific prediction."""
        recommendation = AIRecommendation.objects.filter(
            prediction_id=prediction_id,
            status=AIRecommendation.Status.COMPLETED,
        ).order_by('-created_at').first()

        if recommendation:
            return Response(AIRecommendationSerializer(recommendation).data)
        else:
            return Response(
                {'error': 'No recommendation found for this prediction'},
                status=status.HTTP_404_NOT_FOUND
            )


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing documents.

    Provides:
    - List/retrieve documents
    - Upload new documents
    - Embed documents for RAG
    """

    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    # Phase 0 (SEC-01): documents feed the AI prompt, so anonymous writes
    # were a prompt-injection path; scraping, embedding and search also
    # spend API money. Only browsing stays public.
    PUBLIC_ACTIONS = {'list', 'retrieve', 'stats'}

    def get_permissions(self):
        if self.action in self.PUBLIC_ACTIONS:
            return [AllowAny()]
        return [IsAdminUser()]

    def get_queryset(self):
        queryset = Document.objects.filter(is_active=True)

        # Filter by type
        doc_type = self.request.query_params.get('type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload and embed a new document.

        POST /api/v1/documents/upload/
        {
            "title": "Document Title",
            "content": "Document content...",
            "document_type": "betting_guide",
            "source_url": "https://...",
            "author": "Author Name",
            "team_ids": [1, 2],
            "league_ids": [1]
        }
        """
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            # Create document
            document = Document.objects.create(
                title=data['title'],
                content=data['content'],
                document_type=data['document_type'],
                source_url=data.get('source_url'),
                author=data.get('author', ''),
            )

            # Add relationships
            if data.get('team_ids'):
                document.teams.set(data['team_ids'])
            if data.get('league_ids'):
                document.leagues.set(data['league_ids'])

            # Embed document
            from apps.documents.services import EmbeddingService

            embedding_service = EmbeddingService()
            num_chunks = embedding_service.embed_document(document.id)

            return Response({
                'status': 'success',
                'document_id': document.id,
                'chunks_created': num_chunks,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def embed(self, request, pk=None):
        """Re-embed an existing document."""
        document = self.get_object()

        try:
            from apps.documents.services import EmbeddingService

            embedding_service = EmbeddingService()
            num_chunks = embedding_service.embed_document(document.id)

            return Response({
                'status': 'success',
                'document_id': document.id,
                'chunks_created': num_chunks,
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search documents using vector similarity.

        GET /api/v1/documents/search/?q=betting strategy&top_k=5
        """
        query = request.query_params.get('q', '')
        top_k = int(request.query_params.get('top_k', 5))

        if not query:
            return Response(
                {'error': 'Query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from apps.documents.services import RAGService

            rag_service = RAGService()
            results = rag_service.retrieve(query, top_k=top_k)

            return Response({
                'query': query,
                'results': [
                    {
                        'document_id': r.document_id,
                        'document_title': r.document_title,
                        'content': r.content,
                        'score': r.score,
                        'metadata': r.metadata,
                    }
                    for r in results
                ],
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """
        Trigger a full document refresh (scrape, update, embed).

        POST /api/v1/documents/refresh/
        {
            "async": true,  // Run as Celery task (default)
            "include_news": true  // Include football news scraping
        }
        """
        run_async = request.data.get('async', True)
        include_news = request.data.get('include_news', True)

        try:
            if run_async:
                from tasks.documents import refresh_all_documents

                result = refresh_all_documents.delay(include_news=include_news)

                return Response({
                    'status': 'queued',
                    'task_id': result.id,
                    'message': 'Document refresh task queued',
                })
            else:
                # Run synchronously
                from tasks.documents import (
                    scrape_documentation,
                    update_strategy_documents,
                    embed_documents,
                    scrape_football_news,
                )

                scrape_result = scrape_documentation()
                strategy_result = update_strategy_documents()

                news_result = None
                if include_news:
                    try:
                        news_result = scrape_football_news()
                    except Exception as e:
                        news_result = {'status': 'error', 'message': str(e)}

                embed_result = embed_documents()

                return Response({
                    'status': 'success',
                    'scrape': scrape_result,
                    'strategy': strategy_result,
                    'news': news_result,
                    'embed': embed_result,
                })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='scrape-news')
    def scrape_news(self, request):
        """
        Scrape latest football news from RSS feeds.

        POST /api/v1/documents/scrape-news/
        {
            "async": true,
            "max_articles": 10
        }
        """
        run_async = request.data.get('async', True)
        max_articles = request.data.get('max_articles', 10)

        try:
            from tasks.documents import scrape_football_news

            if run_async:
                result = scrape_football_news.delay(max_articles_per_feed=max_articles)
                return Response({
                    'status': 'queued',
                    'task_id': result.id,
                    'message': 'News scraping task queued',
                })
            else:
                result = scrape_football_news(max_articles_per_feed=max_articles)
                return Response(result)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get document statistics.

        GET /api/v1/documents/stats/
        """
        from apps.documents.models import DocumentChunk

        total_docs = Document.objects.filter(is_active=True).count()
        total_chunks = DocumentChunk.objects.count()
        embedded_chunks = DocumentChunk.objects.filter(embedding__isnull=False).count()

        by_type = Document.objects.filter(is_active=True).values(
            'document_type'
        ).annotate(count=models.Count('id'))

        return Response({
            'total_documents': total_docs,
            'total_chunks': total_chunks,
            'embedded_chunks': embedded_chunks,
            'by_type': {item['document_type']: item['count'] for item in by_type},
        })
