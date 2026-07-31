"""
Team Serializers
"""
from rest_framework import serializers

from apps.teams.models import Team, TeamSeasonStats, HeadToHead
from .leagues import LeagueSerializer


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for Team model."""

    league_name = serializers.CharField(source='league.name', read_only=True)

    class Meta:
        model = Team
        fields = [
            'id',
            'name',
            'short_name',
            'league',
            'league_name',
            'logo_url',
            'founded',
            'stadium',
        ]
        read_only_fields = ['id']


class TeamSeasonStatsSerializer(serializers.ModelSerializer):
    """Serializer for team season statistics."""

    season_name = serializers.CharField(source='season.name', read_only=True)
    played = serializers.IntegerField(source='matches_played', read_only=True)
    position = serializers.IntegerField(source='league_position', read_only=True)
    form_string = serializers.CharField(source='form', read_only=True)
    ppg = serializers.SerializerMethodField()
    goal_diff = serializers.SerializerMethodField()

    class Meta:
        model = TeamSeasonStats
        fields = [
            'id',
            'season',
            'season_name',
            'played',
            'wins',
            'draws',
            'losses',
            'goals_for',
            'goals_against',
            'goal_diff',
            'points',
            'ppg',
            'xg_for',
            'xg_against',
            'form_string',
            'position',
        ]
        read_only_fields = ['id']

    def get_ppg(self, obj) -> float:
        if obj.matches_played > 0:
            return round(obj.points / obj.matches_played, 2)
        return 0.0

    def get_goal_diff(self, obj) -> int:
        return obj.goals_for - obj.goals_against


class TeamDetailSerializer(serializers.ModelSerializer):
    """Detailed team serializer with statistics."""

    league = LeagueSerializer(read_only=True)
    current_season_stats = serializers.SerializerMethodField()
    recent_form = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id',
            'name',
            'short_name',
            'league',
            'logo_url',
            'founded',
            'stadium',
            'current_season_stats',
            'recent_form',
        ]
        read_only_fields = ['id']

    def get_current_season_stats(self, obj):
        # Get current season code from the team's league
        current_season_code = obj.league.current_season
        current_stats = TeamSeasonStats.objects.filter(
            team=obj,
            season__code=current_season_code
        ).first()

        if current_stats:
            return TeamSeasonStatsSerializer(current_stats).data
        return None

    def get_recent_form(self, obj) -> str:
        # Get current season code from the team's league
        current_season_code = obj.league.current_season
        current_stats = TeamSeasonStats.objects.filter(
            team=obj,
            season__code=current_season_code
        ).first()

        if current_stats and current_stats.form:
            return current_stats.form[:5]
        return ''


class HeadToHeadSerializer(serializers.ModelSerializer):
    """Serializer for head-to-head records."""

    team1_name = serializers.CharField(source='team1.name', read_only=True)
    team2_name = serializers.CharField(source='team2.name', read_only=True)

    class Meta:
        model = HeadToHead
        fields = [
            'id',
            'team1',
            'team1_name',
            'team2',
            'team2_name',
            'team1_wins',
            'team2_wins',
            'draws',
            'team1_goals',
            'team2_goals',
            'last_meeting',
            'total_matches',
        ]
        read_only_fields = ['id']
