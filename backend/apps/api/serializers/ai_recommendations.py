"""
AI Recommendation Serializers
"""
from rest_framework import serializers

from apps.documents.models import AIRecommendation, Document, DocumentChunk


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents."""

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'document_type',
            'source_url',
            'author',
            'created_at',
        ]


class AIRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for AI recommendations."""

    match_info = serializers.SerializerMethodField()
    prediction_summary = serializers.SerializerMethodField()

    class Meta:
        model = AIRecommendation
        fields = [
            'id',
            'provider',
            'model_name',
            'status',
            'recommendation',
            'confidence_assessment',
            'risk_analysis',
            'key_factors',
            'tokens_used',
            'processing_time_ms',
            'match_info',
            'prediction_summary',
            'created_at',
        ]

    def get_match_info(self, obj) -> dict:
        match = obj.prediction.match
        return {
            'id': match.id,
            'home_team': match.home_team.name,
            'away_team': match.away_team.name,
            'date': match.match_date.isoformat(),
            'league': match.season.league.name,
        }

    def get_prediction_summary(self, obj) -> dict:
        pred = obj.prediction
        return {
            'outcome': pred.predicted_outcome,
            'confidence': float(pred.confidence),
            'home_prob': float(pred.home_win_prob),
            'draw_prob': float(pred.draw_prob),
            'away_prob': float(pred.away_win_prob),
        }


class AIRecommendationRequestSerializer(serializers.Serializer):
    """Request serializer for generating AI recommendations."""

    prediction_id = serializers.IntegerField()
    provider = serializers.ChoiceField(
        choices=['openai', 'anthropic', 'google'],
        default='openai'
    )
    include_rag = serializers.BooleanField(default=True)

    def validate_prediction_id(self, value):
        from apps.predictions.models import Prediction

        if not Prediction.objects.filter(id=value).exists():
            raise serializers.ValidationError("Prediction not found")
        return value

    def validate_provider(self, value):
        from apps.documents.services import AIRecommendationService

        available = AIRecommendationService.get_available_providers()
        if value not in available:
            raise serializers.ValidationError(
                f"Provider '{value}' not available. Available: {available}"
            )
        return value


class AIProvidersSerializer(serializers.Serializer):
    """Serializer for available AI providers."""

    providers = serializers.ListField(child=serializers.CharField())
    default = serializers.CharField()


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document uploads."""

    title = serializers.CharField(max_length=500)
    content = serializers.CharField()
    document_type = serializers.ChoiceField(
        choices=[
            ('betting_guide', 'Betting Guide'),
            ('team_analysis', 'Team Analysis'),
            ('strategy', 'Strategy Document'),
            ('match_preview', 'Match Preview'),
            ('statistics', 'Statistics Report'),
            ('news', 'News Article'),
            ('other', 'Other'),
        ],
        default='other'
    )
    source_url = serializers.URLField(required=False, allow_null=True)
    author = serializers.CharField(max_length=200, required=False, allow_blank=True)
    team_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )
    league_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )
