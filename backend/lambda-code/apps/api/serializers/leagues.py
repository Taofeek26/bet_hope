"""
League and Season Serializers
"""
from rest_framework import serializers

from apps.leagues.models import League, Season


class LeagueSerializer(serializers.ModelSerializer):
    """Serializer for League model."""

    seasons_count = serializers.SerializerMethodField()
    teams_count = serializers.SerializerMethodField()
    matches_count = serializers.SerializerMethodField()
    predictions_count = serializers.SerializerMethodField()

    class Meta:
        model = League
        fields = [
            'id',
            'code',
            'name',
            'country',
            'tier',
            'logo_url',
            'is_active',
            'seasons_count',
            'teams_count',
            'matches_count',
            'predictions_count',
        ]
        read_only_fields = ['id', 'seasons_count', 'teams_count', 'matches_count', 'predictions_count']

    def get_seasons_count(self, obj) -> int:
        return obj.seasons.count()

    def get_teams_count(self, obj) -> int:
        return obj.teams.count()

    def get_matches_count(self, obj) -> int:
        from apps.matches.models import Match
        return Match.objects.filter(season__league=obj).count()

    def get_predictions_count(self, obj) -> int:
        from apps.predictions.models import Prediction
        return Prediction.objects.filter(match__season__league=obj).count()


class SeasonSerializer(serializers.ModelSerializer):
    """Serializer for Season model."""

    league = LeagueSerializer(read_only=True)
    league_id = serializers.PrimaryKeyRelatedField(
        queryset=League.objects.all(),
        source='league',
        write_only=True
    )
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Season
        fields = [
            'id',
            'league',
            'league_id',
            'code',
            'name',
            'start_date',
            'end_date',
            'is_current',
            'total_matches',
            'matches_played',
            'progress',
        ]
        read_only_fields = ['id', 'progress']

    def get_progress(self, obj) -> float:
        if obj.total_matches and obj.total_matches > 0:
            return round(obj.matches_played / obj.total_matches * 100, 1)
        return 0.0


class SeasonListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for season lists."""

    class Meta:
        model = Season
        fields = ['id', 'code', 'name', 'is_current']
