"""
Analytics Models - Model performance tracking
"""
from django.db import models
from apps.core.models import TimeStampedModel


class ModelMetrics(TimeStampedModel):
    """
    Track model performance metrics over time.
    """
    model_version = models.ForeignKey(
        'predictions.ModelVersion',
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    league = models.ForeignKey(
        'leagues.League',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='model_metrics'
    )

    # Evaluation period
    period_start = models.DateField()
    period_end = models.DateField()

    # Sample size
    total_predictions = models.IntegerField(default=0)
    correct_predictions = models.IntegerField(default=0)

    # Accuracy metrics
    accuracy = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    # By outcome
    home_predictions = models.IntegerField(default=0)
    home_correct = models.IntegerField(default=0)
    draw_predictions = models.IntegerField(default=0)
    draw_correct = models.IntegerField(default=0)
    away_predictions = models.IntegerField(default=0)
    away_correct = models.IntegerField(default=0)

    # Probabilistic metrics
    log_loss = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    brier_score = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    # Confidence analysis
    high_confidence_predictions = models.IntegerField(default=0)
    high_confidence_correct = models.IntegerField(default=0)
    medium_confidence_predictions = models.IntegerField(default=0)
    medium_confidence_correct = models.IntegerField(default=0)
    low_confidence_predictions = models.IntegerField(default=0)
    low_confidence_correct = models.IntegerField(default=0)

    class Meta:
        ordering = ['-period_end']
        verbose_name = 'Model Metrics'
        verbose_name_plural = 'Model Metrics'

    def __str__(self):
        league_name = self.league.name if self.league else 'All Leagues'
        return f"{self.model_version.version} - {league_name} ({self.period_start} to {self.period_end})"

    @property
    def home_accuracy(self):
        if self.home_predictions == 0:
            return None
        return round(self.home_correct / self.home_predictions, 4)

    @property
    def draw_accuracy(self):
        if self.draw_predictions == 0:
            return None
        return round(self.draw_correct / self.draw_predictions, 4)

    @property
    def away_accuracy(self):
        if self.away_predictions == 0:
            return None
        return round(self.away_correct / self.away_predictions, 4)


class DailyStats(TimeStampedModel):
    """
    Daily aggregated statistics for dashboard.
    """
    date = models.DateField(unique=True)

    # Match stats
    matches_played = models.IntegerField(default=0)
    total_goals = models.IntegerField(default=0)
    home_wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    away_wins = models.IntegerField(default=0)

    # Prediction stats
    predictions_made = models.IntegerField(default=0)
    predictions_correct = models.IntegerField(default=0)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Daily Stats'
        verbose_name_plural = 'Daily Stats'

    def __str__(self):
        return f"Stats for {self.date}"

    @property
    def prediction_accuracy(self):
        if self.predictions_made == 0:
            return None
        return round(self.predictions_correct / self.predictions_made, 4)

    @property
    def avg_goals_per_match(self):
        if self.matches_played == 0:
            return 0
        return round(self.total_goals / self.matches_played, 2)
