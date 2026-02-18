"""
Match Views
"""
from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
from django.utils import timezone

from apps.matches.models import Match
from apps.api.serializers import (
    MatchSerializer,
    MatchDetailSerializer,
    MatchListSerializer,
)


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing matches.

    Provides:
    - List matches with filters
    - Retrieve single match with details
    - Get upcoming matches
    - Get live matches
    - Get results
    """

    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MatchDetailSerializer
        if self.action == 'list':
            return MatchListSerializer
        return MatchSerializer

    def get_queryset(self):
        queryset = Match.objects.select_related(
            'home_team', 'away_team', 'season', 'season__league',
            'statistics', 'odds'
        ).prefetch_related('predictions')

        # Filter by league
        league = self.request.query_params.get('league')
        if league:
            queryset = queryset.filter(season__league__code=league)

        # Filter by season
        season = self.request.query_params.get('season')
        if season:
            queryset = queryset.filter(season__code=season)

        # Filter by team
        team = self.request.query_params.get('team')
        if team:
            queryset = queryset.filter(
                Q(home_team_id=team) | Q(away_team_id=team)
            )

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(match_date__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(match_date__lte=date_to)

        # Filter by status
        match_status = self.request.query_params.get('status')
        if match_status:
            queryset = queryset.filter(status=match_status)

        return queryset.order_by('-match_date', 'kickoff_time')

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming matches for next 7 days."""
        today = timezone.now().date()
        end_date = today + timedelta(days=7)

        matches = Match.objects.filter(
            match_date__gte=today,
            match_date__lte=end_date,
            status=Match.Status.SCHEDULED,
        ).select_related(
            'home_team', 'away_team', 'season__league'
        ).prefetch_related('predictions').order_by('match_date', 'kickoff_time')

        # Group by date
        grouped = {}
        for match in matches:
            date_str = match.match_date.isoformat()
            if date_str not in grouped:
                grouped[date_str] = []
            grouped[date_str].append(MatchListSerializer(match).data)

        return Response({
            'start_date': today.isoformat(),
            'end_date': end_date.isoformat(),
            'total_matches': matches.count(),
            'matches_by_date': grouped,
        })

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's matches."""
        today = timezone.now().date()

        matches = Match.objects.filter(
            match_date=today
        ).select_related(
            'home_team', 'away_team', 'season__league'
        ).prefetch_related('predictions').order_by('kickoff_time')

        # Separate by status
        scheduled = matches.filter(status=Match.Status.SCHEDULED)
        live = matches.filter(status=Match.Status.LIVE)
        finished = matches.filter(status=Match.Status.FINISHED)

        return Response({
            'date': today.isoformat(),
            'scheduled': MatchListSerializer(scheduled, many=True).data,
            'live': MatchListSerializer(live, many=True).data,
            'finished': MatchListSerializer(finished, many=True).data,
        })

    @action(detail=False, methods=['get'])
    def results(self, request):
        """Get recent results."""
        days = int(request.query_params.get('days', 7))
        days = min(days, 30)  # Cap at 30 days

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        matches = Match.objects.filter(
            match_date__gte=start_date,
            match_date__lte=end_date,
            status=Match.Status.FINISHED,
        ).select_related(
            'home_team', 'away_team', 'season__league'
        ).prefetch_related('predictions').order_by('-match_date', '-kickoff_time')

        # Optional league filter
        league = request.query_params.get('league')
        if league:
            matches = matches.filter(season__league__code=league)

        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        total = matches.count()
        matches = matches[start_idx:end_idx]

        return Response({
            'period': f"{start_date} to {end_date}",
            'total': total,
            'page': page,
            'page_size': page_size,
            'results': MatchListSerializer(matches, many=True).data,
        })

    @action(detail=False, methods=['get'])
    def live(self, request):
        """Get currently live matches."""
        matches = Match.objects.filter(
            status=Match.Status.LIVE
        ).select_related(
            'home_team', 'away_team', 'season__league'
        ).order_by('match_date', 'kickoff_time')

        return Response({
            'count': matches.count(),
            'matches': MatchSerializer(matches, many=True).data,
        })

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get detailed match statistics."""
        match = self.get_object()

        from apps.matches.models import MatchStatistics, MatchOdds
        from apps.api.serializers import MatchStatisticsSerializer, MatchOddsSerializer

        data = {
            'match': MatchSerializer(match).data,
        }

        # Get statistics
        try:
            stats = MatchStatistics.objects.get(match=match)
            data['statistics'] = MatchStatisticsSerializer(stats).data
        except MatchStatistics.DoesNotExist:
            data['statistics'] = None

        # Get odds
        try:
            odds = MatchOdds.objects.get(match=match)
            data['odds'] = MatchOddsSerializer(odds).data
        except MatchOdds.DoesNotExist:
            data['odds'] = None

        return Response(data)

    @action(detail=True, methods=['get'])
    def prediction(self, request, pk=None):
        """Get prediction for a match."""
        match = self.get_object()

        from apps.predictions.models import Prediction
        from apps.api.serializers import PredictionDetailSerializer

        try:
            prediction = Prediction.objects.select_related('model_version').get(match=match)
            return Response(PredictionDetailSerializer(prediction).data)
        except Prediction.DoesNotExist:
            # Generate prediction on demand
            from apps.ml_pipeline.inference import MatchPredictor

            predictor = MatchPredictor()

            try:
                result = predictor.predict_match(
                    home_team_id=match.home_team_id,
                    away_team_id=match.away_team_id,
                    match_date=match.match_date,
                    season_code=match.season.code,
                    save_to_db=True,
                    match_id=match.id
                )

                return Response({
                    'match_id': match.id,
                    'prediction': result,
                    'generated': True,
                })

            except Exception as e:
                return Response(
                    {'error': f'Could not generate prediction: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    @action(detail=False, methods=['get'])
    def with_predictions(self, request):
        """Get upcoming matches that have predictions."""
        today = timezone.now().date()
        end_date = today + timedelta(days=7)

        matches = Match.objects.filter(
            match_date__gte=today,
            match_date__lte=end_date,
            status=Match.Status.SCHEDULED,
            predictions__isnull=False,
        ).select_related(
            'home_team', 'away_team', 'season__league'
        ).prefetch_related('predictions').order_by('match_date', 'kickoff_time').distinct()

        # Optional filter by confidence
        min_confidence = request.query_params.get('min_confidence')
        if min_confidence:
            matches = matches.filter(
                predictions__confidence_score__gte=float(min_confidence)
            )

        from apps.api.serializers.matches import UpcomingMatchSerializer

        return Response({
            'total': matches.count(),
            'matches': UpcomingMatchSerializer(matches, many=True).data,
        })
