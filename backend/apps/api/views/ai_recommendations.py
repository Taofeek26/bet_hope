"""
AI Recommendation Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.documents.models import AIRecommendation, Document
from apps.api.serializers.ai_recommendations import (
    AIRecommendationSerializer,
    AIRecommendationRequestSerializer,
    AIProvidersSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
)


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
    permission_classes = [AllowAny]

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
