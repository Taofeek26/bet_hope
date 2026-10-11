"""
Team identity across data providers (Phase 2, DATA-01).

football-data.co.uk (CSV history) and football-data.org (fixtures, results,
crests) name the same club differently ("Man United" vs "Manchester United
FC", "FC Koln" vs "1. FC Köln"), and the old sync created a new Team row on
every mismatch, so upcoming fixtures pointed at teams with no history.

A club is identified per COUNTRY, not per league: the old per-league key
also split every promoted/relegated club into one row per division.

Lookup order used by resolve_team():
  1. TeamAlias for (country, normalized name): exact, includes every name
     already seen for that team.
  2. Team.name / Team.fd_name normalized, in the same country.
  3. Known hard cases from KNOWN_ALIASES (names that share no tokens).
  4. Token containment ("newcastle" in "newcastle united"), only if it
     picks exactly one team in the country.
Otherwise a new Team is created and its name recorded, and the miss is
logged so it shows up in the sync output for review.
"""
import logging
import re
import unicodedata
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# Tokens that carry no identity ("FC", "AFC", legal forms, founding years).
_NOISE = {
    'fc', 'afc', 'cf', 'sc', 'ac', 'as', 'ss', 'us', 'sv', 'fk', 'sk', 'nk',
    'cd', 'ud', 'sd', 'rc', 'rcd', 'ca', 'cp', 'sad', 'club', 'de', 'del',
    'la', 'le', 'the', 'calcio', 'football', 'futbol', 'foot', 'ssc', 'acf',
    'bk', 'if', 'ff', 'vfb', 'vfl', 'tsg', 'fsv', 'bsc', 'spvgg', 'e', 'v',
    'balompie', 'olympique', 'stade', 'racing', 'cfc', 'es',
}

# Short forms football-data.co.uk uses, expanded before comparing.
_EXPAND = {
    'man': 'manchester', 'utd': 'united', "nott'm": 'nottingham', 'nottm': 'nottingham',
    'ein': 'eintracht', "m'gladbach": 'monchengladbach', 'mgladbach': 'monchengladbach',
    'sp': 'sporting', 'ath': 'athletic', 'weds': 'wednesday', 'wolves': 'wolverhampton',
    'spurs': 'tottenham', 'qpr': 'queens park rangers', 'psg': 'paris saint germain',
    'st': 'saint', 'intl': 'international',
}

# Pairs that share no useful tokens. Key: country, value: {normalized name
# of either spelling: canonical normalized key}. Grown from the merge
# report (manage.py merge_duplicate_teams --report).
KNOWN_ALIASES = {
    'England': {
        'wolverhampton wanderers': 'wolverhampton',
        'brighton and hove albion': 'brighton',
        'west bromwich albion': 'west brom',
        'sheffield wednesday': 'sheffield wednesday',
        'queens park rangers': 'queens park rangers',
    },
    'Germany': {
        'bayern munchen': 'bayern munich',
        'borussia dortmund': 'dortmund',
        'borussia monchengladbach': 'monchengladbach',
        'bayer 04 leverkusen': 'leverkusen',
        'eintracht frankfurt': 'eintracht frankfurt',
        'hamburger': 'hamburg',
        'koln': 'koln',
        'werder bremen': 'werder bremen',
        'hoffenheim': 'hoffenheim',
        'mainz': 'mainz',
        'union berlin': 'union berlin',
        'elversberg': 'elversberg',
        'paderborn': 'paderborn',
        'st pauli': 'st pauli',
        'saint pauli': 'st pauli',
    },
    'Spain': {
        'atletico madrid': 'athletic madrid',
        'atletico de madrid': 'athletic madrid',
        'athletic club': 'athletic bilbao',
        'athletic bilbao': 'athletic bilbao',
        'real betis': 'betis',
        'real sociedad': 'sociedad',
        'celta vigo': 'celta',
        'celta': 'celta',
        'espanyol barcelona': 'espanol',
        'espanyol': 'espanol',
        'deportivo alaves': 'alaves',
        'rayo vallecano madrid': 'vallecano',
        'rayo vallecano': 'vallecano',
        'real oviedo': 'oviedo',
        'real mallorca': 'mallorca',
    },
    'Italy': {
        'internazionale milano': 'inter',
        'internazionale': 'inter',
        'milan': 'milan',
        'roma': 'roma',
        'lazio roma': 'lazio',
        'napoli': 'napoli',
        'hellas verona': 'verona',
        'pisa sporting': 'pisa',
    },
    'France': {
        'paris saint germain': 'paris saint germain',
        'paris sg': 'paris saint germain',
        'marseille': 'marseille',
        'lyonnais': 'lyon',
        'lyon': 'lyon',
        'saint etienne': 'st etienne',
        'brestois 29': 'brest',
        'stade brestois 29': 'brest',
        'rennais': 'rennes',
    },
    'Netherlands': {
        'psv': 'psv eindhoven',
        'psv eindhoven': 'psv eindhoven',
        'az': 'az alkmaar',
        'az alkmaar': 'az alkmaar',
        'feyenoord rotterdam': 'feyenoord',
        'sparta rotterdam': 'sparta rotterdam',
        'nec': 'nijmegen',
        'nec nijmegen': 'nijmegen',
        'twente enschede': 'twente',
        'go ahead eagles': 'go ahead eagles',
        'fortuna sittard': 'for sittard',
        'heracles almelo': 'heracles',
        'pec zwolle': 'zwolle',
        'excelsior': 'excelsior',
        'telstar 1963': 'telstar',
        'sc heerenveen': 'heerenveen',
        'utrecht': 'utrecht',
        'groningen': 'groningen',
        'volendam': 'volendam',
    },
    'Portugal': {
        'sporting clube de portugal': 'sporting lisbon',
        'sporting cp': 'sporting lisbon',
        'sporting': 'sporting lisbon',
        'benfica': 'benfica',
        'sport lisboa e benfica': 'benfica',
        'porto': 'porto',
        'sporting braga': 'braga',
        'braga': 'braga',
        'vitoria sc': 'guimaraes',
        'vitoria guimaraes': 'guimaraes',
        'gil vicente': 'gil vicente',
        'estoril praia': 'estoril',
        'famalicao': 'famalicao',
        'avs futebol sad': 'avs',
        'casa pia ac': 'casa pia',
    },
}


