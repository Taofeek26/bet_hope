"""
Model v2: training, evaluation, promotion and storage (Phase 3).

Three parts, chosen by measured results on held-out seasons
(html/phase-3.html):
  result_odds    Home/draw/away when bookmaker odds exist. XGBoost learns a
                 CORRECTION to the market: market log-probabilities are the
                 base margin, so it only has to learn where form, Elo and
                 shots disagree with the odds. Beat the market slightly.
  result_noodds  Same target without market features, for fixtures with no
                 odds yet.
  goals_home / goals_away
                 Poisson regressors for each side's goals. Their scoreline
                 grid gives the predicted score, over 2.5 and BTTS, all
                 consistent with each other (v1 split one total 55/45).

Split by time, never shuffled: train < validation season < test window.
The validation season drives early stopping; every reported metric is on
the test window, which no part of the model was fitted on (fixes ML-03).
"""
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import poisson
from sklearn.metrics import log_loss

from .features import FEATURES, build_features, labels, load_matches

logger = logging.getLogger(__name__)

MARKET = ['mkt_home', 'mkt_draw', 'mkt_away']
ODDS_FEATURES = [f for f in FEATURES if f not in MARKET]
NOODDS_FEATURES = [f for f in FEATURES if not f.startswith('mkt_') and f != 'has_odds']
MAX_GOALS = 10
ENGINE = 'v2'


def _clf(depth, mcw, rounds):
    return xgb.XGBClassifier(
        objective='multi:softprob', num_class=3, eval_metric='mlogloss', max_depth=depth,
        learning_rate=0.02, n_estimators=rounds, subsample=0.8, colsample_bytree=0.8,
        min_child_weight=mcw, reg_lambda=5.0, early_stopping_rounds=150, random_state=42, n_jobs=-1)


def _poisson():
    return xgb.XGBRegressor(
        objective='count:poisson', max_depth=3, learning_rate=0.03, n_estimators=2000,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=30, reg_lambda=5.0,
        early_stopping_rounds=100, random_state=42, n_jobs=-1)


def market_margin(X: pd.DataFrame) -> np.ndarray:
    return np.log(np.clip(X[MARKET].values, 1e-6, 1))


def score_grid(lam_h: np.ndarray, lam_a: np.ndarray) -> np.ndarray:
    """P(home=i, away=j) for each row, independent Poisson, shape (n, G, G)."""
    g = np.arange(MAX_GOALS + 1)
    ph = poisson.pmf(g[None, :], lam_h[:, None])
    pa = poisson.pmf(g[None, :], lam_a[:, None])
    return ph[:, :, None] * pa[:, None, :]


