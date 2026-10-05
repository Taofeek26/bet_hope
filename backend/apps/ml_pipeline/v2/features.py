"""
Point-in-time match features (Phase 3, fixes ML-01/02/07).

One chronological pass over every match. For each match the features are
computed from the state BEFORE it is played, then the state is updated
with its result. So a training row can never see its own result or any
later match (the v1 season-stat features did, ML-02), and upcoming
fixtures get exactly the same features as training rows did.

Unknown stays NaN (XGBoost learns where missing values should go) with
explicit has_* flags, instead of v1's 0.0, which looked like a real value
("0 points", "odds of 0").
"""
import math
from collections import defaultdict, deque
from typing import Dict, Tuple

import numpy as np
import pandas as pd

ELO_START = 1500.0
ELO_TIER_STEP = 75.0      # a club first seen in a lower division starts lower
ELO_K = 20.0
ELO_HOME = 60.0           # home advantage in Elo points
FORM_SHORT, FORM_LONG = 5, 10

FEATURES = [
    # strength
    'elo_home', 'elo_away', 'elo_diff', 'elo_expected_home',
    # short / long form (points per game, goals, shots, shots on target)
    'h_ppg5', 'a_ppg5', 'h_ppg10', 'a_ppg10',
    'h_gf10', 'h_ga10', 'a_gf10', 'a_ga10',
    'h_sh10', 'h_sha10', 'a_sh10', 'a_sha10',
    'h_sot10', 'h_sota10', 'a_sot10', 'a_sota10',
    'h_venue_ppg5', 'a_venue_ppg5',
    # season so far
    'h_season_ppg', 'a_season_ppg', 'h_season_gd', 'a_season_gd',
    'h_season_played', 'a_season_played',
    # context
    'h_rest', 'a_rest', 'rest_diff', 'league_home_rate', 'tier',
    # market
    'mkt_home', 'mkt_draw', 'mkt_away', 'mkt_overround', 'mkt_over25',
    'has_odds', 'h_history', 'a_history',
]


def load_matches() -> pd.DataFrame:
    """Every match with what the features need, oldest first."""
    from apps.matches.models import Match

    rows = Match.objects.values(
        'id', 'match_date', 'kickoff_time', 'status', 'home_team_id', 'away_team_id',
        'home_score', 'away_score', 'season__code', 'season__league__code',
        'season__league__tier', 'season__league__country',
        'odds__home_odds', 'odds__draw_odds', 'odds__away_odds', 'odds__over_25_odds',
        'statistics__shots_home', 'statistics__shots_away',
        'statistics__shots_on_target_home', 'statistics__shots_on_target_away',
    )
    df = pd.DataFrame.from_records(rows)
    df = df.rename(columns={
        'season__code': 'season', 'season__league__code': 'league',
        'season__league__tier': 'league_tier', 'season__league__country': 'country',
        'odds__home_odds': 'o_h', 'odds__draw_odds': 'o_d', 'odds__away_odds': 'o_a',
        'odds__over_25_odds': 'o_o25',
        'statistics__shots_home': 'sh_h', 'statistics__shots_away': 'sh_a',
        'statistics__shots_on_target_home': 'sot_h', 'statistics__shots_on_target_away': 'sot_a',
    })
    for c in ['o_h', 'o_d', 'o_a', 'o_o25', 'sh_h', 'sh_a', 'sot_h', 'sot_a', 'home_score', 'away_score']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['match_date'] = pd.to_datetime(df['match_date'])
    df['kick'] = df['kickoff_time'].astype(str).fillna('')
    return df.sort_values(['match_date', 'kick', 'id']).reset_index(drop=True)


