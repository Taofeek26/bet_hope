"""
Prediction Serializers
"""
from rest_framework import serializers

from apps.predictions.models import Prediction, ModelVersion


class ModelVersionSerializer(serializers.ModelSerializer):
    """Serializer for model versions."""

    class Meta:
        model = ModelVersion
        fields = [
            'id',
            'version',
            'model_type',
            'accuracy',
            'status',
            'trained_at',
        ]


class PredictionSerializer(serializers.ModelSerializer):
    """Standard prediction serializer."""

    match_id = serializers.IntegerField(source='match.id', read_only=True)
    match = serializers.SerializerMethodField()
    probabilities = serializers.SerializerMethodField()
    recommended_bet = serializers.SerializerMethodField()
    result_verification = serializers.SerializerMethodField()

    class Meta:
        model = Prediction
        fields = [
            'id',
            'match_id',
            'match',
            'model_version',
            'recommended_outcome',
            'confidence_score',
            'prediction_strength',
            'probabilities',
            'predicted_home_score',
            'predicted_away_score',
            'recommended_bet',
            'result_verification',
            'created_at',
        ]

    def get_match(self, obj) -> dict:
        return {
            'id': obj.match.id,
            'home_team': obj.match.home_team.name,
            'away_team': obj.match.away_team.name,
            'match_date': obj.match.match_date.isoformat(),
            'kickoff_time': obj.match.kickoff_time.strftime('%H:%M') if obj.match.kickoff_time else None,
            'league': obj.match.season.league.name if obj.match.season else None,
            'status': obj.match.status,
        }

    def get_probabilities(self, obj) -> dict:
        return {
            'home': float(obj.home_win_probability),
            'draw': float(obj.draw_probability),
            'away': float(obj.away_win_probability),
        }

    def get_recommended_bet(self, obj) -> dict:
        """Get the recommended bet based on probabilities."""
        probs = {
            'HOME': float(obj.home_win_probability),
            'DRAW': float(obj.draw_probability),
            'AWAY': float(obj.away_win_probability),
        }

        best_outcome = max(probs, key=probs.get)
        best_prob = probs[best_outcome]

        # Calculate fair odds
        fair_odds = round(1 / best_prob, 2) if best_prob > 0 else 0

        return {
            'outcome': best_outcome,
            'probability': best_prob,
            'confidence': obj.prediction_strength,
            'fair_odds': fair_odds,
        }

    def get_result_verification(self, obj) -> dict:
        """Check if prediction was correct for finished matches."""
        if obj.match.status != 'finished':
            return None

        if obj.match.home_score is None or obj.match.away_score is None:
            return None

        # Determine actual result
        if obj.match.home_score > obj.match.away_score:
            actual = 'HOME'
        elif obj.match.home_score < obj.match.away_score:
            actual = 'AWAY'
        else:
            actual = 'DRAW'

        is_correct = obj.recommended_outcome == actual

        return {
            'actual_result': actual,
            'actual_score': f"{obj.match.home_score}-{obj.match.away_score}",
            'predicted_result': obj.recommended_outcome,
            'predicted_score': f"{round(float(obj.predicted_home_score or 0))}-{round(float(obj.predicted_away_score or 0))}" if obj.predicted_home_score is not None else None,
            'is_correct': is_correct,
        }


class PredictionSummarySerializer(serializers.ModelSerializer):
    """Lightweight prediction summary for lists."""

    class Meta:
        model = Prediction
        fields = [
            'recommended_outcome',
            'confidence_score',
            'home_win_probability',
            'draw_probability',
            'away_win_probability',
        ]


