"""
Flash feed builders (Phase 6). Each one is idempotent (FlashItem.dedupe_key)
and is called from the existing daily jobs, so no new schedules are needed:

- record_odds_moves()   after The Odds API sync (sync_odds)
- record_model_changes() after upcoming predictions are regenerated
- scrape_team_news()    in the daily fixtures sync
- results_flash()       after predictions are validated
- the acca flashes live in acca.py

Rules: only state what the data or the source says; news links to its
source; results show losses as clearly as wins.
"""
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone as dt_tz
from decimal import Decimal
from statistics import mean

from django.db import IntegrityError, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

ODDS_MOVE_PTS = 0.04       # implied-probability change that counts as a move
MODEL_CHANGE_PTS = 0.06    # model probability change worth a flash
SNAPSHOT_MIN_AGE = timedelta(hours=6)


def _add(**fields):
    """Create a FlashItem unless its dedupe_key already exists."""
    from .models import FlashItem
    try:
        with transaction.atomic():
            FlashItem.objects.create(**fields)
        return 1
    except IntegrityError:
        return 0


def _pct(p):
    return f'{float(p) * 100:.0f}%'


# ─── Odds moves ──────────────────────────────────────────────────────────────

def record_odds_moves(now=None):
    """Snapshot average bookmaker odds per upcoming match; flash big moves."""
    from apps.matches.models import Match
    from .models import OddsSnapshot

    now = now or timezone.now()
    created = 0
    matches = (Match.objects.filter(status=Match.Status.SCHEDULED, match_date__gte=now.date(),
                                    match_date__lte=(now + timedelta(days=7)).date())
               .select_related('home_team', 'away_team').prefetch_related('bookmaker_prices'))
    for m in matches:
        books = [b for b in m.bookmaker_prices.all() if not b.is_exchange]
        if len(books) < 3:
            continue
        cur = {s: Decimal(mean(float(getattr(b, f'{s}_odds')) for b in books)).quantize(Decimal('0.001'))
               for s in ('home', 'draw', 'away')}
        prev = (OddsSnapshot.objects.filter(match=m, taken_at__lte=now - SNAPSHOT_MIN_AGE)
                .order_by('-taken_at').first())
        last = OddsSnapshot.objects.filter(match=m).order_by('-taken_at').first()
        if prev:
            names = {'home': m.home_team.name, 'draw': 'The draw', 'away': m.away_team.name}
            for side in ('home', 'draw', 'away'):
                was, now_odds = float(getattr(prev, f'{side}_odds')), float(cur[side])
                d = 1 / now_odds - 1 / was
                if abs(d) < ODDS_MOVE_PTS:
                    continue
                verb = 'shortened' if d > 0 else 'drifted'
                created += _add(
                    kind='odds_move', match=m, importance=3 if abs(d) >= 0.08 else 2,
                    title=f'{names[side]} {verb}: {was:.2f} → {now_odds:.2f}',
                    body=(f'{m.home_team.name} v {m.away_team.name}. Bookmakers now give {names[side].lower() if side == "draw" else names[side]} '
                          f'{_pct(1 / now_odds)} (was {_pct(1 / was)}), average of {len(books)} bookmakers since '
                          f'{prev.taken_at:%a %H:%M} UTC. Big moves often follow team news.'),
                    source='The Odds API',
                    dedupe_key=f'odds:{m.id}:{side}:{now:%Y-%m-%d}',
                )
        # One snapshot per sync (skip if the last one is very recent).
        if not last or now - last.taken_at >= timedelta(hours=2):
            OddsSnapshot.objects.create(match=m, home_odds=cur['home'], draw_odds=cur['draw'],
                                        away_odds=cur['away'], bookmakers=len(books), taken_at=now)
    return created


# ─── Model changes ───────────────────────────────────────────────────────────