def metrics(p: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    p = np.clip(p, 1e-6, 1)
    p = p / p.sum(1, keepdims=True)
    onehot = np.eye(3)[y]
    rps = np.mean(np.sum((np.cumsum(p, 1) - np.cumsum(onehot, 1))[:, :2] ** 2, 1) / 2)
    return {
        'n': int(len(y)),
        'accuracy': float(np.mean(p.argmax(1) == y)),
        'log_loss': float(log_loss(y, p, labels=[0, 1, 2])),
        'brier': float(np.mean(np.sum((p - onehot) ** 2, 1))),
        'rps': float(rps),
    }


def calibration_table(p: np.ndarray, y: np.ndarray):
    conf, hit = p.max(1), p.argmax(1) == y
    rows = []
    for lo, hi in [(0, .45), (.45, .55), (.55, .65), (.65, 1.01)]:
        sel = (conf >= lo) & (conf < hi)
        if sel.any():
            rows.append({'band': f'{lo:.2f}-{min(hi, 1):.2f}', 'n': int(sel.sum()),
                         'predicted': float(conf[sel].mean()), 'actual': float(hit[sel].mean())})
    return rows


class ModelV2:
    def __init__(self):
        self.result_odds = None
        self.result_noodds = None
        self.goals_home = None
        self.goals_away = None
        self.meta: Dict = {}

    # ------------------------------------------------------------ predict
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """Probabilities, expected goals and scoreline-derived markets for each row of X."""
        out = pd.DataFrame(index=X.index)
        probs = np.zeros((len(X), 3))
        has = (X['has_odds'] == 1).values
        if has.any():
            Xo = X.loc[has]
            probs[has] = self.result_odds.predict_proba(Xo[ODDS_FEATURES], base_margin=market_margin(Xo))
        if (~has).any():
            probs[~has] = self.result_noodds.predict_proba(X.loc[~has, NOODDS_FEATURES])
        out['p_home'], out['p_draw'], out['p_away'] = probs.T
        out['used_odds'] = has

        lam_h = np.clip(self.goals_home.predict(X[FEATURES]), 0.05, 6)
        lam_a = np.clip(self.goals_away.predict(X[FEATURES]), 0.05, 6)
        grid = score_grid(lam_h, lam_a)
        g = np.arange(MAX_GOALS + 1)
        total = g[:, None] + g[None, :]
        out['xg_home'], out['xg_away'] = lam_h, lam_a
        out['p_over25'] = (grid * (total > 2.5)).sum((1, 2))
        out['p_btts'] = grid[:, 1:, 1:].sum((1, 2))
        # Most likely scoreline CONSISTENT with the predicted result, so the
        # card never says "Away win, 1-1" (ML-08).
        pick = probs.argmax(1)
        masks = [g[:, None] > g[None, :], g[:, None] == g[None, :], g[:, None] < g[None, :]]
        hs, as_ = np.zeros(len(X), int), np.zeros(len(X), int)
        for i in range(len(X)):
            sub = np.where(masks[pick[i]], grid[i], -1)
            hs[i], as_[i] = np.unravel_index(sub.argmax(), sub.shape)
        out['score_home'], out['score_away'] = hs, as_
        return out

    # ------------------------------------------------------------ train
    @classmethod
    def train(cls, df: Optional[pd.DataFrame] = None, X: Optional[pd.DataFrame] = None,
              test_start: Optional[date] = None, valid_years: int = 1, train_years: int = 20):
        """
        Fit on everything before the validation window; report on the test
        window (default: the last full season plus the current one).
        """
        from apps.core.seasons import current_season_code

        if df is None:
            df = load_matches()
        if X is None:
            X = build_features(df)
        y, hg, ag = labels(df)
        fin = ((df.status == 'finished') & df.home_score.notna()).values
        d = df.match_date
        if test_start is None:
            # Start of the previous season: test = last full season + current
            cur = current_season_code()
            test_start = date(2000 + int(cur[:2]) - 1, 7, 1)
        test_start = pd.Timestamp(test_start)
        valid_start = test_start - pd.DateOffset(years=valid_years)
        train_start = valid_start - pd.DateOffset(years=train_years)
        tr = fin & (d >= train_start) & (d < valid_start)
        va = fin & (d >= valid_start) & (d < test_start)
        te = fin & (d >= test_start)
        odds = (X.has_odds == 1).values

        m = cls()
        # Result with odds: correction on top of the market
        m.result_odds = _clf(3, 50, 3000)
        m.result_odds.fit(X.loc[tr & odds, ODDS_FEATURES], y[tr & odds], base_margin=market_margin(X.loc[tr & odds]),
                          eval_set=[(X.loc[va & odds, ODDS_FEATURES], y[va & odds])],
                          base_margin_eval_set=[market_margin(X.loc[va & odds])], verbose=False)
        # Result without odds
        m.result_noodds = _clf(4, 20, 2000)
        m.result_noodds.fit(X.loc[tr, NOODDS_FEATURES], y[tr], eval_set=[(X.loc[va, NOODDS_FEATURES], y[va])], verbose=False)
        # Goals
        m.goals_home, m.goals_away = _poisson(), _poisson()
        m.goals_home.fit(X.loc[tr, FEATURES], hg[tr], eval_set=[(X.loc[va, FEATURES], hg[va])], verbose=False)
        m.goals_away.fit(X.loc[tr, FEATURES], ag[tr], eval_set=[(X.loc[va, FEATURES], ag[va])], verbose=False)

        # Evaluate on the untouched test window
        pred = m.predict(X.loc[te])
        p = pred[['p_home', 'p_draw', 'p_away']].values
        yt = y[te].values
        te_odds = odds[te]
        total = (hg[te] + ag[te]).values
        over_true = (total > 2.5).astype(int)
        mkt_o25 = X.loc[te, 'mkt_over25'].values
        m.meta = {
            'engine': ENGINE,
            'windows': {'train': [str(train_start.date()), str(valid_start.date())],
                        'validation': [str(valid_start.date()), str(test_start.date())],
                        'test_from': str(test_start.date())},
            'samples': {'train': int(tr.sum()), 'validation': int(va.sum()), 'test': int(te.sum())},
            'test': metrics(p, yt),
            'test_with_odds': metrics(p[te_odds], yt[te_odds]) if te_odds.any() else None,
            'test_without_odds': metrics(p[~te_odds], yt[~te_odds]) if (~te_odds).any() else None,
            'baselines': {
                'bookmaker': metrics(X.loc[te, MARKET].values[te_odds], yt[te_odds]) if te_odds.any() else None,
                'home_always_accuracy': float(np.mean(yt == 0)),
            },
            'calibration': calibration_table(p, yt),
            'over25': {
                'model_log_loss': float(log_loss(over_true, np.clip(pred['p_over25'].values, 1e-6, 1 - 1e-6), labels=[0, 1])),
                'model_accuracy': float(np.mean((pred['p_over25'].values > .5) == over_true)),
            },
            'best_iterations': {
                'result_odds': int(m.result_odds.best_iteration),
                'result_noodds': int(m.result_noodds.best_iteration),
                'goals_home': int(m.goals_home.best_iteration),
                'goals_away': int(m.goals_away.best_iteration),
            },
            'features': FEATURES,
        }
        has_mkt = ~np.isnan(mkt_o25)
        if has_mkt.any():
            mo = np.clip(mkt_o25[has_mkt] / (mkt_o25[has_mkt] + (1 - mkt_o25[has_mkt])), 1e-6, 1 - 1e-6)
            m.meta['over25']['bookmaker_accuracy'] = float(np.mean((mo > .5) == over_true[has_mkt]))
        m._test_index = X.index[te]
        return m

    # ------------------------------------------------------------ io
    FILES = ('result_odds', 'result_noodds', 'goals_home', 'goals_away')

    def save(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        for name in self.FILES:
            getattr(self, name).save_model(str(directory / f'{name}.json'))
        # Not metadata.json: S3ModelStorage.upload_artifacts overwrites that name.
        (directory / 'model_v2.json').write_text(json.dumps(self.meta, indent=2))

    @classmethod
    def load(cls, directory: Path) -> 'ModelV2':
        m = cls()
        m.result_odds, m.result_noodds = xgb.XGBClassifier(), xgb.XGBClassifier()
        m.goals_home, m.goals_away = xgb.XGBRegressor(), xgb.XGBRegressor()
        for name in cls.FILES:
            getattr(m, name).load_model(str(directory / f'{name}.json'))
        m.meta = json.loads((directory / 'model_v2.json').read_text())
        return m


def model_dir(version: str) -> Path:
    base = Path('/tmp') if os.getenv('AWS_LAMBDA_FUNCTION_NAME') else Path(__file__).resolve().parents[3]
    return base / 'models' / version


def load_version(version: str) -> ModelV2:
    """Load a saved v2 model, from local disk or S3."""
    d = model_dir(version)
    if not (d / 'model_v2.json').exists() and os.getenv('S3_MODEL_BUCKET'):
        from apps.ml_pipeline.storage import S3ModelStorage
        S3ModelStorage().download_artifacts(version, str(d))
    return ModelV2.load(d)
