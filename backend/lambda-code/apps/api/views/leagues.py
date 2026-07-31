"""
League and Season Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q

from apps.leagues.models import League, Season
from apps.api.serializers import LeagueSerializer, SeasonSerializer


class LeagueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing leagues.

    Provides:
    - List all leagues
    - Retrieve single league
    - Get league standings
    - Get league statistics
    """

    queryset = League.objects.all()
    serializer_class = LeagueSerializer
    permission_classes = [AllowAny]
    lookup_field = 'code'

    def get_queryset(self):
        queryset = League.objects.annotate(
            seasons_count=Count('seasons')
        )

        # Filter by country
        country = self.request.query_params.get('country')
        if country:
            queryset = queryset.filter(country__iexact=country)

        # Filter by tier
        tier = self.request.query_params.get('tier')
        if tier:
            queryset = queryset.filter(tier=tier)

        # Filter active only
        active_only = self.request.query_params.get('active')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset.order_by('country', 'tier', 'name')

    @action(detail=True, methods=['get'])
    def standings(self, request, code=None):
        """Get current standings for a league."""
        league = self.get_object()

        # Get current season (use league's current_season property)
        current_season_code = league.current_season
        current_season = Season.objects.filter(
            league=league,
            code=current_season_code
        ).first()

        if not current_season:
            # Fallback to latest season with matches
            current_season = Season.objects.filter(
                league=league
            ).order_by('-code').first()

        if not current_season:
            return Response(
                {'error': 'No season found'},
                status=status.HTTP_404_NOT_FOUND
            )

        from apps.teams.models import TeamSeasonStats
        from apps.matches.models import Match

        standings = TeamSeasonStats.objects.filter(
            season=current_season
        ).select_related('team').order_by('league_position', '-wins')

        # If no TeamSeasonStats, calculate from Match data
        if not standings.exists():
            standings_data = self._calculate_standings_from_matches(current_season)
        else:
            standings_data = []
            for i, stats in enumerate(standings, 1):
                standings_data.append({
                    'position': stats.league_position or i,
                    'team_id': stats.team.id,
                    'team_name': stats.team.name,
                    'team_logo': stats.team.logo_url,
                    'played': stats.matches_played,
                    'wins': stats.wins,
                    'draws': stats.draws,
                    'losses': stats.losses,
                    'goals_for': stats.goals_for,
                    'goals_against': stats.goals_against,
                    'goal_difference': stats.goals_for - stats.goals_against,
                    'points': stats.points,
                    'form': stats.form[:5] if stats.form else '',
                })

        return Response({
            'league': LeagueSerializer(league).data,
            'season': SeasonSerializer(current_season).data,
            'standings': standings_data,
        })

    def _calculate_standings_from_matches(self, season):
        """Calculate standings from match results."""
        from apps.matches.models import Match
        from collections import defaultdict

        # Get all finished matches for this season
        matches = Match.objects.filter(
            season=season,
            status=Match.Status.FINISHED
        ).select_related('home_team', 'away_team')

        # Build team stats
        team_stats = defaultdict(lambda: {
            'team_id': None,
            'team_name': '',
            'team_logo': '',
            'played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'points': 0,
            'form': [],
        })

        for match in matches:
            home = match.home_team
            away = match.away_team
            home_score = match.home_score or 0
            away_score = match.away_score or 0

            # Initialize team info
            if team_stats[home.id]['team_id'] is None:
                team_stats[home.id]['team_id'] = home.id
                team_stats[home.id]['team_name'] = home.name
                team_stats[home.id]['team_logo'] = home.logo_url or ''

            if team_stats[away.id]['team_id'] is None:
                team_stats[away.id]['team_id'] = away.id
                team_stats[away.id]['team_name'] = away.name
                team_stats[away.id]['team_logo'] = away.logo_url or ''

            # Update stats
            team_stats[home.id]['played'] += 1
            team_stats[away.id]['played'] += 1
            team_stats[home.id]['goals_for'] += home_score
            team_stats[home.id]['goals_against'] += away_score
            team_stats[away.id]['goals_for'] += away_score
            team_stats[away.id]['goals_against'] += home_score

            if home_score > away_score:
                team_stats[home.id]['wins'] += 1
                team_stats[home.id]['points'] += 3
                team_stats[home.id]['form'].append('W')
                team_stats[away.id]['losses'] += 1
                team_stats[away.id]['form'].append('L')
            elif away_score > home_score:
                team_stats[away.id]['wins'] += 1
                team_stats[away.id]['points'] += 3
                team_stats[away.id]['form'].append('W')
                team_stats[home.id]['losses'] += 1
                team_stats[home.id]['form'].append('L')
            else:
                team_stats[home.id]['draws'] += 1
                team_stats[home.id]['points'] += 1
                team_stats[home.id]['form'].append('D')
                team_stats[away.id]['draws'] += 1
                team_stats[away.id]['points'] += 1
                team_stats[away.id]['form'].append('D')

        # Convert to list and sort
        standings = []
        for team_id, stats in team_stats.items():
            stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
            stats['form'] = ''.join(stats['form'][-5:])  # Last 5 matches
            standings.append(stats)

        # Sort by points, goal difference, goals for
        standings.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

        # Add positions
        for i, team in enumerate(standings, 1):
            team['position'] = i

        return standings

    @action(detail=True, methods=['get'])
    def seasons(self, request, code=None):
        """Get all seasons for a league."""
        league = self.get_object()
        seasons = Season.objects.filter(league=league).order_by('-code')

        return Response({
            'league': LeagueSerializer(league).data,
            'seasons': SeasonSerializer(seasons, many=True).data,
        })

    @action(detail=True, methods=['get'])
    def stats(self, request, code=None):
        """Get aggregate statistics for a league."""
        league = self.get_object()

        from apps.matches.models import Match
        from django.db.models import Avg, Sum

        current_season = Season.objects.filter(
            league=league,
            is_current=True
        ).first()

        if not current_season:
            return Response({'error': 'No current season'}, status=404)

        matches = Match.objects.filter(
            season=current_season,
            status=Match.Status.FINISHED
        )

        total_matches = matches.count()
        if total_matches == 0:
            return Response({'error': 'No matches played'}, status=404)

        # Calculate statistics
        totals = matches.aggregate(
            total_goals=Sum('home_score') + Sum('away_score'),
            home_wins=Count('id', filter=Q(home_score__gt=F('away_score'))),
            away_wins=Count('id', filter=Q(away_score__gt=F('home_score'))),
            draws=Count('id', filter=Q(home_score=F('away_score'))),
        )

        from django.db.models import F

        home_wins = matches.filter(home_score__gt=F('away_score')).count()
        away_wins = matches.filter(away_score__gt=F('home_score')).count()
        draws = matches.filter(home_score=F('away_score')).count()

        total_goals = sum(
            (m.home_score or 0) + (m.away_score or 0)
            for m in matches
        )

        btts = matches.filter(
            home_score__gt=0,
            away_score__gt=0
        ).count()

        over_25 = sum(
            1 for m in matches
            if (m.home_score or 0) + (m.away_score or 0) > 2.5
        )

        return Response({
            'league': LeagueSerializer(league).data,
            'season': current_season.name,
            'statistics': {
                'total_matches': total_matches,
                'total_goals': total_goals,
                'goals_per_match': round(total_goals / total_matches, 2),
                'home_wins': home_wins,
                'home_win_pct': round(home_wins / total_matches * 100, 1),
                'away_wins': away_wins,
                'away_win_pct': round(away_wins / total_matches * 100, 1),
                'draws': draws,
                'draw_pct': round(draws / total_matches * 100, 1),
                'btts_matches': btts,
                'btts_pct': round(btts / total_matches * 100, 1),
                'over_25_matches': over_25,
                'over_25_pct': round(over_25 / total_matches * 100, 1),
            }
        })


class SeasonViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing seasons."""

    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Season.objects.select_related('league')

        # Filter by league
        league = self.request.query_params.get('league')
        if league:
            queryset = queryset.filter(league__code=league)

        # Filter current only
        current = self.request.query_params.get('current')
        if current and current.lower() == 'true':
            queryset = queryset.filter(is_current=True)

        return queryset.order_by('-code')
