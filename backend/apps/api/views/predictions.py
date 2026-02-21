"""
Prediction Views
"""
from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q, Avg, Count, F
from django.utils import timezone

from apps.predictions.models import Prediction, ModelVersion
from apps.api.serializers import (
    PredictionSerializer,
    PredictionDetailSerializer,
    PredictionRequestSerializer,
    BatchPredictionRequestSerializer,
    ModelVersionSerializer,
)


class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for predictions.

    Provides:
    - List predictions
    - Retrieve prediction details
    - Generate predictions
    - Get prediction statistics
    - Value bet suggestions
    """

    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PredictionDetailSerializer
        return PredictionSerializer

    def get_queryset(self):
        queryset = Prediction.objects.select_related(
            'match', 'match__home_team', 'match__away_team',
            'match__season__league'
        )

        # Filter by league
        league = self.request.query_params.get('league')
        if league:
            queryset = queryset.filter(match__season__league__code=league)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(match__match_date__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(match__match_date__lte=date_to)

        # Filter by minimum confidence
        min_conf = self.request.query_params.get('min_confidence')
        if min_conf:
            queryset = queryset.filter(confidence_score__gte=float(min_conf))

        return queryset.order_by('-match__match_date')

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate prediction for a single match."""
        serializer = PredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        from apps.ml_pipeline.inference import MatchPredictor

        predictor = MatchPredictor()

        try:
            result = predictor.predict_match(
                home_team_id=data['home_team_id'],
                away_team_id=data['away_team_id'],
                match_date=data['match_date'],
                season_code=data.get('season_code'),
                save_to_db=False
            )

            return Response(result)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def batch(self, request):
        """Generate predictions for multiple matches."""
        serializer = BatchPredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        from apps.ml_pipeline.inference import MatchPredictor

        predictor = MatchPredictor()
        results = predictor.predict_batch(
            matches=data['matches'],
            save_to_db=data.get('save_to_db', False)
        )

        return Response({
            'total': len(results),
            'predictions': results,
        })

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get predictions for upcoming matches."""
        today = timezone.now().date()
        days = int(request.query_params.get('days', 7))
        include_finished = request.query_params.get('include_finished', 'false').lower() == 'true'

        predictions = Prediction.objects.filter(
            match__match_date__gte=today,
            match__match_date__lte=today + timedelta(days=days),
        ).select_related(
            'match', 'match__home_team', 'match__away_team',
            'match__season__league'
        )

        # Only filter by status if not including finished
        if not include_finished:
            predictions = predictions.filter(match__status='scheduled')

        predictions = predictions.order_by('match__match_date', 'match__kickoff_time')

        # Optional confidence filter
        min_conf = request.query_params.get('min_confidence')
        if min_conf:
            predictions = predictions.filter(confidence_score__gte=float(min_conf))

        return Response({
            'period': f"{today} to {today + timedelta(days=days)}",
            'total': predictions.count(),
            'predictions': PredictionSerializer(predictions, many=True).data,
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get predictions for recent matches (including yesterday and today)."""
        today = timezone.now().date()
        days_back = int(request.query_params.get('days_back', 1))
        days_forward = int(request.query_params.get('days_forward', 7))
        include_finished = request.query_params.get('include_finished', 'true').lower() == 'true'

        start_date = today - timedelta(days=days_back)
        end_date = today + timedelta(days=days_forward)

        predictions = Prediction.objects.filter(
            match__match_date__gte=start_date,
            match__match_date__lte=end_date,
        ).select_related(
            'match', 'match__home_team', 'match__away_team',
            'match__season__league'
        )

        if not include_finished:
            predictions = predictions.filter(match__status='scheduled')

        predictions = predictions.order_by('-match__match_date', 'match__kickoff_time')

        # Optional confidence filter
        min_conf = request.query_params.get('min_confidence')
        if min_conf:
            predictions = predictions.filter(confidence_score__gte=float(min_conf))

        return Response({
            'period': f"{start_date} to {end_date}",
            'total': predictions.count(),
            'predictions': PredictionSerializer(predictions, many=True).data,
        })

    @action(detail=False, methods=['get'])
    def value_bets(self, request):
        """Get value bet suggestions."""
        today = timezone.now().date()

        # Support specific date filtering (like dashboard)
        date_str = request.query_params.get('date')
        days = int(request.query_params.get('days', 7))

        from apps.matches.models import Match, MatchOdds

        # Build date filter
        if date_str:
            # Specific date requested
            try:
                from datetime import datetime
                specific_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                date_filter = {'match_date': specific_date}
            except ValueError:
                date_filter = {
                    'match_date__gte': today,
                    'match_date__lte': today + timedelta(days=days),
                }
        else:
            # Default: next N days
            date_filter = {
                'match_date__gte': today,
                'match_date__lte': today + timedelta(days=days),
            }

        # Get upcoming matches with predictions and odds
        matches = Match.objects.filter(
            **date_filter,
            status='scheduled',
            predictions__isnull=False,
        ).select_related(
            'home_team', 'away_team', 'odds'
        ).prefetch_related('predictions').distinct()

        value_bets = []

        for match in matches:
            if not hasattr(match, 'odds') or not match.odds:
                continue

            # Get the latest prediction for the match
            prediction = match.predictions.order_by('-created_at').first()
            if not prediction:
                continue
            odds = match.odds

            # Check each market for value
            markets = [
                ('home', prediction.home_win_probability, odds.home_odds),
                ('draw', prediction.draw_probability, odds.draw_odds),
                ('away', prediction.away_win_probability, odds.away_odds),
            ]

            for market, model_prob, market_odds in markets:
                if not market_odds or float(market_odds) <= 1:
                    continue

                implied_prob = 1 / float(market_odds)
                edge = float(model_prob) - implied_prob

                # Only include if there's positive edge
                if edge > 0.05:  # 5% threshold
                    value_bets.append({
                        'match': {
                            'id': match.id,
                            'home_team': match.home_team.name,
                            'away_team': match.away_team.name,
                            'home_team_logo': match.home_team.logo_url,
                            'away_team_logo': match.away_team.logo_url,
                            'date': match.match_date.isoformat(),
                            'time': match.kickoff_time.isoformat() if match.kickoff_time else None,
                        },
                        'prediction_id': prediction.id,
                        'market': market,
                        'model_probability': float(model_prob),
                        'market_probability': round(implied_prob, 3),
                        'edge': round(edge, 3),
                        'odds': float(market_odds),
                        'confidence': float(prediction.confidence_score),
                        'rating': self._rate_value_bet(edge, float(prediction.confidence_score)),
                    })

        # Sort by edge
        value_bets.sort(key=lambda x: x['edge'], reverse=True)

        return Response({
            'total': len(value_bets),
            'value_bets': value_bets,
        })

    def _rate_value_bet(self, edge: float, confidence: float) -> str:
        """Rate a value bet based on edge and confidence."""
        if edge > 0.15 and confidence > 0.6:
            return 'strong'
        elif edge > 0.1 or (edge > 0.05 and confidence > 0.55):
            return 'moderate'
        return 'weak'

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get prediction accuracy statistics."""
        from apps.matches.models import Match

        # Time period filter
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        # Get predictions for finished matches
        predictions = Prediction.objects.filter(
            match__match_date__gte=start_date,
            match__status=Match.Status.FINISHED,
        ).select_related('match')

        if not predictions.exists():
            return Response({
                'error': 'No verified predictions found',
                'period': f'Last {days} days',
            })

        total = predictions.count()
        correct = 0
        by_outcome = {'H': {'total': 0, 'correct': 0}, 'D': {'total': 0, 'correct': 0}, 'A': {'total': 0, 'correct': 0}}
        by_confidence = {}

        for pred in predictions:
            match = pred.match

            # Skip if scores are None
            if match.home_score is None or match.away_score is None:
                continue

            # Determine actual result
            if match.home_score > match.away_score:
                actual = 'H'
            elif match.home_score < match.away_score:
                actual = 'A'
            else:
                actual = 'D'

            # Map recommended_outcome to H/D/A format
            outcome_map = {'HOME': 'H', 'DRAW': 'D', 'AWAY': 'A', 'H': 'H', 'D': 'D', 'A': 'A'}
            predicted = outcome_map.get(pred.recommended_outcome, pred.recommended_outcome)
            is_correct = predicted == actual

            if is_correct:
                correct += 1

            # Track by outcome
            if predicted in by_outcome:
                by_outcome[predicted]['total'] += 1
                if is_correct:
                    by_outcome[predicted]['correct'] += 1

            # Track by confidence level
            conf = float(pred.confidence_score)
            if conf >= 0.6:
                conf_level = 'high'
            elif conf >= 0.45:
                conf_level = 'medium'
            else:
                conf_level = 'low'

            if conf_level not in by_confidence:
                by_confidence[conf_level] = {'total': 0, 'correct': 0}
            by_confidence[conf_level]['total'] += 1
            if is_correct:
                by_confidence[conf_level]['correct'] += 1

        # Calculate accuracies
        accuracy = correct / total if total > 0 else 0

        outcome_accuracy = {}
        for outcome, data in by_outcome.items():
            if data['total'] > 0:
                outcome_accuracy[outcome] = {
                    'total': data['total'],
                    'correct': data['correct'],
                    'accuracy': round(data['correct'] / data['total'], 3),
                }

        confidence_accuracy = {}
        for level, data in by_confidence.items():
            if data['total'] > 0:
                confidence_accuracy[level] = {
                    'total': data['total'],
                    'correct': data['correct'],
                    'accuracy': round(data['correct'] / data['total'], 3),
                }

        return Response({
            'period': f'Last {days} days',
            'total_predictions': total,
            'correct_predictions': correct,
            'accuracy': round(accuracy, 3),
            'by_outcome': outcome_accuracy,
            'by_confidence': confidence_accuracy,
        })

    @action(detail=False, methods=['get'])
    def model_info(self, request):
        """Get information about the active model."""
        try:
            active_model = ModelVersion.objects.filter(status='active').first()

            if active_model:
                return Response(ModelVersionSerializer(active_model).data)
            else:
                return Response(
                    {'error': 'No active model found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def daily_picks(self, request):
        """Get top prediction picks for a specific date (default: today)."""
        from datetime import datetime

        # Parse date from query params, default to today
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()

        predictions = Prediction.objects.filter(
            match__match_date=target_date,
            match__status='scheduled',
            confidence_score__gte=0.55,
        ).select_related(
            'match', 'match__home_team', 'match__away_team',
            'match__season__league'
        ).order_by('-confidence_score')[:10]

        picks = []
        for pred in predictions:
            match = pred.match
            league = match.season.league
            league_display = f"{league.name} ({league.country})" if league.country else league.name
            picks.append({
                'match': {
                    'id': match.id,
                    'home_team': match.home_team.name,
                    'away_team': match.away_team.name,
                    'home_team_logo': match.home_team.logo_url,
                    'away_team_logo': match.away_team.logo_url,
                    'league': league_display,
                    'time': match.kickoff_time.strftime('%H:%M') if match.kickoff_time else None,
                },
                'prediction': {
                    'id': pred.id,
                    'outcome': pred.recommended_outcome,
                    'confidence': float(pred.confidence_score),
                    'probabilities': {
                        'home': float(pred.home_win_probability),
                        'draw': float(pred.draw_probability),
                        'away': float(pred.away_win_probability),
                    },
                },
                'risk': 'low' if pred.confidence_score >= 0.6 else 'medium',
            })

        return Response({
            'date': target_date.isoformat(),
            'total_picks': len(picks),
            'picks': picks,
        })

    @action(detail=False, methods=['get'])
    def weekly_availability(self, request):
        """Get prediction counts for next 7 days."""
        today = timezone.now().date()
        availability = []

        for i in range(7):
            date = today + timedelta(days=i)
            matches_count = Prediction.objects.filter(
                match__match_date=date,
                match__status='scheduled',
            ).count()
            high_conf_count = Prediction.objects.filter(
                match__match_date=date,
                match__status='scheduled',
                confidence_score__gte=0.55,
            ).count()
            availability.append({
                'date': date.isoformat(),
                'day_offset': i,
                'total_matches': matches_count,
                'high_confidence': high_conf_count,
            })

        return Response({
            'start_date': today.isoformat(),
            'days': availability,
        })
