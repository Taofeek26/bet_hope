"""
Engagement features (Phase 6): the flash feed, the daily acca and the odds
history behind "odds moved" flashes.
"""
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class FlashItem(TimeStampedModel):
    """One short, timestamped update shown in the flash feed."""

    class Kind(models.TextChoices):
        ODDS = 'odds_move', 'Odds move'
        NEWS = 'news', 'Team news'
        MODEL = 'model_change', 'Model change'
        RESULTS = 'results', 'Results'
        ACCA = 'acca', 'Acca of the day'

    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    url = models.URLField(max_length=500, blank=True)
    source = models.CharField(max_length=50, blank=True)
    tag = models.CharField(max_length=20, blank=True)  # news: injury / suspension / manager / ...
    match = models.ForeignKey('matches.Match', on_delete=models.CASCADE, null=True, blank=True, related_name='flash_items')
    team = models.ForeignKey('teams.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='flash_items')
    importance = models.PositiveSmallIntegerField(default=2)  # 1 low, 2 normal, 3 high
    dedupe_key = models.CharField(max_length=160, unique=True)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'engage_flash_item'
        ordering = ['-published_at', '-id']

    def __str__(self):
        return f'[{self.kind}] {self.title}'


class OddsSnapshot(models.Model):
    """Average bookmaker 1X2 odds for a match at one sync, to detect moves."""
    match = models.ForeignKey('matches.Match', on_delete=models.CASCADE, related_name='odds_snapshots')
    home_odds = models.DecimalField(max_digits=7, decimal_places=3)
    draw_odds = models.DecimalField(max_digits=7, decimal_places=3)
    away_odds = models.DecimalField(max_digits=7, decimal_places=3)
    bookmakers = models.PositiveSmallIntegerField(default=0)
    taken_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'engage_odds_snapshot'
        indexes = [models.Index(fields=['match', 'taken_at'])]


class DailyAcca(TimeStampedModel):
    """The acca of the day: built once from that morning's strongest picks, then tracked."""

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        WON = 'won', 'Won'
        LOST = 'lost', 'Lost'
        VOID = 'void', 'Void'

    date = models.DateField(unique=True)
    legs = models.JSONField(default=list)  # [{match_id, match, kickoff, league, key, label, probability, fair_odds, best_odds, result}]
    combined_probability = models.DecimalField(max_digits=6, decimal_places=4)
    combined_fair_odds = models.DecimalField(max_digits=9, decimal_places=2)
    combined_best_odds = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    model_version = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    legs_won = models.PositiveSmallIntegerField(default=0)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'engage_daily_acca'
        ordering = ['-date']


class PushSubscription(TimeStampedModel):
    """A browser/phone that asked for push alerts (Phase 6). No account needed."""
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    teams = models.JSONField(default=list, blank=True)   # favourite team ids
    prefs = models.JSONField(default=dict, blank=True)   # {"digest": true, "results": true, "teams": true}
    failures = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'engage_push_subscription'


class PushSent(models.Model):
    """One row per broadcast (e.g. the morning digest of a date), so it goes out once."""
    key = models.CharField(max_length=80, unique=True)
    sent = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engage_push_sent'


class MatchPreview(TimeStampedModel):
    """A short AI-written preview of a big match, generated once a day (Phase 6)."""
    match = models.OneToOneField('matches.Match', on_delete=models.CASCADE, related_name='ai_preview')
    text = models.TextField()
    model_name = models.CharField(max_length=80, blank=True)
    prediction_version = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'engage_match_preview'


class GamePlayer(TimeStampedModel):
    """Score challenge player (Phase 6): a nickname and a device token, no account, no prizes."""
    nickname = models.CharField(max_length=20, unique=True)
    token_hash = models.CharField(max_length=64, unique=True)  # sha256 of the device token

    class Meta:
        db_table = 'engage_game_player'


class GamePick(TimeStampedModel):
    """One score prediction; editable until kickoff."""
    player = models.ForeignKey(GamePlayer, on_delete=models.CASCADE, related_name='picks')
    match = models.ForeignKey('matches.Match', on_delete=models.CASCADE, related_name='game_picks')
    home = models.PositiveSmallIntegerField()
    away = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'engage_game_pick'
        constraints = [models.UniqueConstraint(fields=['player', 'match'], name='uniq_game_pick')]