def _mean(values) -> float:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return float(np.mean(vals)) if vals else np.nan


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Features for every row of `df` (from load_matches), in the same order.
    Finished matches update the running state; other rows (upcoming
    fixtures) only read it.
    """
    elo: Dict[int, float] = {}
    hist = defaultdict(lambda: deque(maxlen=FORM_LONG))           # (pts, gf, ga, sh, sha, sot, sota)
    venue = defaultdict(lambda: deque(maxlen=FORM_SHORT))         # (team, is_home) -> pts
    last_date: Dict[int, pd.Timestamp] = {}
    played: Dict[int, int] = defaultdict(int)
    season = defaultdict(lambda: [0, 0, 0])                       # (team, league, season) -> [n, pts, gd]
    league_results = defaultdict(lambda: deque(maxlen=600))       # league -> home win 1/0

    out = np.full((len(df), len(FEATURES)), np.nan)
    col = {f: i for i, f in enumerate(FEATURES)}

    for i, r in enumerate(df.itertuples(index=False)):
        h, a = r.home_team_id, r.away_team_id
        tier = r.league_tier or 2
        for t in (h, a):
            if t not in elo:
                elo[t] = ELO_START - ELO_TIER_STEP * (tier - 1)
        eh, ea = elo[h], elo[a]
        exp_home = 1.0 / (1.0 + 10 ** ((ea - eh - ELO_HOME) / 400.0))

        def form(t, n, idx):
            return _mean([m[idx] for m in list(hist[t])[-n:]])

        row = out[i]
        row[col['elo_home']], row[col['elo_away']] = eh, ea
        row[col['elo_diff']] = eh - ea + ELO_HOME
        row[col['elo_expected_home']] = exp_home
        for side, t in (('h', h), ('a', a)):
            if hist[t]:
                row[col[f'{side}_ppg5']] = form(t, FORM_SHORT, 0)
                row[col[f'{side}_ppg10']] = form(t, FORM_LONG, 0)
                row[col[f'{side}_gf10']] = form(t, FORM_LONG, 1)
                row[col[f'{side}_ga10']] = form(t, FORM_LONG, 2)
                row[col[f'{side}_sh10']] = form(t, FORM_LONG, 3)
                row[col[f'{side}_sha10']] = form(t, FORM_LONG, 4)
                row[col[f'{side}_sot10']] = form(t, FORM_LONG, 5)
                row[col[f'{side}_sota10']] = form(t, FORM_LONG, 6)
            v = venue[(t, side == 'h')]
            if v:
                row[col[f'{side}_venue_ppg5']] = float(np.mean(v))
            s = season[(t, r.league, r.season)]
            row[col[f'{side}_season_played']] = s[0]
            if s[0]:
                row[col[f'{side}_season_ppg']] = s[1] / s[0]
                row[col[f'{side}_season_gd']] = s[2] / s[0]
            if t in last_date:
                row[col[f'{side}_rest']] = min((r.match_date - last_date[t]).days, 30)
            row[col[f'{side}_history']] = min(played[t], 50)
        row[col['rest_diff']] = row[col['h_rest']] - row[col['a_rest']]
        lr = league_results[r.league]
        if len(lr) >= 50:
            row[col['league_home_rate']] = float(np.mean(lr))
        row[col['tier']] = tier

        # Market: normalized implied probabilities (overround removed)
        if r.o_h and r.o_d and r.o_a and r.o_h > 1 and r.o_d > 1 and r.o_a > 1:
            inv = np.array([1 / r.o_h, 1 / r.o_d, 1 / r.o_a])
            row[col['mkt_overround']] = inv.sum() - 1
            inv = inv / inv.sum()
            row[col['mkt_home']], row[col['mkt_draw']], row[col['mkt_away']] = inv
            row[col['has_odds']] = 1.0
        else:
            row[col['has_odds']] = 0.0
        if r.o_o25 and r.o_o25 > 1:
            row[col['mkt_over25']] = 1 / r.o_o25

        # ---- update state with the result (finished matches only) ----
        if r.status != 'finished' or pd.isna(r.home_score) or pd.isna(r.away_score):
            continue
        hs, as_ = int(r.home_score), int(r.away_score)
        ph, pa = (3, 0) if hs > as_ else (1, 1) if hs == as_ else (0, 3)
        hist[h].append((ph, hs, as_, r.sh_h, r.sh_a, r.sot_h, r.sot_a))
        hist[a].append((pa, as_, hs, r.sh_a, r.sh_h, r.sot_a, r.sot_h))
        venue[(h, True)].append(ph)
        venue[(a, False)].append(pa)
        for t, pts, gd in ((h, ph, hs - as_), (a, pa, as_ - hs)):
            s = season[(t, r.league, r.season)]
            s[0] += 1; s[1] += pts; s[2] += gd
            last_date[t] = r.match_date
            played[t] += 1
        league_results[r.league].append(1.0 if hs > as_ else 0.0)
        # Elo with a goal-margin multiplier
        score_home = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
        margin = math.log(abs(hs - as_) + 1) + 1
        delta = ELO_K * margin * (score_home - exp_home)
        elo[h] = eh + delta
        elo[a] = ea - delta

    feats = pd.DataFrame(out, columns=FEATURES, index=df.index)
    return feats


def labels(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """result (0 home, 1 draw, 2 away), home goals, away goals."""
    hs, as_ = df['home_score'], df['away_score']
    result = np.where(hs > as_, 0, np.where(hs == as_, 1, 2))
    return pd.Series(result, index=df.index), hs, as_
