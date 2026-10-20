"""
Web push (Phase 6): alerts that arrive with the app closed, once it is
installed or the browser allows it. Two daily broadcasts, each sent once:

- morning digest (05:15 UTC run): acca of the day, number of top picks,
  and each subscriber's favourite teams playing today
- results (after validation): how yesterday's top picks did

Keys: VAPID_PRIVATE_KEY / VAPID_PUBLIC_KEY (Lambda env; the public one is
served to browsers by /engage/push_key/).
"""
import json
import logging
import os
from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone

logger = logging.getLogger(__name__)
SITE = 'https://bet-hope-frontend.vercel.app'


def _send(sub, payload):
    from pywebpush import webpush, WebPushException
    try:
        webpush(
            subscription_info={'endpoint': sub.endpoint, 'keys': {'p256dh': sub.p256dh, 'auth': sub.auth}},
            data=json.dumps(payload),
            vapid_private_key=os.environ['VAPID_PRIVATE_KEY'],
            vapid_claims={'sub': 'mailto:alerts@bet-hope.app'},
            ttl=12 * 3600,
        )
        sub.failures, sub.last_sent_at = 0, timezone.now()
        sub.save(update_fields=['failures', 'last_sent_at', 'updated_at'])
        return True
    except WebPushException as e:
        status = getattr(e.response, 'status_code', None)
        if status in (404, 410):          # the browser unsubscribed: forget it
            sub.delete()
        else:
            sub.failures += 1
            sub.save(update_fields=['failures', 'updated_at'])
            if sub.failures >= 5:
                sub.delete()
        return False


def _once(key):
    from django.db import transaction
    from .models import PushSent
    try:
        with transaction.atomic():
            return PushSent.objects.create(key=key)
    except IntegrityError:
        return None


def morning_digest(now=None):
    """Send today's digest once. Personalised with favourite teams playing today."""
    from apps.engage.models import DailyAcca, PushSubscription
    from apps.matches.models import Match

    if not os.getenv('VAPID_PRIVATE_KEY'):
        return 0
    now = now or timezone.now()
    today = now.date()
    subs = list(PushSubscription.objects.all())
    if not subs:
        return 0
    log = _once(f'digest:{today}')
    if not log:
        return 0

    from apps.predictions.picks import TOP_PICK_PROB, picks_for, top_pick_queryset
    top = len(picks_for(top_pick_queryset(match_date=today, status=Match.Status.SCHEDULED), min_prob=TOP_PICK_PROB))
    acca = DailyAcca.objects.filter(date=today).first()
    base = (f"Acca of the day: {len(acca.legs)} picks, all win {float(acca.combined_probability) * 100:.0f}%. "
            if acca else '') + (f'{top} top picks today.' if top else 'No top picks today.')
    todays = {}
    for m in (Match.objects.filter(match_date=today, status=Match.Status.SCHEDULED)
              .select_related('home_team', 'away_team').prefetch_related('predictions')):
        p = max(m.predictions.all(), key=lambda x: x.updated_at, default=None)
        for tid in (m.home_team_id, m.away_team_id):
            todays[tid] = (m, p)

    sent = 0
    for sub in subs:
        prefs = sub.prefs or {}
        fav = [todays[t] for t in (sub.teams or []) if t in todays and prefs.get('teams', True)]
        if fav:
            m, p = fav[0]
            ko = m.kickoff_at.strftime('%H:%M UTC') if m.kickoff_at else 'today'
            chance = (f" · model: home {float(p.home_win_probability) * 100:.0f}% / draw {float(p.draw_probability) * 100:.0f}% "
                      f"/ away {float(p.away_win_probability) * 100:.0f}%") if p else ''
            payload = {'title': f'{m.home_team.name} v {m.away_team.name} {ko}', 'body': f'{chance.strip(" ·")} · {base}'.strip(' ·'),
                       'url': f'{SITE}/matches/{m.id}', 'tag': f'digest-{today}'}
        elif prefs.get('digest', True):
            payload = {'title': 'Bet Hope today', 'body': base, 'url': f'{SITE}/', 'tag': f'digest-{today}'}
        else:
            continue
        sent += _send(sub, payload)
    log.sent = sent
    log.save(update_fields=['sent'])
    return sent


def results_push(now=None):
    """Yesterday's top-pick record, once, to everyone who wants results."""
    from apps.engage.flash import yesterday_results
    from apps.engage.models import PushSubscription

    if not os.getenv('VAPID_PRIVATE_KEY'):
        return 0
    res = yesterday_results()
    if not res['total']:
        return 0
    subs = [s for s in PushSubscription.objects.all() if (s.prefs or {}).get('results', True)]
    if not subs or not (log := _once(f"results:{res['date']}")):
        return 0
    payload = {'title': f"Yesterday: {res['won']} of {res['total']} top picks won",
               'body': ' · '.join(f"{'✅' if r['correct'] else '❌'} {r['match']}" for r in res['picks'][:4]),
               'url': f'{SITE}/', 'tag': f"results-{res['date']}"}
    sent = sum(_send(s, payload) for s in subs)
    log.sent = sent
    log.save(update_fields=['sent'])
    return sent
