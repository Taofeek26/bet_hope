"""
Leagues Models
"""
from django.db import models
from apps.core.models import SyncedModel


class League(SyncedModel):
    """
    Football league/competition.
    """

    class Tier(models.IntegerChoices):
        TIER_1 = 1, 'Tier 1 - Top 5 Leagues'
        TIER_2 = 2, 'Tier 2 - Other Major'
        TIER_3 = 3, 'Tier 3 - Second Divisions'
        TIER_4 = 4, 'Tier 4 - Other'

    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True, help_text="Football-Data.co.uk code (e.g., E0, SP1)")
    tier = models.IntegerField(choices=Tier.choices, default=Tier.TIER_2)
    logo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=100, help_text="Lower = higher priority")

    # Season configuration
    season_start_month = models.IntegerField(default=8, help_text="Month when season starts (1-12)")
    season_end_month = models.IntegerField(default=5, help_text="Month when season ends (1-12)")

    # Data availability
    has_xg_data = models.BooleanField(default=False, help_text="Whether xG data is available")
    has_player_data = models.BooleanField(default=False, help_text="Whether player-level data is available")

    class Meta:
        ordering = ['tier', 'priority', 'name']
        verbose_name = 'League'
        verbose_name_plural = 'Leagues'

    def __str__(self):
        return f"{self.name} ({self.country})"

    @property
    def current_season(self):
        """Get current season code (e.g., '2425')."""
        from datetime import date
        today = date.today()
        year = today.year
        month = today.month

        if month >= self.season_start_month:
            # We're in the first half of the season
            start_year = year
        else:
            # We're in the second half of the season
            start_year = year - 1

        return f"{str(start_year)[2:]}{str(start_year + 1)[2:]}"


class Season(SyncedModel):
    """
    A season for a league.
    """

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', 'Upcoming'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='seasons')
    code = models.CharField(max_length=10, help_text="Season code (e.g., '2324')")
    name = models.CharField(max_length=20, help_text="Display name (e.g., '2023-24')")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)

    # Stats
    total_matches = models.IntegerField(default=0)
    matches_played = models.IntegerField(default=0)
    total_goals = models.IntegerField(default=0)

    class Meta:
        ordering = ['-code']
        unique_together = ['league', 'code']
        verbose_name = 'Season'
        verbose_name_plural = 'Seasons'

    def __str__(self):
        return f"{self.league.name} {self.name}"

    @property
    def is_current(self):
        return self.code == self.league.current_season

    @property
    def progress_percentage(self):
        if self.total_matches == 0:
            return 0
        return round((self.matches_played / self.total_matches) * 100, 1)
