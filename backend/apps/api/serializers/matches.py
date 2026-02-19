"""
Match Serializers
"""
from rest_framework import serializers

from apps.matches.models import Match, MatchStatistics, MatchOdds
from .teams import TeamSerializer


class MatchOddsSerializer(serializers.ModelSerializer):
    """Serializer for match odds."""

    implied_probs = serializers.SerializerMethodField()

    class Meta:
        model = MatchOdds
        fields = [
            'home_odds',
            'draw_odds',
            'away_odds',
            'over_25_odds',
            'under_25_odds',
            'implied_probs',
        ]

    def get_implied_probs(self, obj) -> dict:
        """Calculate implied probabilities from odds."""
        probs = {}

        if obj.home_odds and float(obj.home_odds) > 1:
            probs['home'] = round(1 / float(obj.home_odds), 3)
        if obj.draw_odds and float(obj.draw_odds) > 1:
            probs['draw'] = round(1 / float(obj.draw_odds), 3)
        if obj.away_odds and float(obj.away_odds) > 1:
            probs['away'] = round(1 / float(obj.away_odds), 3)

        # Normalize
        total = sum(probs.values())
        if total > 0:
            probs = {k: round(v / total, 3) for k, v in probs.items()}

        return probs


class MatchStatisticsSerializer(serializers.ModelSerializer):
    """Serializer for match statistics."""

    class Meta:
        model = MatchStatistics
        fields = [
            'shots_home',
            'shots_away',
            'shots_on_target_home',
            'shots_on_target_away',
            'corners_home',
            'corners_away',
            'fouls_home',
            'fouls_away',
            'yellow_cards_home',
            'yellow_cards_away',
            'red_cards_home',
            'red_cards_away',
            'possession_home',
            'possession_away',
        ]


class MatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for match lists."""

    home_team_name = serializers.CharField(source='home_team.name', read_only=True)
    away_team_name = serializers.CharField(source='away_team.name', read_only=True)
    home_team_logo = serializers.CharField(source='home_team.logo_url', read_only=True)
    away_team_logo = serializers.CharField(source='away_team.logo_url', read_only=True)
    league_name = serializers.CharField(source='season.league.name', read_only=True)
    has_prediction = serializers.SerializerMethodField()
    prediction = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            'id',
            'home_team',
            'home_team_name',
            'home_team_logo',
            'away_team',
            'away_team_name',
            'away_team_logo',
            'match_date',
            'kickoff_time',
            'home_score',
            'away_score',
            'status',
            'league_name',
            'has_prediction',
            'prediction',
        ]

    def get_has_prediction(self, obj) -> bool:
        # Check if predictions were prefetched, otherwise query
        if hasattr(obj, '_prefetched_objects_cache') and 'predictions' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['predictions']) > 0
        return obj.predictions.exists()

    def get_prediction(self, obj):
        from .predictions import PredictionSerializer

        # Try prefetched predictions first
        if hasattr(obj, '_prefetched_objects_cache') and 'predictions' in obj._prefetched_objects_cache:
            predictions = obj._prefetched_objects_cache['predictions']
            if predictions:
                return PredictionSerializer(predictions[0]).data
            return None

        # Fall back to query
        prediction = obj.predictions.order_by('-created_at').first()
        if prediction:
            return PredictionSerializer(prediction).data
        return None


class MatchSerializer(serializers.ModelSerializer):
    """Standard match serializer."""

    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)
    season_name = serializers.CharField(source='season.name', read_only=True)
    league_name = serializers.CharField(source='season.league.name', read_only=True)
    result = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            'id',
            'season',
            'season_name',
            'league_name',
            'home_team',
            'away_team',
            'match_date',
            'kickoff_time',
            'home_score',
            'away_score',
            'home_halftime_score',
            'away_halftime_score',
            'status',
            'result',
        ]

    def get_result(self, obj) -> str:
        if obj.status != Match.Status.FINISHED:
            return None
        if obj.home_score > obj.away_score:
            return 'H'
        elif obj.home_score < obj.away_score:
            return 'A'
        return 'D'


class MatchDetailSerializer(serializers.ModelSerializer):
    """Detailed match serializer with all related data."""

    home_team = TeamSerializer(read_only=True)
    away_team = TeamSerializer(read_only=True)
    statistics = MatchStatisticsSerializer(read_only=True)
    odds = MatchOddsSerializer(read_only=True)
    prediction = serializers.SerializerMethodField()
    h2h = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            'id',
            'season',
            'home_team',
            'away_team',
            'match_date',
            'kickoff_time',
            'home_score',
            'away_score',
            'home_halftime_score',
            'away_halftime_score',
            'status',
            'statistics',
            'odds',
            'prediction',
            'h2h',
        ]

    def get_prediction(self, obj):
        from .predictions import PredictionSerializer

        # Try prefetched predictions first
        if hasattr(obj, '_prefetched_objects_cache') and 'predictions' in obj._prefetched_objects_cache:
            predictions = obj._prefetched_objects_cache['predictions']
            if predictions:
                return PredictionSerializer(predictions[0]).data
            return None

        # Fall back to query
        prediction = obj.predictions.order_by('-created_at').first()
        if prediction:
            return PredictionSerializer(prediction).data
        return None

    def get_h2h(self, obj) -> dict:
        """Get head-to-head summary."""
        from apps.teams.models import HeadToHead

        h2h = HeadToHead.objects.filter(
            team_a__in=[obj.home_team, obj.away_team],
            team_b__in=[obj.home_team, obj.away_team]
        ).first()

        if h2h:
            # Determine which team is which
            if h2h.team_a_id == obj.home_team_id:
                return {
                    'total_matches': h2h.total_matches,
                    'home_wins': h2h.team_a_wins,
                    'away_wins': h2h.team_b_wins,
                    'draws': h2h.draws,
                    'last_meeting': h2h.last_match_date.isoformat() if h2h.last_match_date else None,
                }
            else:
                return {
                    'total_matches': h2h.total_matches,
                    'home_wins': h2h.team_b_wins,
                    'away_wins': h2h.team_a_wins,
                    'draws': h2h.draws,
                    'last_meeting': h2h.last_match_date.isoformat() if h2h.last_match_date else None,
                }

        return None


class UpcomingMatchSerializer(serializers.ModelSerializer):
    """Serializer for upcoming matches with predictions."""

    home_team_name = serializers.CharField(source='home_team.name')
    away_team_name = serializers.CharField(source='away_team.name')
    home_team_logo = serializers.CharField(source='home_team.logo_url')
    away_team_logo = serializers.CharField(source='away_team.logo_url')
    league_name = serializers.CharField(source='season.league.name')
    prediction = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            'id',
            'home_team',
            'home_team_name',
            'home_team_logo',
            'away_team',
            'away_team_name',
            'away_team_logo',
            'match_date',
            'kickoff_time',
            'league_name',
            'prediction',
        ]

    def get_prediction(self, obj):
        from .predictions import PredictionSummarySerializer

        if hasattr(obj, 'prediction'):
            return PredictionSummarySerializer(obj.prediction).data
        return None
