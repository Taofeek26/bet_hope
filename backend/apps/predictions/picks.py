"""
One pick per match across markets, for top picks and the acca of the day
(Phase 8). Before this, both used only home/draw/away, so a match like
"Over 2.5 at 70%" or "Draw or Leipzig at 78%" never appeared.

The rule, chosen on the 266 live v2 matches settled by 19 Oct 2026:
  - Candidates are the popular markets Nigerian bookmakers all offer:
    1, 2, double chance, GG/NG, over/under 1.5/2.5/3.5.
  - Only chances between 60% and 85% count. Below 60% is too weak; above
    85% (team over 0.5, over 1.5 in a big game) pays 1.05-1.15, so it adds
    risk to a slip without adding return.
  - Of those, the pick is the market where the model's chance is furthest
    ABOVE that market's usual rate (BASE_RATE). Over 1.5 at 80% is ordinary
    (most matches are near 79%); GG at 66% is a strong signal (usual 55%).
    Picking the highest raw chance instead chose over 1.5 for half of all
    matches at fair odds 1.26.
  - A market whose best known bookmaker price is 5+ points below fair is
    skipped: the bookmakers disagree strongly and the bet loses money even
    if the model is right.
On those 266 matches this rule's picks won 74.1% (the model said 71.8%) at
an average fair price of 1.40, with every market type represented.
"""
from typing import Dict, Iterable, List, Optional

from .markets import build_markets

MIN_PROB, MAX_PROB = 0.60, 0.85
TOP_PICK_PROB = 0.65  # a top pick on the dashboard needs at least this
MAX_PRICE_GAP = 0.05

# Average model chance per market over live matches (Oct 2026): what
# "nothing special about this match" looks like for each market.
BASE_RATE = {
    '1': 0.436, '2': 0.325, '1X': 0.675, 'X2': 0.564, '12': 0.761,
    'GG': 0.554, 'NG': 0.446,
    'O1.5': 0.793, 'O2.5': 0.569, 'U2.5': 0.431, 'O3.5': 0.350, 'U3.5': 0.650,
}
# Families for the acca's "mix of markets" rule.
FAMILY = {
    '1': 'Result', '2': 'Result',
    '1X': 'Double chance', 'X2': 'Double chance', '12': 'Double chance',
    'GG': 'GG/NG', 'NG': 'GG/NG',
    'O1.5': 'Goals', 'O2.5': 'Goals', 'U2.5': 'Goals', 'O3.5': 'Goals', 'U3.5': 'Goals',
}


def best_1x2(match) -> Dict[str, dict]:
    """Best bookmaker 1X2 price per side (uses prefetched bookmaker_prices)."""
    books = [b for b in match.bookmaker_prices.all() if not b.is_exchange]
    out = {}
    for side in ('home', 'draw', 'away'):
        if books:
            top = max(books, key=lambda b: getattr(b, f'{side}_odds'))
            out[side] = {'odds': float(getattr(top, f'{side}_odds')), 'bookmaker': top.title}
    return out


def best_pick(prediction, match=None) -> Optional[dict]:
    """The match's pick as a market row (build_markets shape + family/lift), or None."""
    match = match or prediction.match
    rows = build_markets(prediction, match.home_team.name, match.away_team.name,
                         best_1x2=best_1x2(match), avg_odds=getattr(match, 'odds', None))
    best = None
    for r in rows:
        key, p = r['key'], r['probability']
        if key not in BASE_RATE or not (MIN_PROB <= p <= MAX_PROB):
            continue
        if r['edge'] is not None and r['edge'] < -MAX_PRICE_GAP:
            continue
        lift = p - BASE_RATE[key]
        if best is None or lift > best['lift']:
            best = {**r, 'family': FAMILY[key], 'lift': round(lift, 4)}
    return best


def picks_for(predictions: Iterable, min_prob: float = MIN_PROB) -> List[tuple]:
    """[(prediction, pick)] for each match's latest prediction with a pick, strongest first."""
    latest = {}
    for p in predictions:
        cur = latest.get(p.match_id)
        if cur is None or p.updated_at > cur.updated_at:
            latest[p.match_id] = p
    out = []
    for p in latest.values():
        pick = best_pick(p)
        if pick and pick['probability'] >= min_prob:
            out.append((p, pick))
    out.sort(key=lambda t: -t[1]['probability'])
    return out


def top_pick_queryset(**match_filters):
    """v2 predictions with what best_pick needs prefetched; filter on match__ fields."""
    from .models import Prediction
    return (Prediction.objects.filter(model_version__startswith='v2_',
                                      **{f'match__{k}': v for k, v in match_filters.items()})
            .select_related('match__home_team', 'match__away_team', 'match__season__league', 'match__odds')
            .prefetch_related('match__bookmaker_prices'))
