"""
Popular betting markets from one prediction (Phase 5, step 3 / bet slip).

- Result markets (1X2, double chance, draw no bet) come from the model's
  calibrated home/draw/away probabilities (sums of them), so they count as tested.
- Goal markets (GG/NG, over/under, team goals, correct score) come from the
  same Poisson score grid v2 uses for its tested over 2.5 figure, built from
  the expected goals stored with the prediction (features_json xg_home/away).
  Only over/under 2.5 was separately measured on unseen matches; the other
  goal markets are estimates from the same goals model.

Each entry carries the model probability and its fair odds (1 / probability),
plus the best price we hold for it, if any (1X2 from The Odds API; over/under
2.5 from football-data.co.uk's market average).
"""
import math

MAX_GOALS = 10


def _pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _grid(xh, xa):
    ph = [_pmf(i, xh) for i in range(MAX_GOALS + 1)]
    pa = [_pmf(j, xa) for j in range(MAX_GOALS + 1)]
    return [[ph[i] * pa[j] for j in range(MAX_GOALS + 1)] for i in range(MAX_GOALS + 1)]


def _row(group, key, label, prob, best=None, measured=False):
    prob = max(min(float(prob), 0.999), 0.001)
    return {
        'group': group, 'key': key, 'label': label,
        'probability': round(prob, 4), 'fair_odds': round(1 / prob, 2),
        'best_odds': round(float(best['odds']), 2) if best else None,
        'best_bookmaker': best.get('bookmaker') if best else None,
        'edge': round(prob - 1 / float(best['odds']), 4) if best else None,
        'tested': measured,
    }


def build_markets(prediction, home, away, best_1x2=None, avg_odds=None):
    """List of market rows for the bet slip. best_1x2: {'home': {'odds', 'bookmaker'}, ...}."""
    ph = float(prediction.home_win_probability)
    pd = float(prediction.draw_probability)
    pa = float(prediction.away_win_probability)
    best_1x2 = best_1x2 or {}
    rows = [
        _row('1X2', '1', f'{home} to win', ph, best_1x2.get('home'), True),
        _row('1X2', 'X', 'Draw', pd, best_1x2.get('draw'), True),
        _row('1X2', '2', f'{away} to win', pa, best_1x2.get('away'), True),
        _row('Double chance', '1X', f'{home} or draw', ph + pd, measured=True),
        _row('Double chance', '12', f'{home} or {away}', ph + pa, measured=True),
        _row('Double chance', 'X2', f'Draw or {away}', pd + pa, measured=True),
    ]
    if pd < 0.999:
        rows += [
            _row('Draw no bet', 'DNB1', f'{home} (draw = stake back)', ph / (1 - pd), measured=True),
            _row('Draw no bet', 'DNB2', f'{away} (draw = stake back)', pa / (1 - pd), measured=True),
        ]

    feats = prediction.features_json or {}
    xh, xa = feats.get('xg_home'), feats.get('xg_away')
    if xh is None or xa is None:
        if prediction.over_25_probability is not None:
            o = float(prediction.over_25_probability)
            rows += [_row('Over/Under', 'O2.5', 'Over 2.5 goals', o, _avg(avg_odds, 'over_25_odds'), True),
                     _row('Over/Under', 'U2.5', 'Under 2.5 goals', 1 - o, _avg(avg_odds, 'under_25_odds'), True)]
        return rows

    g = _grid(float(xh), float(xa))
    cells = [(i, j, g[i][j]) for i in range(MAX_GOALS + 1) for j in range(MAX_GOALS + 1)]
    total = sum(p for _, _, p in cells)  # ~1; renormalise the truncated tail
    P = lambda cond: sum(p for i, j, p in cells if cond(i, j)) / total

    gg = P(lambda i, j: i > 0 and j > 0)
    rows += [
        _row('GG/NG', 'GG', 'Both teams to score (GG)', gg),
        _row('GG/NG', 'NG', 'Not both teams to score (NG)', 1 - gg),
    ]
    for line in (1.5, 2.5, 3.5):
        o = P(lambda i, j, L=line: i + j > L)
        tested = line == 2.5
        rows += [
            _row('Over/Under', f'O{line}', f'Over {line} goals', o,
                 _avg(avg_odds, 'over_25_odds') if tested else None, tested),
            _row('Over/Under', f'U{line}', f'Under {line} goals', 1 - o,
                 _avg(avg_odds, 'under_25_odds') if tested else None, tested),
        ]
    for side, name, idx in (('H', home, 0), ('A', away, 1)):
        for line in (0.5, 1.5):
            o = P(lambda i, j, L=line, k=idx: (i if k == 0 else j) > L)
            rows.append(_row('Team goals', f'{side}O{line}', f'{name} over {line} goals', o))
    rows += [
        _row('Clean sheet', 'HCS', f'{home} clean sheet', P(lambda i, j: j == 0)),
        _row('Clean sheet', 'ACS', f'{away} clean sheet', P(lambda i, j: i == 0)),
    ]
    top = sorted(cells, key=lambda c: -c[2])[:6]
    rows += [_row('Correct score', f'CS{i}-{j}', f'Correct score {i}-{j}', p / total) for i, j, p in top]
    return rows


def _avg(avg_odds, field):
    v = getattr(avg_odds, field, None) if avg_odds else None
    return {'odds': v, 'bookmaker': 'Market average'} if v and float(v) > 1 else None
