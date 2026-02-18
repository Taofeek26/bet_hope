"""
Team Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q

from apps.teams.models import Team, TeamSeasonStats, HeadToHead
from apps.api.serializers import (
    TeamSerializer,
    TeamDetailSerializer,
    TeamSeasonStatsSerializer,
)


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing teams.

    Provides:
    - List all teams
    - Retrieve single team with details
    - Get team statistics
    - Get team fixtures
    - Head-to-head comparison
    """

    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TeamDetailSerializer
        return TeamSerializer

    def get_queryset(self):
        queryset = Team.objects.select_related('league')

        # Filter by league
        league = self.request.query_params.get('league')
        if league:
            queryset = queryset.filter(league__code=league)

        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(short_name__icontains=search)
            )

        return queryset.order_by('name')

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get team statistics across seasons."""
        team = self.get_object()

        stats = TeamSeasonStats.objects.filter(
            team=team
        ).select_related('season').order_by('-season__code')

        return Response({
            'team': TeamSerializer(team).data,
            'seasons': TeamSeasonStatsSerializer(stats, many=True).data,
        })

    @action(detail=True, methods=['get'])
    def fixtures(self, request, pk=None):
        """Get team fixtures (past and upcoming)."""
        team = self.get_object()

        from apps.matches.models import Match
        from apps.api.serializers import MatchListSerializer
        from django.utils import timezone

        # Get matches
        matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team)
        ).select_related(
            'home_team', 'away_team', 'season'
        ).order_by('-match_date')

        # Separate past and upcoming
        today = timezone.now().date()

        past = matches.filter(match_date__lt=today)[:10]
        upcoming = matches.filter(match_date__gte=today)[:10]

        return Response({
            'team': TeamSerializer(team).data,
            'past_matches': MatchListSerializer(past, many=True).data,
            'upcoming_matches': MatchListSerializer(upcoming, many=True).data,
        })

    @action(detail=True, methods=['get'])
    def form(self, request, pk=None):
        """Get team's recent form."""
        team = self.get_object()

        from apps.matches.models import Match
        from django.utils import timezone

        # Get last 10 matches
        matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            status=Match.Status.FINISHED,
        ).select_related(
            'home_team', 'away_team'
        ).order_by('-match_date')[:10]

        form_data = []
        total_points = 0
        total_goals_for = 0
        total_goals_against = 0

        for match in matches:
            is_home = match.home_team_id == team.id

            if is_home:
                goals_for = match.home_score or 0
                goals_against = match.away_score or 0
                opponent = match.away_team.name
            else:
                goals_for = match.away_score or 0
                goals_against = match.home_score or 0
                opponent = match.home_team.name

            if goals_for > goals_against:
                result = 'W'
                points = 3
            elif goals_for == goals_against:
                result = 'D'
                points = 1
            else:
                result = 'L'
                points = 0

            total_points += points
            total_goals_for += goals_for
            total_goals_against += goals_against

            form_data.append({
                'match_id': match.id,
                'date': match.match_date.isoformat(),
                'opponent': opponent,
                'venue': 'H' if is_home else 'A',
                'score': f"{goals_for}-{goals_against}",
                'result': result,
                'points': points,
            })

        n = len(form_data)
        return Response({
            'team': TeamSerializer(team).data,
            'form_string': ''.join(m['result'] for m in form_data),
            'summary': {
                'matches': n,
                'points': total_points,
                'ppg': round(total_points / n, 2) if n > 0 else 0,
                'goals_for': total_goals_for,
                'goals_against': total_goals_against,
                'goal_diff': total_goals_for - total_goals_against,
            },
            'matches': form_data,
        })

    @action(detail=True, methods=['get'], url_path='h2h/(?P<opponent_id>[^/.]+)')
    def head_to_head(self, request, pk=None, opponent_id=None):
        """Get head-to-head record against another team."""
        team = self.get_object()

        try:
            opponent = Team.objects.get(pk=opponent_id)
        except Team.DoesNotExist:
            return Response(
                {'error': 'Opponent team not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get H2H record
        h2h = HeadToHead.objects.filter(
            Q(team1=team, team2=opponent) |
            Q(team1=opponent, team2=team)
        ).first()

        # Get recent matches between teams
        from apps.matches.models import Match
        from apps.api.serializers import MatchListSerializer

        matches = Match.objects.filter(
            Q(home_team=team, away_team=opponent) |
            Q(home_team=opponent, away_team=team),
            status=Match.Status.FINISHED,
        ).order_by('-match_date')[:10]

        if h2h:
            # Normalize so team is always "team1" in response
            if h2h.team1_id == team.id:
                h2h_data = {
                    'total_matches': h2h.total_matches,
                    'team_wins': h2h.team1_wins,
                    'opponent_wins': h2h.team2_wins,
                    'draws': h2h.draws,
                    'team_goals': h2h.team1_goals,
                    'opponent_goals': h2h.team2_goals,
                }
            else:
                h2h_data = {
                    'total_matches': h2h.total_matches,
                    'team_wins': h2h.team2_wins,
                    'opponent_wins': h2h.team1_wins,
                    'draws': h2h.draws,
                    'team_goals': h2h.team2_goals,
                    'opponent_goals': h2h.team1_goals,
                }
        else:
            h2h_data = None

        return Response({
            'team': TeamSerializer(team).data,
            'opponent': TeamSerializer(opponent).data,
            'head_to_head': h2h_data,
            'recent_matches': MatchListSerializer(matches, many=True).data,
        })