def normalize(name: Optional[str]) -> str:
    """Canonical comparison form: no accents, punctuation, noise or years."""
    if not name:
        return ''
    s = name.replace('ß', 'ss').replace('&', ' and ')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    tokens = []
    for raw in re.split(r"[\s\.\-/,()]+", s):
        if not raw:
            continue
        tok = _EXPAND.get(raw, raw)
        tok = tok.replace("'", '')
        for part in tok.split():
            if part in _NOISE or part.isdigit():
                continue
            tokens.append(part)
    return ' '.join(tokens)


_ALIAS_CACHE: dict = {}


def _aliases(country: str) -> dict:
    """KNOWN_ALIASES for a country with keys and values run through normalize()."""
    if country not in _ALIAS_CACHE:
        _ALIAS_CACHE[country] = {
            normalize(k): normalize(v) for k, v in KNOWN_ALIASES.get(country, {}).items()
        }
    return _ALIAS_CACHE[country]


def canonical_key(name: str, country: str) -> str:
    """normalize() plus the country's known alias, if any."""
    n = normalize(name)
    return _aliases(country).get(n, n)


def fix_mojibake(name: str) -> str:
    """Repair UTF-8 text that was decoded as Latin-1 once (e.g. 'MÃ¼nster')."""
    if not name or not re.search('[ÃÂ]', name):
        return name
    try:
        repaired = name.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name
    return repaired


class TeamResolver:
    """
    Find-or-create Teams for one sync run. Loads teams and aliases once
    (a sync touches hundreds of fixtures) and keeps them current as it
    creates rows. Use one instance per sync.
    """

    # Competitions whose teams come from many countries.
    MULTI_COUNTRY = {'Europe'}

    def __init__(self, source: str):
        from apps.teams.models import Team, TeamAlias

        self.source = source
        self.by_country = {}
        for t in Team.objects.select_related('league'):
            self.by_country.setdefault(t.league.country, []).append(t)
        self.aliases = {
            (a.country, a.key): a.team_id for a in TeamAlias.objects.all()
        }
        self.by_id = {t.pk: t for ts in self.by_country.values() for t in ts}
        # Exact spelling first: normalizing can make two different clubs
        # look alike ("Wimbledon" vs "AFC Wimbledon"), and each provider
        # spells a club the same way every time.
        self.exact = {}
        for t in self.by_id.values():
            for n in {t.name, t.fd_name} - {''}:
                k = (t.league.country, n.strip().lower())
                self.exact[k] = None if k in self.exact and self.exact[k] != t.pk else t.pk
        self.created = []

    def resolve(self, name: str, league, logo_url: str = ''):
        """Return the Team for `name` playing in `league`, creating it if unknown."""
        from apps.teams.models import Team
        from .merge import record_alias

        name = fix_mojibake(name)
        country = league.country
        countries = list(self.by_country) if country in self.MULTI_COUNTRY else [country]

        team = None
        for c in countries:
            team_id = self.exact.get((c, name.strip().lower()))
            if team_id:
                team = self.by_id[team_id]
                break
        for c in countries if team is None else []:
            team_id = self.aliases.get((c, canonical_key(name, c)))
            if team_id and team_id in self.by_id:
                team = self.by_id[team_id]
                break
        if team is None:
            found = [m for c in countries
                     if (m := best_match(name, c, self.by_country.get(c, [])))]
            if len(found) == 1:
                team = found[0]
        if team is None:
            team = Team.objects.create(name=name, fd_name=name, league=league, logo_url=logo_url or '')
            self.by_country.setdefault(country, []).append(team)
            self.by_id[team.pk] = team
            self.exact[(country, name.strip().lower())] = team.pk
            self.created.append(f'{name} ({league.code})')
            logger.warning('New team %r in %s: no existing club matched', name, league.code)

        if logo_url and not team.logo_url:
            team.logo_url = logo_url
            team.save(update_fields=['logo_url', 'updated_at'])
        alias = record_alias(team, name, self.source, team.league.country)
        if alias:
            self.aliases[(alias.country, alias.key)] = alias.team_id
        return team


def best_match(name: str, country: str, candidates: Iterable) -> Optional[object]:
    """
    Pick the Team among `candidates` (Team objects in the same country)
    that is the same club as `name`, or None. Exact canonical key first,
    then unique token containment.
    """
    key = canonical_key(name, country)
    if not key:
        return None
    candidates = list(candidates)
    exact = [t for t in candidates
             if key in {canonical_key(t.name, country), canonical_key(t.fd_name, country)}]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None  # ambiguous: leave for review

    key_tokens = set(key.split())
    contained = []
    for t in candidates:
        for other in {canonical_key(t.name, country), canonical_key(t.fd_name, country)} - {''}:
            ot = set(other.split())
            if ot and (ot <= key_tokens or key_tokens <= ot):
                contained.append(t)
                break
    if len(contained) == 1:
        return contained[0]
    return None
