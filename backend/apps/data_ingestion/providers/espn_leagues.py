"""
Competitions whose fixtures, results and history all come from ESPN
(Phase 9): the Europa League, and three leagues that kick off in the
Nigerian early morning (J1 League ~05:00-07:00 UTC, A-League ~04:00-09:00
UTC) or around midday (Chinese Super League ~11:00 UTC).

None of our other sources has them for free: football-data.org's free tier
has no Europa League or Asian leagues, and football-data.co.uk's Japan file
stopped in June 2025. ESPN returns a whole calendar year per league in one
request (?dates=YYYY&limit=1000), so a daily run costs 4-8 requests and the
history back-fill about 16.

Matches are keyed by ESPN's event id (fd_match_id = 'espn_<id>', like
'fdorg_' for football-data.org), so a rescheduled match moves to its new
date instead of leaving a stale copy behind. Teams go through the shared
TeamResolver: Europa League clubs from our 20 leagues keep their history.

Not included: the Korean K League. ESPN doesn't carry it and no free source
with results history was found (19 Oct 2026).
"""
import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .espn import CANCELLED, FINAL, POSTPONED, SOURCE, URL

logger = logging.getLogger(__name__)

# code -> ESPN slug, display name, country, tier, season start month
LEAGUES = {
    'EL': {'slug': 'uefa.europa', 'name': 'Europa League', 'country': 'Europe', 'tier': 1, 'start': 7},
    'JPN': {'slug': 'jpn.1', 'name': 'J1 League', 'country': 'Japan', 'tier': 2, 'start': 8},
    'CHN': {'slug': 'chn.1', 'name': 'Chinese Super League', 'country': 'China', 'tier': 2, 'start': 1},
    'AUS': {'slug': 'aus.1', 'name': 'A-League Men', 'country': 'Australia', 'tier': 2, 'start': 9},
}
HISTORY_FROM = 2023
LIVE = {'STATUS_IN_PROGRESS', 'STATUS_FIRST_HALF', 'STATUS_SECOND_HALF', 'STATUS_EXTRA_TIME'}
HALFTIME = {'STATUS_HALFTIME'}


def _year_events(session, slug, year):
    r = session.get(URL.format(slug=slug), params={'dates': str(year), 'limit': 1000}, timeout=40)
    r.raise_for_status()
    return r.json().get('events', [])


def _league(code):
    from apps.leagues.models import League
    info = LEAGUES[code]
    league, created = League.objects.get_or_create(code=code, defaults={
        'name': info['name'], 'country': info['country'], 'tier': info['tier'],
        'season_start_month': info['start'], 'season_end_month': (info['start'] - 2) % 12 + 1,
    })
    return league


def _status(name, Match):
    if name in FINAL:
        return Match.Status.FINISHED
    if name in POSTPONED:
        return Match.Status.POSTPONED
    if name in CANCELLED:
        return Match.Status.CANCELLED
    if name in LIVE:
        return Match.Status.LIVE
    if name in HALFTIME:
        return Match.Status.HALFTIME
    return Match.Status.SCHEDULED


def sync_league(code, years, session=None, stdout=None):
    """Create/update every ESPN event of `code` in `years`. Returns counts."""
    import requests
    from apps.core.seasons import season_code_for, season_name
    from apps.leagues.models import Season
    from apps.matches.models import Match
    from apps.teams.identity import TeamResolver

    say = (lambda m: stdout.write(m)) if stdout else (lambda m: None)
    session = session or requests.Session()
    league = _league(code)
    resolver = TeamResolver(source=SOURCE)
    seasons = {}
    out = {'created': 0, 'updated': 0, 'skipped': 0}
    for year in years:
        try:
            events = _year_events(session, LEAGUES[code]['slug'], year)
        except Exception as e:
            say(f'  {code} {year}: ESPN failed ({e})')
            continue
        for ev in events:
            try:
                comp = (ev.get('competitions') or [{}])[0]
                side = {c.get('homeAway'): c for c in comp.get('competitors', [])}
                if 'home' not in side or 'away' not in side or not ev.get('date'):
                    out['skipped'] += 1
                    continue
                ko = datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))
                d = ko.date()
                scode = season_code_for(d, league.season_start_month)
                if scode not in seasons:
                    seasons[scode], _ = Season.objects.get_or_create(
                        league=league, code=scode, defaults={'name': season_name(scode)})
                home = resolver.resolve(side['home']['team'].get('displayName', ''), league,
                                        side['home']['team'].get('logo', ''))
                away = resolver.resolve(side['away']['team'].get('displayName', ''), league,
                                        side['away']['team'].get('logo', ''))
                status = _status(ev.get('status', {}).get('type', {}).get('name', ''), Match)
                hs = as_ = None
                if status in (Match.Status.FINISHED, Match.Status.LIVE, Match.Status.HALFTIME):
                    hs, as_ = int(side['home'].get('score')), int(side['away'].get('score'))
                ext = f"espn_{ev['id']}"
                with transaction.atomic():
                    m = (Match.objects.filter(fd_match_id=ext).first()
                         or Match.objects.filter(season=seasons[scode], home_team=home, away_team=away,
                                                 match_date=d).first())
                    fields = {'season': seasons[scode], 'home_team': home, 'away_team': away,
                              'match_date': d, 'kickoff_time': ko.time(), 'kickoff_at': ko,
                              'status': status, 'home_score': hs, 'away_score': as_, 'fd_match_id': ext}
                    if m is None:
                        m = Match.objects.create(**fields)
                        out['created'] += 1
                    else:
                        if m.status == Match.Status.FINISHED and status != Match.Status.FINISHED:
                            continue  # never un-finish a match on a glitchy feed
                        for k, v in fields.items():
                            setattr(m, k, v)
                        m.save()
                        out['updated'] += 1
                    m.mark_synced(SOURCE)
            except Exception as e:
                out['skipped'] += 1
                logger.warning('ESPN %s event %s skipped: %s', code, ev.get('id'), e)
    if resolver.created:
        say(f"  {code}: {len(resolver.created)} new teams")
    say(f"  {code} ({', '.join(map(str, years))}): {out['created']} created, {out['updated']} updated, "
        f"{out['skipped']} skipped")
    return out


def sync_all(history=False, stdout=None):
    """
    Daily: this year (and next year from November, for seasons that cross
    it). history=True, or a league with nothing before this year yet (its
    first run): every year back to HISTORY_FROM, so the model has form and
    Elo for its teams.
    """
    import requests
    from datetime import date
    from apps.matches.models import Match
    now = timezone.now()
    session = requests.Session()
    session.headers['User-Agent'] = 'BetHope/1.0 (fixtures)'
    out = {}
    for code in LEAGUES:
        has_past = Match.objects.filter(season__league__code=code, match_date__lt=date(now.year, 1, 1)).exists()
        years = list(range(HISTORY_FROM, now.year + 1)) if history or not has_past else [now.year]
        if now.month >= 11:
            years.append(now.year + 1)
        out[code] = sync_league(code, years, session=session, stdout=stdout)
    return out
