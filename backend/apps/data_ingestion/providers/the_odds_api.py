"""
The Odds API (Phase 5, step 2b): current 1X2 prices from ~40 bookmakers for
19 of our 21 original competitions (not Scottish Championship / League One),
plus the Europa League, J1 League, Chinese Super League and A-League.

Why: football-data.co.uk's fixtures file only lists the next few days, so
most fixtures had no odds until shortly before kickoff, which blocked value
bets, paper bets and the model's market input. One call per league returns
every listed upcoming match, usually a week or more ahead.

Credits: 1 per league per call (region 'eu', market 'h2h'). Only leagues
with a fixture in the next REFRESH_DAYS are fetched, and fetching stops if
the monthly allowance runs low, so the free 500 credits cannot be overrun.
"""
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean

import requests
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

BASE = 'https://api.the-odds-api.com/v4'
REFRESH_DAYS = 3
MIN_REMAINING = 25
EXCHANGES = {'betfair_ex_uk', 'betfair_ex_eu', 'betfair_ex_au', 'smarkets', 'matchbook'}

SPORT_KEYS = {
    'E0': 'soccer_epl', 'E1': 'soccer_efl_champ', 'E2': 'soccer_england_league1',
    'E3': 'soccer_england_league2', 'SC0': 'soccer_spl',
    'D1': 'soccer_germany_bundesliga', 'D2': 'soccer_germany_bundesliga2',
    'I1': 'soccer_italy_serie_a', 'I2': 'soccer_italy_serie_b',
    'SP1': 'soccer_spain_la_liga', 'SP2': 'soccer_spain_segunda_division',
    'F1': 'soccer_france_ligue_one', 'F2': 'soccer_france_ligue_two',
    'N1': 'soccer_netherlands_eredivisie', 'B1': 'soccer_belgium_first_div',
    'P1': 'soccer_portugal_primeira_liga', 'T1': 'soccer_turkey_super_league',
    'G1': 'soccer_greece_super_league', 'CL': 'soccer_uefa_champs_league',
    # Phase 9: Europa League and the early-morning (WAT) Asian/Australian leagues
    'EL': 'soccer_uefa_europa_league', 'JPN': 'soccer_japan_j_league',
    'CHN': 'soccer_china_superleague', 'AUS': 'soccer_australia_aleague',
}
# Fetched last, and only while plenty of credits remain, so the original
# leagues never lose their odds to them on the free 500-credit plan.
LOW_PRIORITY = {'EL', 'JPN', 'CHN', 'AUS'}
LOW_PRIORITY_MIN = 120


def _names(team):
    """Every spelling we know for a team: name, football-data name, aliases."""
    names = {team.name, team.fd_name or ''}
    names |= {a.name for a in team.aliases.all()}
    return {n for n in names if n}


def _same_club(api_name, team):
    from apps.teams.identity import canonical_key
    country = team.league.country if team.league_id else ''
    key = canonical_key(api_name, country)
    if not key:
        return False
    keys = {canonical_key(n, country) for n in _names(team)} - {''}
    if key in keys:
        return True
    kt = set(key.split())
    return any(kt <= set(k.split()) or set(k.split()) <= kt for k in keys)


def _find_match(event, candidates):
    """The scheduled Match for an API event: same day (±1) and both clubs agree."""
    ko = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
    found = [
        m for m in candidates
        if abs((m.match_date - ko.date()).days) <= 1
        and _same_club(event['home_team'], m.home_team)
        and _same_club(event['away_team'], m.away_team)
    ]
    return found[0] if len(found) == 1 else None


def _prices(event):
    out = []
    for b in event.get('bookmakers', []):
        market = next((mk for mk in b.get('markets', []) if mk.get('key') == 'h2h'), None)
        if not market:
            continue
        by_name = {o['name']: o.get('price') for o in market.get('outcomes', [])}
        h, a, d = by_name.get(event['home_team']), by_name.get(event['away_team']), by_name.get('Draw')
        if not (h and d and a) or min(h, d, a) <= 1:
            continue
        out.append({
            'bookmaker': b['key'], 'title': b.get('title', b['key']),
            'home': Decimal(str(h)), 'draw': Decimal(str(d)), 'away': Decimal(str(a)),
            'link': (b.get('link') or '')[:500],
            'last_update': b.get('last_update'),
            'is_exchange': b['key'] in EXCHANGES,
        })
    return out


