"""
Score challenge (Phase 6): predict the exact score of the week's big matches.
3 points for the exact score, 1 for the right result. Weekly leaderboard
(Monday-Sunday UTC). The Bet Hope model plays too, with its predicted score.
For fun only: no stakes, no prizes.
"""
import hashlib
import re
import secrets
from datetime import datetime, time, timedelta, timezone as dt_tz

from django.utils import timezone

LEAGUES = ['E0', 'SP1', 'I1', 'D1', 'F1', 'CL']
NICK_RE = re.compile(r'^[A-Za-z0-9_ .-]{3,20}$')
BLOCKED = {'admin', 'bethope', 'bet hope', 'moderator', 'support'}


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_token():
    return secrets.token_urlsafe(32)


def week_bounds(when=None):
    when = when or timezone.now()
    start = datetime.combine((when - timedelta(days=when.weekday())).date(), time.min, tzinfo=dt_tz.utc)
    return start, start + timedelta(days=7)


def points(ph, pa, h, a):
    if h is None or a is None:
        return None
    if ph == h and pa == a:
        return 3
    res = lambda x, y: (x > y) - (x < y)
    return 1 if res(ph, pa) == res(h, a) else 0


def week_matches(start, end):
    from apps.matches.models import Match
    return (Match.objects.filter(season__league__code__in=LEAGUES, kickoff_at__gte=start, kickoff_at__lt=end)
            .exclude(status__in=[Match.Status.POSTPONED, Match.Status.CANCELLED])
            .select_related('home_team', 'away_team', 'season__league').order_by('kickoff_at'))


def leaderboard(start, end, limit=50):
    from apps.predictions.models import Prediction
    from .models import GamePick

    table = {}
    picks = (GamePick.objects.filter(match__kickoff_at__gte=start, match__kickoff_at__lt=end)
             .select_related('player', 'match'))
    for p in picks:
        row = table.setdefault(p.player.nickname, {'name': p.player.nickname, 'points': 0, 'exact': 0, 'results': 0, 'picks': 0, 'is_model': False})
        row['picks'] += 1
        pts = points(p.home, p.away, p.match.home_score, p.match.away_score) if p.match.status == 'finished' else None
        if pts is not None:
            row['points'] += pts
            row['exact'] += pts == 3
            row['results'] += pts >= 1
    # The model's own entry: its most likely score for each match.
    model = {'name': 'Bet Hope model 🤖', 'points': 0, 'exact': 0, 'results': 0, 'picks': 0, 'is_model': True}
    for pr in (Prediction.objects.filter(match__in=week_matches(start, end), model_version__startswith='v2_',
                                         predicted_home_score__isnull=False).select_related('match')):
        m = pr.match
        model['picks'] += 1
        pts = points(int(pr.predicted_home_score), int(pr.predicted_away_score), m.home_score, m.away_score) if m.status == 'finished' else None
        if pts is not None:
            model['points'] += pts
            model['exact'] += pts == 3
            model['results'] += pts >= 1
    rows = sorted(list(table.values()) + [model], key=lambda r: (-r['points'], -r['exact'], r['name']))
    for i, r in enumerate(rows, 1):
        r['rank'] = i
    return rows[:limit]
