"""
Predictions for upcoming fixtures with model v2 (Phase 3).

Features for fixtures come from the same chronological pass as training
(features.build_features), so a fixture sees exactly the state a training
row would have seen. Each Prediction records the model version and the
inputs it used (fixes ML-12), and is frozen once the match kicks off, so
accuracy only ever counts genuine pre-match predictions (ML-11).
"""
import logging
from datetime import timedelta
from decimal import Decimal

import numpy as np
from django.utils import timezone

from .features import build_features, load_matches
from .model import load_version

logger = logging.getLogger(__name__)

# Inputs stored with each prediction (for debugging, the AI prompt and audits)
SNAPSHOT = ['elo_home', 'elo_away', 'h_ppg5', 'a_ppg5', 'h_sot10', 'a_sot10',
            'h_season_ppg', 'a_season_ppg', 'mkt_home', 'mkt_draw', 'mkt_away', 'has_odds']


def _d(x, places=5):
    return Decimal(str(round(float(x), places)))


def predict_upcoming(version: str, days: int = 14) -> dict:
    from apps.matches.models import Match
    from apps.predictions.models import Prediction

    model = load_version(version)
    df = load_matches()
    X = build_features(df)

    today = timezone.now().date()
    upcoming = ((df.status == 'scheduled') & (df.match_date.dt.date >= today)
                & (df.match_date.dt.date <= today + timedelta(days=days)))
    if not upcoming.any():
        return {'predicted': 0, 'frozen': 0}
    rows = df.loc[upcoming]
    out = model.predict(X.loc[upcoming])

    now = timezone.now()
    kickoff = dict(Match.objects.filter(id__in=rows.id.tolist()).values_list('id', 'kickoff_at'))
    created = updated = frozen = 0
    for idx, r in rows.iterrows():
        ko = kickoff.get(r.id)
        if ko is not None and ko <= now:
            frozen += 1  # already kicked off: keep the pre-match prediction
            continue
        p = out.loc[idx]
        probs = [p.p_home, p.p_draw, p.p_away]
        snap = {k: (None if np.isnan(v) else round(float(v), 4)) for k, v in X.loc[idx, SNAPSHOT].items()}
        defaults = {
            'model_version': version,
            'model_type': 'v2',
            'home_win_probability': _d(p.p_home),
            'draw_probability': _d(p.p_draw),
            'away_win_probability': _d(p.p_away),
            'confidence_score': _d(max(probs), 4),
            'predicted_home_score': Decimal(int(p.score_home)),
            'predicted_away_score': Decimal(int(p.score_away)),
            'predicted_total_goals': _d(p.xg_home + p.xg_away, 2),
            'over_25_probability': _d(p.p_over25),
            'features_json': {**snap, 'xg_home': round(float(p.xg_home), 2),
                              'xg_away': round(float(p.xg_away), 2), 'used_odds': bool(p.used_odds)},
            # Same shape the AI prompt already reads (market / probability / confidence)
            'key_factors': [
                {'market': 'home_win', 'probability': round(float(p.p_home), 4), 'confidence': 'model'},
                {'market': 'draw', 'probability': round(float(p.p_draw), 4), 'confidence': 'model'},
                {'market': 'away_win', 'probability': round(float(p.p_away), 4), 'confidence': 'model'},
                {'market': 'over_2.5', 'probability': round(float(p.p_over25), 4), 'confidence': 'model'},
                {'market': 'both_teams_score', 'probability': round(float(p.p_btts), 4), 'confidence': 'model'},
            ],
        }
        existing = Prediction.objects.filter(match_id=r.id).order_by('-created_at').first()
        if existing:
            for k, v in defaults.items():
                setattr(existing, k, v)
            existing.save()  # save() sets recommended_outcome and strength
            updated += 1
        else:
            Prediction.objects.create(match_id=r.id, **defaults)
            created += 1
    return {'predicted': created + updated, 'created': created, 'updated': updated, 'frozen': frozen,
            'with_odds': int(out.used_odds.sum())}
