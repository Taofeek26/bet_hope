"""
Final scores from ESPN's public scoreboard (Phase 8): the second results
source.

Why: football-data.org's free tier covers 9 competitions, and the other
12 leagues (League One/Two, Scotland, Turkey, Greece, the second
divisions ...) only got results from football-data.co.uk's CSVs, which can
lag a week. On 19 Oct 2026 that left 92 played matches without a score, so
bets, accas and paper bets on them could not settle.

What it does: for each match that kicked off 2.5+ hours ago and is still
not finished, read ESPN's scoreboard for that league around that date and
take the score of the event whose home AND away teams are this match's
teams. It only updates existing Match rows (never creates teams or
matches); a match it can't pair is left for the CSV sync.

ESPN's site API is public and needs no key, but it is unofficial and can
change without notice; every failure is logged and skipped, never raised.
"""
import logging
import time
from difflib import SequenceMatcher
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Set

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

URL = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard'
SOURCE = 'espn'

# Bet Hope league code -> ESPN league slug (all checked 19 Oct 2026).
SLUGS = {
    'E0': 'eng.1', 'E1': 'eng.2', 'E2': 'eng.3', 'E3': 'eng.4',
    'SC0': 'sco.1', 'SC1': 'sco.2', 'SC2': 'sco.3',
    'D1': 'ger.1', 'D2': 'ger.2', 'I1': 'ita.1', 'I2': 'ita.2',
    'SP1': 'esp.1', 'SP2': 'esp.2', 'F1': 'fra.1', 'F2': 'fra.2',
    'N1': 'ned.1', 'B1': 'bel.1', 'P1': 'por.1', 'T1': 'tur.1', 'G1': 'gre.1',
    'CL': 'uefa.champions',
    # Phase 9: competitions whose fixtures come from ESPN (espn_leagues.py)
    'EL': 'uefa.europa', 'JPN': 'jpn.1', 'CHN': 'chn.1', 'AUS': 'aus.1',
}
FINAL = {'STATUS_FULL_TIME', 'STATUS_FINAL', 'STATUS_FINAL_AET', 'STATUS_FINAL_PEN', 'STATUS_FINAL_ET'}
POSTPONED = {'STATUS_POSTPONED'}
CANCELLED = {'STATUS_CANCELED', 'STATUS_CANCELLED', 'STATUS_ABANDONED'}


class _Scoreboards:
    """ESPN scoreboard per (slug, day), fetched once per run."""

    def __init__(self, pause: float = 0.25):
        self.cache: Dict[tuple, List[dict]] = {}
        self.pause = pause
        self.requests = 0
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'BetHope/1.0 (results check)'

    def events(self, slug: str, day: date) -> List[dict]:
        key = (slug, day)
        if key not in self.cache:
            self.cache[key] = []
            try:
                if self.requests:
                    time.sleep(self.pause)
                self.requests += 1
                r = self.session.get(URL.format(slug=slug), params={'dates': day.strftime('%Y%m%d')}, timeout=20)
                r.raise_for_status()
                self.cache[key] = r.json().get('events', [])
            except Exception as e:  # unofficial API: log and carry on
                logger.warning('ESPN %s %s failed: %s', slug, day, e)
        return self.cache[key]


def _team_keys(team, alias_keys: Dict[int, Set[str]]) -> Set[str]:
    from apps.teams.identity import canonical_key
    country = team.league.country
    keys = {canonical_key(team.name, country), canonical_key(team.fd_name, country)}
    return (keys | alias_keys.get(team.pk, set())) - {''}


def _espn_keys(competitor: dict, country: str) -> Set[str]:
    from apps.teams.identity import canonical_key
    t = competitor.get('team', {})
    names = {t.get('displayName'), t.get('shortDisplayName'), t.get('name'), t.get('location')}
    return {canonical_key(n, country) for n in names if n} - {''}


def same_club(espn: Set[str], ours: Set[str]) -> bool:
    """Exact canonical name, or one name's words all inside the other's ("cambridge" / "cambridge united")."""
    if espn & ours:
        return True
    for a in espn:
        ta = set(a.split())
        for b in ours:
            tb = set(b.split())
            if ta and tb and (ta <= tb or tb <= ta):
                return True
    return False


def _word_match(x: str, y: str) -> bool:
    """One word is the start of the other ("peterboro", "c" in "caledonian"), or a
    close spelling with the same first three letters ("olympiakos"/"olympiacos")."""
    if x.startswith(y) or y.startswith(x):
        return True
    return x[:3] == y[:3] and SequenceMatcher(None, x, y).ratio() >= 0.75


def similar(espn: Set[str], ours: Set[str]) -> bool:
    """
    Close spelling of the same club: every word of the shorter name matches a
    word of the longer one. "Bristol Rvs"/"Bristol Rovers" and "Goztep"/"Goztepe"
    pass; "Bristol City"/"Bristol Rovers" and "Burnley"/"Barnsley" don't.
    """
    for a in espn:
        for b in ours:
            short, long_ = sorted((a.split(), b.split()), key=len)
            if short and all(any(_word_match(x, y) for y in long_) for x in short):
                return True
    return False


