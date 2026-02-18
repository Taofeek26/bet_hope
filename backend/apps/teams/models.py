"""
Teams Models
"""
from django.db import models
from apps.core.models import SyncedModel


class Team(SyncedModel):
    """
    Football team/club.
    """
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True)
    code = models.CharField(max_length=10, blank=True, help_text="Short code (e.g., ARS, MUN)")
    league = models.ForeignKey(
        'leagues.League',
        on_delete=models.CASCADE,
        related_name='teams'
    )

    # Identifiers from different sources
    fd_name = models.CharField(max_length=200, blank=True, help_text="Name in Football-Data.co.uk")
    fbref_id = models.CharField(max_length=50, blank=True, help_text="FBref team ID")
    understat_id = models.CharField(max_length=50, blank=True, help_text="Understat team ID")

    # Club info
    logo_url = models.URLField(blank=True)
    founded = models.IntegerField(null=True, blank=True)
    stadium = models.CharField(max_length=200, blank=True)
    stadium_capacity = models.IntegerField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'

    def __str__(self):
        return self.name

    def get_current_stats(self):
        """Get current season statistics."""
        return self.season_stats.filter(
            season__code=self.league.current_season
        ).first()


class TeamSeasonStats(SyncedModel):
    """
    Team statistics for a specific season.
    """
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='season_stats')
    season = models.ForeignKey('leagues.Season', on_delete=models.CASCADE, related_name='team_stats')

    # Overall record
    matches_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    points = models.IntegerField(default=0)

    # Position
    league_position = models.IntegerField(null=True, blank=True)
    previous_position = models.IntegerField(null=True, blank=True)

    # Form (last 5 matches)
    form = models.CharField(max_length=10, blank=True, help_text="e.g., WWDLW")

    # Home record
    home_played = models.IntegerField(default=0)
    home_wins = models.IntegerField(default=0)
    home_draws = models.IntegerField(default=0)
    home_losses = models.IntegerField(default=0)
    home_goals_for = models.IntegerField(default=0)
    home_goals_against = models.IntegerField(default=0)

    # Away record
    away_played = models.IntegerField(default=0)
    away_wins = models.IntegerField(default=0)
    away_draws = models.IntegerField(default=0)
    away_losses = models.IntegerField(default=0)
    away_goals_for = models.IntegerField(default=0)
    away_goals_against = models.IntegerField(default=0)

    # Advanced stats (if available)
    xg_for = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    xg_against = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    clean_sheets = models.IntegerField(default=0)
    failed_to_score = models.IntegerField(default=0)

    class Meta:
        ordering = ['league_position']
        unique_together = ['team', 'season']
        verbose_name = 'Team Season Stats'
        verbose_name_plural = 'Team Season Stats'

    def __str__(self):
        return f"{self.team.name} - {self.season.name}"

    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against

    @property
    def points_per_game(self):
        if self.matches_played == 0:
            return 0
        return round(self.points / self.matches_played, 2)

    @property
    def goals_per_game(self):
        if self.matches_played == 0:
            return 0
        return round(self.goals_for / self.matches_played, 2)

    @property
    def conceded_per_game(self):
        if self.matches_played == 0:
            return 0
        return round(self.goals_against / self.matches_played, 2)


class HeadToHead(SyncedModel):
    """
    Head-to-head record between two teams.
    """
    team_a = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='h2h_as_team_a')
    team_b = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='h2h_as_team_b')

    # Overall record
    total_matches = models.IntegerField(default=0)
    team_a_wins = models.IntegerField(default=0)
    team_b_wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    team_a_goals = models.IntegerField(default=0)
    team_b_goals = models.IntegerField(default=0)

    # At team A's home
    matches_at_a = models.IntegerField(default=0)
    team_a_home_wins = models.IntegerField(default=0)
    team_b_away_wins = models.IntegerField(default=0)
    draws_at_a = models.IntegerField(default=0)

    # At team B's home
    matches_at_b = models.IntegerField(default=0)
    team_b_home_wins = models.IntegerField(default=0)
    team_a_away_wins = models.IntegerField(default=0)
    draws_at_b = models.IntegerField(default=0)

    last_match_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ['team_a', 'team_b']
        verbose_name = 'Head to Head'
        verbose_name_plural = 'Head to Head Records'

    def __str__(self):
        return f"{self.team_a.name} vs {self.team_b.name}"

    @classmethod
    def get_or_create_for_teams(cls, team1, team2):
        """
        Get or create H2H record, ensuring consistent ordering.
        """
        # Always store with lower ID first
        if team1.id > team2.id:
            team1, team2 = team2, team1

        h2h, created = cls.objects.get_or_create(
            team_a=team1,
            team_b=team2
        )
        return h2h, created