def record_model_changes(changes, now=None):
    """
    changes: [(match, old {'H','D','A'} probs, new probs, old pick, new pick)]
    collected by predict_upcoming just before it overwrites a prediction.
    """
    now = now or timezone.now()
    created = 0
    label = lambda m, k: {'H': m.home_team.name, 'D': 'the draw', 'A': m.away_team.name}[k]
    for m, old, new, old_pick, new_pick in changes:
        deltas = {k: new[k] - old[k] for k in 'HDA'}
        k = max(deltas, key=lambda x: abs(deltas[x]))
        if old_pick != new_pick:
            title = f'Model now picks {label(m, new_pick)} in {m.home_team.name} v {m.away_team.name}'
        elif abs(deltas[k]) >= MODEL_CHANGE_PTS:
            title = f'{label(m, k).capitalize() if k == "D" else label(m, k)} chance {"up" if deltas[k] > 0 else "down"} {abs(deltas[k]) * 100:.0f} pts'
        else:
            continue
        created += _add(
            kind='model_change', match=m, importance=3 if old_pick != new_pick else 2,
            title=title[:200],
            body=(f'{m.home_team.name} v {m.away_team.name}: home {_pct(old["H"])} → {_pct(new["H"])}, '
                  f'draw {_pct(old["D"])} → {_pct(new["D"])}, away {_pct(old["A"])} → {_pct(new["A"])}. '
                  'Usually because new results or odds came in.'),
            source='Bet Hope model',
            dedupe_key=f'model:{m.id}:{now:%Y-%m-%d}',
        )
    return created


# ─── Team news ───────────────────────────────────────────────────────────────

NEWS_FEEDS = [
    ('BBC Sport', 'https://feeds.bbci.co.uk/sport/football/rss.xml'),
    ('Sky Sports', 'https://www.skysports.com/rss/12040'),
    ('ESPN', 'https://www.espn.com/espn/rss/soccer/news'),
]
# Words too common to identify a club on their own ("United", "City", ...).
_GENERIC = {'united', 'city', 'town', 'athletic', 'rovers', 'wanderers', 'county', 'albion', 'real', 'sporting',
            'club', 'fc', 'olympique', 'racing', 'inter', 'atletico', 'dynamo', 'sport', 'hotspur', 'villa', 'palace',
            'forest', 'park', 'rangers', 'celtic', 'hearts', 'saints'}


def _team_patterns(teams):
    """Regex per team from its name and aliases; names must be distinctive."""
    pats = []
    for t in teams:
        names = {t.name, t.fd_name or ''} | {a.name for a in t.aliases.all()}
        good = sorted({n.strip() for n in names if n and len(n.strip()) >= 4 and n.strip().lower() not in _GENERIC},
                      key=len, reverse=True)
        if good:
            pats.append((t, re.compile(r'\b(' + '|'.join(re.escape(n) for n in good) + r')\b', re.I)))
    return pats


def _classify_with_ai(items):
    """One cheap batch call: tag + one-line summary per headline. Never invents facts."""
    key = os.getenv('OPENROUTER_API_KEY')
    if not key or not items:
        return {}
    try:
        import openai
        client = openai.OpenAI(api_key=key, base_url='https://openrouter.ai/api/v1')
        listing = '\n'.join(f'{i}. {it["title"]} — {it["summary"][:240]}' for i, it in enumerate(items))
        messages = [{'role': 'system', 'content': (
            'You tag football news for bettors. For each numbered item return JSON '
            '{"items":[{"i":0,"tag":"injury|suspension|manager|lineup|transfer|other","summary":"..."}]}. '
            'summary: max 18 words, ONLY facts stated in the headline/snippet, no speculation. Reply with JSON only.')},
            {'role': 'user', 'content': listing}]
        data = None
        for _ in range(2):  # reasoning models sometimes spend the budget thinking and return nothing
            # 12k tokens: deepseek-v4-pro reasons before answering; a small
            # budget ran out mid-reasoning and returned an empty reply.
            r = client.chat.completions.create(model='deepseek/deepseek-v4-pro', max_tokens=12000, temperature=0,
                                               response_format={'type': 'json_object'}, messages=messages)
            text = r.choices[0].message.content or ''
            if '{' in text:
                data = json.loads(text[text.find('{'): text.rfind('}') + 1])
                break
        if not data:
            return {}
        return {int(x['i']): x for x in data.get('items', []) if 'i' in x}
    except Exception as e:  # tagging is a nice-to-have; headlines still show
        logger.warning(f'News tagging failed: {e}')
        return {}


