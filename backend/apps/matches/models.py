"""
Matches Models
"""
from django.db import models
from apps.core.models import SyncedModel


class Match(SyncedModel):
    """
    Football match/fixture.
    """

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        LIVE = 'live', 'Live'
        HALFTIME = 'halftime', 'Half Time'
        FINISHED = 'finished', 'Finished'
        POSTPONED = 'postponed', 'Postponed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Outcome(models.TextChoices):
        HOME = 'H', 'Home Win'
        DRAW = 'D', 'Draw'
        AWAY = 'A', 'Away Win'

    # Core fields
    season = models.ForeignKey('leagues.Season', on_delete=models.CASCADE, related_name='matches')
    home_team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='away_matches')

    # Timing
    match_date = models.DateField()
    kickoff_time = models.TimeField(null=True, blank=True)
    matchweek = models.IntegerField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)

    # Score
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    home_halftime_score = models.IntegerField(null=True, blank=True)
    away_halftime_score = models.IntegerField(null=True, blank=True)

    # Outcome (calculated)
    outcome = models.CharField(max_length=1, choices=Outcome.choices, blank=True)

    # External IDs
    fd_match_id = models.CharField(max_length=50, blank=True, help_text="Football-Data.co.uk match ID")
    fbref_match_id = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-match_date', '-kickoff_time']
        verbose_name = 'Match'
        verbose_name_plural = 'Matches'
        indexes = [
            models.Index(fields=['match_date']),
            models.Index(fields=['status']),
            models.Index(fields=['season', 'match_date']),
        ]
        # Prevent duplicate matches - same teams on same date in same season
        constraints = [
            models.UniqueConstraint(
                fields=['season', 'home_team', 'away_team', 'match_date'],
                name='unique_match_per_season'
            )
        ]

    def __str__(self):
        score = f"{self.home_score}-{self.away_score}" if self.home_score is not None else "vs"
        return f"{self.home_team.name} {score} {self.away_team.name}"

    def save(self, *args, **kwargs):
        # Calculate outcome
        if self.home_score is not None and self.away_score is not None:
            if self.home_score > self.away_score:
                self.outcome = self.Outcome.HOME
            elif self.home_score < self.away_score:
                self.outcome = self.Outcome.AWAY
            else:
                self.outcome = self.Outcome.DRAW
        super().save(*args, **kwargs)

    @property
    def league(self):
        return self.season.league

    @property
    def is_finished(self):
        return self.status == self.Status.FINISHED

    @property
    def total_goals(self):
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score + self.away_score


class MatchStatistics(SyncedModel):
    """
    Detailed match statistics.
    """
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='statistics')

    # Possession
    possession_home = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    possession_away = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Shots
    shots_home = models.IntegerField(null=True, blank=True)
    shots_away = models.IntegerField(null=True, blank=True)
    shots_on_target_home = models.IntegerField(null=True, blank=True)
    shots_on_target_away = models.IntegerField(null=True, blank=True)

    # Set pieces
    corners_home = models.IntegerField(null=True, blank=True)
    corners_away = models.IntegerField(null=True, blank=True)

    # Discipline
    fouls_home = models.IntegerField(null=True, blank=True)
    fouls_away = models.IntegerField(null=True, blank=True)
    yellow_cards_home = models.IntegerField(null=True, blank=True)
    yellow_cards_away = models.IntegerField(null=True, blank=True)
    red_cards_home = models.IntegerField(null=True, blank=True)
    red_cards_away = models.IntegerField(null=True, blank=True)

    # Advanced (xG from Understat/FBref)
    xg_home = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    xg_away = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Match Statistics'
        verbose_name_plural = 'Match Statistics'

    def __str__(self):
        return f"Stats: {self.match}"


class MatchOdds(SyncedModel):
    """
    Betting odds for a match (from Football-Data.co.uk).
    Used as baseline probabilities and for model validation.
    """
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='odds')

    # Average market odds
    home_odds = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    draw_odds = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    away_odds = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    # Over/Under 2.5 goals
    over_25_odds = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    under_25_odds = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    # Both teams to score
    btts_yes_odds = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    btts_no_odds = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    # Bookmaker source
    bookmaker = models.CharField(max_length=50, default='Average', help_text="Source of odds")

    class Meta:
        verbose_name = 'Match Odds'
        verbose_name_plural = 'Match Odds'

    def __str__(self):
        return f"Odds: {self.match}"

    @property
    def implied_home_prob(self):
        """Convert odds to implied probability."""
        if not self.home_odds:
            return None
        return round(1 / float(self.home_odds), 4)

    @property
    def implied_draw_prob(self):
        if not self.draw_odds:
            return None
        return round(1 / float(self.draw_odds), 4)

    @property
    def implied_away_prob(self):
        if not self.away_odds:
            return None
        return round(1 / float(self.away_odds), 4)

    @property
    def overround(self):
        """Calculate bookmaker margin (overround)."""
        if not all([self.home_odds, self.draw_odds, self.away_odds]):
            return None
        total = (1 / float(self.home_odds) +
                 1 / float(self.draw_odds) +
                 1 / float(self.away_odds))
        return round((total - 1) * 100, 2)
