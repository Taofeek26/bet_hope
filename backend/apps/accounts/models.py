"""
User accounts (Phase 7): each user's own My bets, favourites and limits,
stored on the server so they follow the user across devices.
Login is Django's User (username = lower-cased email) with JWT.
"""
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=60, blank=True)
    favourite_teams = models.JSONField(default=list, blank=True)
    favourite_leagues = models.JSONField(default=list, blank=True)
    weekly_limit = models.PositiveIntegerField(null=True, blank=True)  # naira

    class Meta:
        db_table = 'accounts_profile'


class UserBet(TimeStampedModel):
    """A bet the user placed at their bookmaker (from the slip or the SportyBet extension)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bets')
    client_id = models.CharField(max_length=80)  # id made on the device (keeps syncs idempotent)
    placed_at = models.DateTimeField()
    bookmaker = models.CharField(max_length=30)
    stake = models.DecimalField(max_digits=12, decimal_places=2)
    odds = models.DecimalField(max_digits=10, decimal_places=2)
    selections = models.JSONField(default=list)
    source = models.CharField(max_length=20, default='manual')
    booking_code = models.CharField(max_length=40, blank=True)
    ticket_id = models.CharField(max_length=60, blank=True)
    leg_odds = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'accounts_bet'
        ordering = ['-placed_at']
        constraints = [models.UniqueConstraint(fields=['user', 'client_id'], name='uniq_user_bet')]
