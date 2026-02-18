"""
Players Models (Placeholder - can be expanded with FBref data)
"""
from django.db import models
from apps.core.models import SyncedModel


class Player(SyncedModel):
    """
    Football player.
    """

    class Position(models.TextChoices):
        GOALKEEPER = 'GK', 'Goalkeeper'
        DEFENDER = 'DEF', 'Defender'
        MIDFIELDER = 'MID', 'Midfielder'
        FORWARD = 'FWD', 'Forward'

    name = models.CharField(max_length=200)
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='players'
    )
    position = models.CharField(max_length=3, choices=Position.choices, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # External IDs
    fbref_id = models.CharField(max_length=50, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Player'
        verbose_name_plural = 'Players'

    def __str__(self):
        return self.name