def scrape_team_news(now=None, max_age_hours=36):
    """Headlines mentioning a club with a fixture in the next 7 days."""
    import feedparser
    from apps.matches.models import Match
    from apps.teams.models import Team
    from .models import FlashItem

    now = now or timezone.now()
    upcoming = list(Match.objects.filter(status=Match.Status.SCHEDULED, match_date__gte=now.date(),
                                         match_date__lte=(now + timedelta(days=7)).date())
                    .select_related('home_team', 'away_team').order_by('match_date', 'kickoff_at'))
    next_match = {}
    for m in upcoming:
        next_match.setdefault(m.home_team_id, m)
        next_match.setdefault(m.away_team_id, m)
    pats = _team_patterns(Team.objects.filter(id__in=next_match).prefetch_related('aliases'))

    found, seen = [], set()
    for source, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            logger.warning(f'{source} feed failed: {e}')
            continue
        for e in feed.entries[:60]:
            link = e.get('link') or ''
            title = (e.get('title') or '').strip()
            if not link or not title or link in seen:
                continue
            published = e.get('published_parsed') or e.get('updated_parsed')
            when = (datetime(*published[:6], tzinfo=dt_tz.utc) if published else now)
            if now - when > timedelta(hours=max_age_hours):
                continue
            # The club must be in the headline itself: matching the description
            # too pulled in podcasts and round-ups that merely mention a club.
            teams = [t for t, p in pats if p.search(title)]
            if not teams:
                continue
            seen.add(link)
            found.append({'source': source, 'url': link[:500], 'title': title[:200], 'when': when,
                          'summary': '' if (e.get('summary') or '').strip().lower() in ('', 'null', 'none') else
                                     re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', e.get('summary'))).strip(),
                          'team': teams[0], 'match': next_match[teams[0].id]})

    tags = _classify_with_ai(found)
    created = 0
    for i, it in enumerate(found):
        t = tags.get(i, {})
        tag = t.get('tag') if t.get('tag') in {'injury', 'suspension', 'manager', 'lineup', 'transfer', 'other'} else ''
        m = it['match']
        fields = dict(
            tag=tag,
            importance=3 if tag in ('injury', 'suspension', 'lineup') else 1 if tag in ('transfer', 'other') else 2,
            body=' · '.join(x for x in ((t.get('summary') or it['summary'][:240]), f'Next: {m.home_team.name} v {m.away_team.name}') if x),
        )
        key = f'news:{it["url"]}'[:160]
        made = _add(kind='news', match=m, team=it['team'], source=it['source'], url=it['url'],
                    title=it['title'], published_at=it['when'], dedupe_key=key, **fields)
        if not made and tag:
            # Seen before without a tag (tagging failed that run): fill it in now.
            FlashItem.objects.filter(dedupe_key=key, tag='').update(**fields)
        created += made
    return {'matched': len(found), 'created': created}


# ─── Results ─────────────────────────────────────────────────────────────────

def yesterday_results(day=None):
    """How yesterday's top picks (any market, 65%+, made before kickoff) did. Used by the API and the flash."""
    from django.db.models import F, Q
    from apps.accounts.settle import leg_result
    from apps.predictions.picks import TOP_PICK_PROB, picks_for, top_pick_queryset

    day = day or (timezone.now() - timedelta(days=1)).date()
    preds = (top_pick_queryset(match_date=day, status='finished', home_score__isnull=False)
             .filter(Q(match__kickoff_at__isnull=False, created_at__lt=F('match__kickoff_at'))
                     | Q(match__kickoff_at__isnull=True, created_at__date__lt=F('match__match_date'))))
    rows = []
    for p, pick in picks_for(preds, min_prob=TOP_PICK_PROB):
        m = p.match
        result = leg_result(pick['key'], m.home_score, m.away_score, m.status)
        if result == 'void':
            continue
        rows.append({
            'match_id': p.match_id,
            'match': f'{m.home_team.name} v {m.away_team.name}',
            'pick': pick['label'], 'market': pick['group'], 'key': pick['key'],
            'confidence': pick['probability'],
            'score': f'{m.home_score}-{m.away_score}',
            'correct': result == 'won',
        })
    return {'date': day.isoformat(), 'total': len(rows), 'won': sum(r['correct'] for r in rows), 'picks': rows}


def results_flash(day=None):
    res = yesterday_results(day)
    if not res['total']:
        return 0
    lines = [f"{'✅' if r['correct'] else '❌'} {r['match']}: {r['pick']} ({r['score']})" for r in res['picks'][:12]]
    return _add(
        kind='results', importance=3,
        title=f"Yesterday: {res['won']} of {res['total']} top picks won",
        body='\n'.join(lines),
        source='Bet Hope record',
        dedupe_key=f"results:{res['date']}",
    )
