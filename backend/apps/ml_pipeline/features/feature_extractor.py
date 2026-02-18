"""
Feature Extractor

Main orchestrator for feature extraction pipeline.
Handles caching, batching, and feature selection.
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import date
from pathlib import Path
import pickle
import hashlib

import numpy as np
import pandas as pd
from django.conf import settings

from .team_features import TeamFeatureBuilder
from .match_features import MatchFeatureBuilder

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Main feature extraction orchestrator.

    Provides a unified interface for:
    - Single match feature extraction
    - Batch feature extraction
    - Training dataset generation
    - Feature caching and persistence
    """

    # Feature groups for selection
    FEATURE_GROUPS = {
        'form': [
            'form_points', 'form_goals_scored', 'form_goals_conceded',
            'form_goal_diff', 'form_win_rate', 'form_weighted_points',
        ],
        'extended_form': [
            'extended_form_points', 'extended_form_goals_scored',
            'extended_form_goal_diff', 'extended_form_win_rate',
        ],
        'venue_form': [
            'venue_form_points', 'venue_form_goals_scored',
            'venue_form_goal_diff', 'venue_form_win_rate',
        ],
        'season': [
            'season_points', 'season_goals_per_game',
            'season_conceded_per_game', 'season_goal_diff',
            'season_win_rate', 'season_xg_diff',
        ],
        'xg': [
            'xg_for_avg', 'xg_against_avg', 'xg_diff', 'xg_overperformance',
        ],
        'patterns': [
            'btts_rate', 'over_25_rate', 'over_15_rate', 'first_half_goals_rate',
        ],
        'h2h': [
            'h2h_matches', 'h2h_home_wins', 'h2h_away_wins', 'h2h_draws',
            'h2h_home_goals_avg', 'h2h_away_goals_avg', 'h2h_total_goals_avg',
        ],
        'context': [
            'home_rest_days', 'away_rest_days', 'rest_diff',
            'is_weekend', 'is_early_season', 'is_late_season',
        ],
        'odds': [
            'implied_home_prob', 'implied_draw_prob', 'implied_away_prob',
            'odds_home', 'odds_draw', 'odds_away',
        ],
    }

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        use_cache: bool = True
    ):
        """
        Initialize the feature extractor.

        Args:
            cache_dir: Directory for feature cache files
            use_cache: Whether to use disk caching
        """
        self.cache_dir = cache_dir or Path(settings.BASE_DIR) / 'cache' / 'features'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache

        self.team_builder = TeamFeatureBuilder()
        self.match_builder = MatchFeatureBuilder(self.team_builder)

        # In-memory feature column order (for consistent ordering)
        self._feature_columns = None

    def extract_match_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: date,
        season_code: Optional[str] = None,
        include_odds: bool = True,
        feature_groups: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Extract features for a single match.

        Args:
            home_team_id: Home team database ID
            away_team_id: Away team database ID
            match_date: Date of match
            season_code: Optional season code
            include_odds: Whether to include odds features
            feature_groups: Optional list of feature groups to include

        Returns:
            Dict of feature name -> value
        """
        features = self.match_builder.build_features(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            match_date=match_date,
            season_code=season_code,
            include_odds=include_odds
        )

        if feature_groups:
            features = self._filter_features(features, feature_groups)

        return features

    def extract_batch_features(
        self,
        matches: List[Dict[str, Any]],
        feature_groups: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Extract features for multiple matches.

        Args:
            matches: List of dicts with 'home_team_id', 'away_team_id', 'match_date'
            feature_groups: Optional feature groups filter

        Returns:
            DataFrame with features for all matches
        """
        features_list = []

        for match in matches:
            features = self.extract_match_features(
                home_team_id=match['home_team_id'],
                away_team_id=match['away_team_id'],
                match_date=match['match_date'],
                season_code=match.get('season_code'),
                include_odds=match.get('include_odds', True),
                feature_groups=feature_groups
            )
            features['match_id'] = match.get('match_id')
            features_list.append(features)

        return pd.DataFrame(features_list)

    def build_training_data(
        self,
        season_codes: List[str],
        league_codes: Optional[List[str]] = None,
        feature_groups: Optional[List[str]] = None,
        use_disk_cache: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Build training dataset from historical matches.

        Args:
            season_codes: List of season codes
            league_codes: Optional league filter
            feature_groups: Optional feature groups filter
            use_disk_cache: Whether to use disk caching

        Returns:
            Tuple of (features_df, result_labels, goals_labels)
        """
        # Check cache first
        if use_disk_cache and self.use_cache:
            cache_key = self._get_cache_key(season_codes, league_codes, feature_groups)
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                logger.info(f"Loaded training data from cache: {cache_key}")
                return cached

        # Build from scratch
        logger.info("Building training dataset...")
        X, y_result, y_goals = self.match_builder.build_training_dataset(
            season_codes=season_codes,
            league_codes=league_codes
        )

        # Filter features if specified
        if feature_groups:
            X = self._filter_dataframe_features(X, feature_groups)

        # Store feature columns for inference
        self._feature_columns = list(X.columns)

        # Cache to disk
        if use_disk_cache and self.use_cache:
            self._save_to_cache(cache_key, (X, y_result, y_goals))

        return X, y_result, y_goals

    def _filter_features(
        self,
        features: Dict[str, float],
        groups: List[str]
    ) -> Dict[str, float]:
        """Filter features to only include specified groups."""
        allowed_suffixes = []
        for group in groups:
            allowed_suffixes.extend(self.FEATURE_GROUPS.get(group, []))

        filtered = {}
        for key, value in features.items():
            # Check if key ends with any allowed suffix
            for suffix in allowed_suffixes:
                if key.endswith(suffix):
                    filtered[key] = value
                    break

        return filtered

    def _filter_dataframe_features(
        self,
        df: pd.DataFrame,
        groups: List[str]
    ) -> pd.DataFrame:
        """Filter DataFrame columns to only include specified groups."""
        allowed_suffixes = []
        for group in groups:
            allowed_suffixes.extend(self.FEATURE_GROUPS.get(group, []))

        columns_to_keep = []
        for col in df.columns:
            for suffix in allowed_suffixes:
                if col.endswith(suffix):
                    columns_to_keep.append(col)
                    break

        return df[columns_to_keep]

    def _get_cache_key(
        self,
        season_codes: List[str],
        league_codes: Optional[List[str]],
        feature_groups: Optional[List[str]]
    ) -> str:
        """Generate cache key for training data."""
        data = {
            'seasons': sorted(season_codes),
            'leagues': sorted(league_codes) if league_codes else None,
            'groups': sorted(feature_groups) if feature_groups else None,
        }
        hash_str = hashlib.md5(str(data).encode()).hexdigest()[:16]
        return f"training_data_{hash_str}"

    def _load_from_cache(self, cache_key: str) -> Optional[Tuple]:
        """Load training data from disk cache."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Cache load failed: {e}")
        return None

    def _save_to_cache(self, cache_key: str, data: Tuple):
        """Save training data to disk cache."""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"Saved training data to cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def get_feature_columns(self) -> List[str]:
        """Get the ordered list of feature columns."""
        return self._feature_columns or []

    def get_feature_importance_df(
        self,
        importances: np.ndarray,
        feature_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Create DataFrame of feature importances.

        Args:
            importances: Array of importance values
            feature_names: Optional feature names (uses stored columns if None)

        Returns:
            DataFrame sorted by importance
        """
        names = feature_names or self._feature_columns
        if not names or len(names) != len(importances):
            raise ValueError("Feature names don't match importances")

        df = pd.DataFrame({
            'feature': names,
            'importance': importances
        })
        return df.sort_values('importance', ascending=False)

    def clear_cache(self):
        """Clear all caches."""
        self.team_builder.clear_cache()
        self.match_builder.clear_cache()