def sync_odds(api_key=None, leagues=None, stdout=None):
    """Fetch and store prices. Returns a summary dict."""
    from apps.matches.models import Match, MatchOdds, BookmakerPrice

    api_key = api_key or os.getenv('ODDS_API_KEY')
    say = (stdout.write if stdout else logger.info)
    if not api_key:
        say('ODDS_API_KEY not configured. Skipping The Odds API.')
        return {'skipped': 'no key'}

    today = timezone.now().date()
    soon = Match.objects.filter(
        status=Match.Status.SCHEDULED, match_date__gte=today,
        match_date__lte=today + timedelta(days=REFRESH_DAYS),
    )
    due = sorted(set(soon.values_list('season__league__code', flat=True)) & set(SPORT_KEYS),
                 key=lambda c: (c in LOW_PRIORITY, c))
    if leagues:
        due = [c for c in due if c in leagues]
    summary = {'leagues': 0, 'events': 0, 'matched': 0, 'unmatched': [], 'odds_filled': 0,
               'prices': 0, 'credits_remaining': None}

    for code in due:
        left = summary['credits_remaining']
        if code in LOW_PRIORITY and left is not None and left < LOW_PRIORITY_MIN:
            say(f'  {code}: skipped, {left} credits left (kept for the main leagues)')
            continue
        try:
            r = requests.get(
                f'{BASE}/sports/{SPORT_KEYS[code]}/odds',
                params={'apiKey': api_key, 'regions': 'eu', 'markets': 'h2h',
                        'oddsFormat': 'decimal', 'includeLinks': 'true'},
                timeout=30,
            )
        except requests.RequestException as e:
            say(f'  {code}: request failed ({e})')
            continue
        remaining = r.headers.get('x-requests-remaining')
        if remaining is not None:
            summary['credits_remaining'] = int(float(remaining))
        if r.status_code != 200:
            say(f'  {code}: HTTP {r.status_code} {r.text[:120]}')
            if r.status_code in (401, 429):
                break
            continue
        summary['leagues'] += 1
        candidates = list(
            Match.objects.filter(
                season__league__code=code, status=Match.Status.SCHEDULED,
                match_date__gte=today - timedelta(days=1),
            ).select_related('home_team__league', 'away_team__league')
            .prefetch_related('home_team__aliases', 'away_team__aliases')
        )
        for event in r.json():
            summary['events'] += 1
            match = _find_match(event, candidates)
            if not match:
                summary['unmatched'].append(f"{code}: {event['home_team']} v {event['away_team']}")
                continue
            prices = _prices(event)
            if not prices:
                continue
            summary['matched'] += 1
            with transaction.atomic():
                for p in prices:
                    BookmakerPrice.objects.update_or_create(
                        match=match, bookmaker=p['bookmaker'],
                        defaults={'title': p['title'], 'home_odds': p['home'], 'draw_odds': p['draw'],
                                  'away_odds': p['away'], 'link': p['link'], 'is_exchange': p['is_exchange'],
                                  'last_update': p['last_update']},
                    )
                    summary['prices'] += 1
                # Market average (bookmakers only, like football-data's "Avg"),
                # only where football-data.co.uk hasn't supplied odds yet.
                books = [p for p in prices if not p['is_exchange']]
                if len(books) >= 3:
                    existing = MatchOdds.objects.filter(match=match).first()
                    if existing is None or existing.bookmaker.startswith('OddsAPI'):
                        q = Decimal('0.001')
                        MatchOdds.objects.update_or_create(match=match, defaults={
                            'home_odds': Decimal(mean(p['home'] for p in books)).quantize(q),
                            'draw_odds': Decimal(mean(p['draw'] for p in books)).quantize(q),
                            'away_odds': Decimal(mean(p['away'] for p in books)).quantize(q),
                            'bookmaker': f'OddsAPI avg ({len(books)})',
                        })
                        summary['odds_filled'] += 1
        if summary['credits_remaining'] is not None and summary['credits_remaining'] < MIN_REMAINING:
            say(f'  Stopping: only {summary["credits_remaining"]} Odds API credits left this month')
            break

    try:
        from apps.engage.flash import record_odds_moves
        summary['odds_move_flashes'] = record_odds_moves()
    except Exception as e:
        logger.warning(f'odds-move flashes failed: {e}')
    say(f"The Odds API: {summary['leagues']} leagues, {summary['matched']}/{summary['events']} events matched, "
        f"{summary['prices']} bookmaker prices, odds filled for {summary['odds_filled']} fixtures, "
        f"credits left {summary['credits_remaining']}")
    if summary['unmatched']:
        say(f"  Unmatched ({len(summary['unmatched'])}): " + '; '.join(summary['unmatched'][:15]))
    return summary
