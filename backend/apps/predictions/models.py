"""
Predictions Models
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel


class Prediction(TimeStampedModel):
    """
    ML model prediction for a match.
    """

    class Strength(models.TextChoices):
        STRONG = 'strong', 'Strong'
        MODERATE = 'moderate', 'Moderate'
        WEAK = 'weak', 'Weak'

    class Outcome(models.TextChoices):
        HOME = 'HOME', 'Home Win'
        DRAW = 'DRAW', 'Draw'
        AWAY = 'AWAY', 'Away Win'

    match = models.ForeignKey(
        'matches.Match',
        on_delete=models.CASCADE,
        related_name='predictions'
    )

    # Probabilities (must sum to ~1.0)
    home_win_probability = models.DecimalField(
        max_digits=6,
        decimal_places=5,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    draw_probability = models.DecimalField(
        max_digits=6,
        decimal_places=5,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    away_win_probability = models.DecimalField(
        max_digits=6,
        decimal_places=5,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )

    # Predicted score
    predicted_home_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )
    predicted_away_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Confidence & recommendation
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    prediction_strength = models.CharField(
        max_length=20,
        choices=Strength.choices,
        default=Strength.WEAK
    )
    recommended_outcome = models.CharField(
        max_length=10,
        choices=Outcome.choices
    )

    # Model info
    model_version = models.CharField(max_length=50)
    model_type = models.CharField(max_length=50, default='xgboost')

    # Feature snapshot (for debugging/analysis)
    features_json = models.JSONField(null=True, blank=True)

    # Explanation
    key_factors = models.JSONField(default=list, blank=True)

    # Validation (filled after match)
    is_correct = models.BooleanField(null=True, blank=True)
    actual_outcome = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Prediction'
        verbose_name_plural = 'Predictions'
        indexes = [
            models.Index(fields=['match', 'model_version']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_correct']),
        ]

    def __str__(self):
        return f"Prediction: {self.match} ({self.confidence_score:.0%})"

    def save(self, *args, **kwargs):
        # Set recommended outcome based on highest probability
        probs = {
            self.Outcome.HOME: float(self.home_win_probability),
            self.Outcome.DRAW: float(self.draw_probability),
            self.Outcome.AWAY: float(self.away_win_probability),
        }
        self.recommended_outcome = max(probs, key=probs.get)

        # Set prediction strength based on confidence
        if self.confidence_score >= 0.70:
            self.prediction_strength = self.Strength.STRONG
        elif self.confidence_score >= 0.55:
            self.prediction_strength = self.Strength.MODERATE
        else:
            self.prediction_strength = self.Strength.WEAK

        super().save(*args, **kwargs)

    def validate_prediction(self, actual_outcome: str):
        """
        Validate prediction against actual result.
        """
        self.actual_outcome = actual_outcome

        outcome_map = {'H': 'HOME', 'D': 'DRAW', 'A': 'AWAY'}
        actual_mapped = outcome_map.get(actual_outcome, actual_outcome)

        self.is_correct = (self.recommended_outcome == actual_mapped)
        self.save(update_fields=['is_correct', 'actual_outcome', 'updated_at'])

        return self.is_correct


class ModelVersion(TimeStampedModel):
    """
    Track ML model versions and their performance.
    """

    class Status(models.TextChoices):
        TRAINING = 'training', 'Training'
        EVALUATING = 'evaluating', 'Evaluating'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'

    version = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRAINING)

    # Training info
    trained_at = models.DateTimeField(null=True, blank=True)
    training_samples = models.IntegerField(default=0)
    training_seasons = models.JSONField(default=list)
    training_leagues = models.JSONField(default=list)

    # Model config
    model_type = models.CharField(max_length=50, default='xgboost')
    hyperparameters = models.JSONField(default=dict)
    feature_names = models.JSONField(default=list)
    feature_importance = models.JSONField(default=dict)

    # Evaluation metrics
    accuracy = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    log_loss = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    brier_score = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    # File paths
    model_path = models.CharField(max_length=500, blank=True)
    scaler_path = models.CharField(max_length=500, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Model Version'
        verbose_name_plural = 'Model Versions'

    def __str__(self):
        return f"Model {self.version} ({self.status})"

    @classmethod
    def get_active_version(cls):
        """Get the currently active model version."""
        return cls.objects.filter(status=cls.Status.ACTIVE).first()
