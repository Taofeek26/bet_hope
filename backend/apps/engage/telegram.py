"""
Telegram channel posts (Phase 6). Switched off until TELEGRAM_BOT_TOKEN and
TELEGRAM_CHANNEL (e.g. "@bethope_tips") are set on the manage Lambda.

Three posts a day at most, each once (PushSent keys "tg:..."):
- the acca of the day, when it is built (04:15 UTC run)
- today's top picks (05:15 UTC run, after retraining)
- yesterday's results, wins and losses alike (after validation)
"""
import html
import logging
import os

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)
SITE = 'https://bet-hope-frontend.vercel.app'
FOOTER = '\n\n18+ · Bet responsibly · <a href="{site}">Bet Hope</a>'


def _enabled():
    return bool(os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHANNEL'))


def _post(key, text):
    from .push import _once
    if not _enabled() or not _once(f'tg:{key}'):
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
            json={'chat_id': os.environ['TELEGRAM_CHANNEL'], 'text': text + FOOTER.format(site=SITE),
                  'parse_mode': 'HTML', 'disable_web_page_preview': True},
            timeout=20,
        )
        if not r.ok:
            logger.warning(f'Telegram post {key} failed: {r.status_code} {r.text[:200]}')
        return r.ok
    except requests.RequestException as e:
        logger.warning(f'Telegram post {key} failed: {e}')
        return False


def post_acca(acca):
    if not acca:
        return False
    e = html.escape
    lines = [f"<b>🎯 Acca of the day · {acca.date:%a %d %b}</b>"]
    lines += [f"• {e(l['match'])}: <b>{e(l['label'])}</b> ({l['probability'] * 100:.0f}%)" for l in acca.legs]
    lines.append(f"\nAll win: <b>{float(acca.combined_probability) * 100:.0f}%</b> · fair odds {float(acca.combined_fair_odds):.2f}")
    return _post(f'acca:{acca.date}', '\n'.join(lines))


def post_top_picks(now=None):
    from apps.matches.models import Match
    from apps.predictions.picks import TOP_PICK_PROB, picks_for, top_pick_queryset
    now = now or timezone.now()
    picks = picks_for(top_pick_queryset(match_date=now.date(), status=Match.Status.SCHEDULED),
                      min_prob=TOP_PICK_PROB)[:10]
    if not picks:
        return False
    e = html.escape
    lines = [f"<b>⚽ Top picks today · {now:%a %d %b}</b>"]
    lines += [f"• {e(p.match.home_team.name)} v {e(p.match.away_team.name)}"
              f"{' ' + p.match.kickoff_at.strftime('%H:%M UTC') if p.match.kickoff_at else ''}: "
              f"<b>{e(pick['label'])}</b> {pick['probability'] * 100:.0f}%" for p, pick in picks]
    return _post(f'picks:{now.date()}', '\n'.join(lines))


def post_results():
    from .flash import yesterday_results
    res = yesterday_results()
    if not res['total']:
        return False
    e = html.escape
    lines = [f"<b>📊 Yesterday: {res['won']} of {res['total']} top picks won</b>"]
    lines += [f"{'✅' if r['correct'] else '❌'} {e(r['match'])}: {e(r['pick'])} ({r['score']})" for r in res['picks'][:12]]
    return _post(f"results:{res['date']}", '\n'.join(lines))