def _find_event(match, events: Iterable[dict], alias_keys) -> Optional[dict]:
    """
    The one event that is this match. Exact names on both sides first; if
    none, one exact side plus a close spelling of the other. Ambiguity at
    either step means no answer.
    """
    home_keys = _team_keys(match.home_team, alias_keys)
    away_keys = _team_keys(match.away_team, alias_keys)
    strict, loose = [], []
    for ev in events:
        comps = (ev.get('competitions') or [{}])[0].get('competitors', [])
        side = {c.get('homeAway'): c for c in comps}
        if 'home' not in side or 'away' not in side:
            continue
        eh = _espn_keys(side['home'], match.home_team.league.country)
        ea = _espn_keys(side['away'], match.away_team.league.country)
        sh, sa = same_club(eh, home_keys), same_club(ea, away_keys)
        if sh and sa:
            strict.append((ev, side))
        elif (sh and similar(ea, away_keys)) or (sa and similar(eh, home_keys)):
            loose.append((ev, side))
    found = strict if strict else loose
    if len(found) != 1:
        return None  # nothing, or ambiguous: leave it for the CSV sync
    return {'event': found[0][0], 'home': found[0][1]['home'], 'away': found[0][1]['away']}


def stale_matches(days_back: int = 60, leagues: Optional[Iterable[str]] = None):
    """Matches that should be over (kickoff 2.5+ h ago) but have no final score."""
    from django.db.models import Q
    from apps.matches.models import Match
    now = timezone.now()
    qs = (Match.objects.filter(season__league__code__in=list(leagues or SLUGS),
                               match_date__gte=now.date() - timedelta(days=days_back),
                               status__in=[Match.Status.SCHEDULED, Match.Status.LIVE, Match.Status.HALFTIME])
          .filter(Q(kickoff_at__lte=now - timedelta(minutes=150))
                  | Q(kickoff_at__isnull=True, match_date__lt=now.date()))
          .select_related('season__league', 'home_team__league', 'away_team__league'))
    return list(qs)


def sync_stale_results(days_back: int = 60, stdout=None) -> dict:
    """Fill final scores for stale matches from ESPN. Returns counts."""
    from apps.matches.models import Match
    from apps.teams.merge import record_alias
    from apps.teams.models import TeamAlias

    say = (lambda s: stdout.write(s)) if stdout else (lambda s: None)
    matches = stale_matches(days_back)
    out = {'stale': len(matches), 'finished': 0, 'postponed': 0, 'cancelled': 0, 'unmatched': 0, 'requests': 0}
    if not matches:
        say('ESPN results: no stale matches')
        return out

    team_ids = {m.home_team_id for m in matches} | {m.away_team_id for m in matches}
    alias_keys: Dict[int, Set[str]] = {}
    for team_id, key in TeamAlias.objects.filter(team_id__in=team_ids).values_list('team_id', 'key'):
        alias_keys.setdefault(team_id, set()).add(key)

    boards = _Scoreboards()
    for m in matches:
        slug = SLUGS[m.season.league.code]
        day = m.kickoff_at.date() if m.kickoff_at else m.match_date
        # ESPN dates are US-based: a late kickoff in UTC can sit on the day before.
        events = [e for d in (day, day - timedelta(days=1), day + timedelta(days=1)) for e in boards.events(slug, d)]
        hit = _find_event(m, {e.get('id'): e for e in events}.values(), alias_keys)
        if not hit:
            out['unmatched'] += 1
            say(f'  ESPN: no pair for {m.home_team.name} v {m.away_team.name} ({m.season.league.code} {day})')
            continue
        state = hit['event'].get('status', {}).get('type', {}).get('name', '')
        if state in FINAL:
            try:
                h, a = int(hit['home']['score']), int(hit['away']['score'])
            except (KeyError, TypeError, ValueError):
                out['unmatched'] += 1
                continue
            m.home_score, m.away_score, m.status = h, a, Match.Status.FINISHED
            m.save(update_fields=['home_score', 'away_score', 'status', 'updated_at'])
            m.mark_synced(SOURCE)
            out['finished'] += 1
            say(f'  ESPN: {m.home_team.name} {h}-{a} {m.away_team.name} ({m.season.league.code})')
            # Remember ESPN's spellings, so later lookups are exact.
            for comp, team in ((hit['home'], m.home_team), (hit['away'], m.away_team)):
                if team.league.country != 'Europe':
                    record_alias(team, comp['team'].get('displayName', ''), SOURCE)
        elif state in POSTPONED:
            m.status = Match.Status.POSTPONED
            m.save(update_fields=['status', 'updated_at'])
            out['postponed'] += 1
        elif state in CANCELLED:
            m.status = Match.Status.CANCELLED
            m.save(update_fields=['status', 'updated_at'])
            out['cancelled'] += 1
    out['requests'] = boards.requests
    say(f"ESPN results: {out['finished']} finished, {out['postponed']} postponed, {out['cancelled']} cancelled, "
        f"{out['unmatched']} not paired, of {out['stale']} stale ({out['requests']} requests)")
    return out