class PredictionDetailSerializer(serializers.ModelSerializer):
    """Detailed prediction with match context."""

    match = serializers.SerializerMethodField()
    probabilities = serializers.SerializerMethodField()
    value_bets = serializers.SerializerMethodField()
    accuracy_check = serializers.SerializerMethodField()

    class Meta:
        model = Prediction
        fields = [
            'id',
            'match',
            'model_version',
            'model_type',
            'recommended_outcome',
            'confidence_score',
            'prediction_strength',
            'probabilities',
            'predicted_home_score',
            'predicted_away_score',
            'key_factors',
            'value_bets',
            'accuracy_check',
            'created_at',
        ]

    def get_match(self, obj) -> dict:
        return {
            'id': obj.match.id,
            'home_team': obj.match.home_team.name,
            'away_team': obj.match.away_team.name,
            'date': obj.match.match_date.isoformat(),
            'status': obj.match.status,
            'score': f"{obj.match.home_score}-{obj.match.away_score}" if obj.match.status == 'finished' else None,
        }

    def get_probabilities(self, obj) -> dict:
        return {
            'home_win': {
                'probability': float(obj.home_win_probability),
                'percentage': f"{float(obj.home_win_probability) * 100:.1f}%",
            },
            'draw': {
                'probability': float(obj.draw_probability),
                'percentage': f"{float(obj.draw_probability) * 100:.1f}%",
            },
            'away_win': {
                'probability': float(obj.away_win_probability),
                'percentage': f"{float(obj.away_win_probability) * 100:.1f}%",
            },
        }

    def get_value_bets(self, obj) -> list:
        """Identify potential value bets."""
        value_bets = []

        # Check if match has odds
        if hasattr(obj.match, 'odds') and obj.match.odds:
            odds = obj.match.odds

            checks = [
                ('home_win', obj.home_win_probability, odds.home_odds),
                ('draw', obj.draw_probability, odds.draw_odds),
                ('away_win', obj.away_win_probability, odds.away_odds),
            ]

            for market, model_prob, market_odds in checks:
                if market_odds and float(market_odds) > 1:
                    implied_prob = 1 / float(market_odds)
                    edge = float(model_prob) - implied_prob

                    if edge > 0.05:  # 5% edge threshold
                        value_bets.append({
                            'market': market,
                            'model_prob': float(model_prob),
                            'market_prob': round(implied_prob, 3),
                            'edge': round(edge, 3),
                            'odds': float(market_odds),
                            'rating': 'strong' if edge > 0.1 else 'moderate',
                        })

        return value_bets

    def get_accuracy_check(self, obj) -> dict:
        """Check prediction accuracy if match is finished."""
        if obj.match.status != 'finished':
            return {'status': 'pending'}

        # Determine actual result
        if obj.match.home_score > obj.match.away_score:
            actual = 'HOME'
        elif obj.match.home_score < obj.match.away_score:
            actual = 'AWAY'
        else:
            actual = 'DRAW'

        is_correct = obj.recommended_outcome == actual
        total_goals = obj.match.home_score + obj.match.away_score

        return {
            'status': 'verified',
            'predicted': obj.recommended_outcome,
            'actual': actual,
            'correct': is_correct,
            'predicted_home_score': float(obj.predicted_home_score) if obj.predicted_home_score else None,
            'predicted_away_score': float(obj.predicted_away_score) if obj.predicted_away_score else None,
            'goals_actual': total_goals,
        }


class PredictionRequestSerializer(serializers.Serializer):
    """Serializer for prediction requests."""

    home_team_id = serializers.IntegerField()
    away_team_id = serializers.IntegerField()
    match_date = serializers.DateField()
    season_code = serializers.CharField(required=False, allow_null=True)

    def validate(self, data):
        if data['home_team_id'] == data['away_team_id']:
            raise serializers.ValidationError("Home and away teams must be different")
        return data


class BatchPredictionRequestSerializer(serializers.Serializer):
    """Serializer for batch prediction requests."""

    matches = PredictionRequestSerializer(many=True)
    save_to_db = serializers.BooleanField(default=False)


class PredictionStatsSerializer(serializers.Serializer):
    """Serializer for prediction statistics."""

    total_predictions = serializers.IntegerField()
    verified_predictions = serializers.IntegerField()
    accuracy = serializers.FloatField()
    accuracy_by_outcome = serializers.DictField()
    roi = serializers.FloatField(required=False)
    period = serializers.CharField()
