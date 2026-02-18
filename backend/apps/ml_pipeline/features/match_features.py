"""
Match Feature Engineering

Combines team features with head-to-head and contextual features
to create a complete feature vector for match prediction.
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from django.db.models import Q, Avg

logger = logging.getLogger(__name__)


class MatchFeatureBuilder:
    """
    Builds feature vectors for match predictions.

    Combines:
    - Home team features
    - Away team features
    - Head-to-head statistics
    - Contextual features (rest days, importance, etc.)
    """

    def __init__(self, team_feature_builder=None):
        """
        Initialize the match feature builder.

        Args:
            team_feature_builder: Optional TeamFeatureBuilder instance
        """
        from .team_features import TeamFeatureBuilder

        self.team_builder = team_feature_builder or TeamFeatureBuilder()
        self._cache = {}

    def build_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: date,
        season_code: Optional[str] = None,
        include_odds: bool = True
    ) -> Dict[str, float]:
        """
        Build complete feature vector for a match.

        Args:
            home_team_id: Home team database ID
            away_team_id: Away team database ID
            match_date: Date of the match
            season_code: Optional season filter
            include_odds: Whether to include betting odds features

        Returns:
            Dict of feature name -> value
        """
        cache_key = f"{home_team_id}_{away_team_id}_{match_date}_{season_code}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        features = {}

        # Home team features
        home_features = self.team_builder.build_features(
            team_id=home_team_id,
            as_of_date=match_date,
            is_home=True,
            season_code=season_code
        )
        for key, value in home_features.items():
            features[f'home_{key}'] = value

        # Away team features
        away_features = self.team_builder.build_features(
            team_id=away_team_id,
            as_of_date=match_date,
            is_home=False,
            season_code=season_code
        )
        for key, value in away_features.items():
            features[f'away_{key}'] = value

        # Differential features
        diff_features = self._calculate_differential_features(home_features, away_features)
        features.update(diff_features)

        # Head-to-head features
        h2h_features = self._calculate_h2h_features(
            home_team_id, away_team_id, match_date
        )
        features.update(h2h_features)

        # Contextual features
        context_features = self._calculate_context_features(
            home_team_id, away_team_id, match_date
        )
        features.update(context_features)

        # Odds-based features (if available)
        if include_odds:
            odds_features = self._get_odds_features(
                home_team_id, away_team_id, match_date
            )
            features.update(odds_features)

        self._cache[cache_key] = features
        return features

    def _calculate_differential_features(
        self,
        home_features: Dict[str, float],
        away_features: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate differential features between home and away teams.

        Returns:
            Dict of differential features
        """
        diff_keys = [
            'form_points', 'form_goals_scored', 'form_goals_conceded',
            'form_goal_diff', 'form_win_rate', 'season_points',
            'xg_for_avg', 'xg_against_avg', 'xg_diff'
        ]

        diffs = {}
        for key in diff_keys:
            home_val = home_features.get(key, 0.0)
            away_val = away_features.get(key, 0.0)
            diffs[f'diff_{key}'] = home_val - away_val

        return diffs

    def _calculate_h2h_features(
        self,
        home_team_id: int,
        away_team_id: int,
        as_of_date: date,
        limit: int = 10
    ) -> Dict[str, float]:
        """
        Calculate head-to-head features.

        Returns:
            Dict of H2H statistics
        """
        from apps.matches.models import Match

        # Get previous meetings
        h2h_matches = Match.objects.filter(
            Q(home_team_id=home_team_id, away_team_id=away_team_id) |
            Q(home_team_id=away_team_id, away_team_id=home_team_id),
            match_date__lt=as_of_date,
            status=Match.Status.FINISHED,
        ).order_by('-match_date')[:limit]

        if not h2h_matches.exists():
            return {
                'h2h_matches': 0,
                'h2h_home_wins': 0.0,
                'h2h_away_wins': 0.0,
                'h2h_draws': 0.0,
                'h2h_home_goals_avg': 0.0,
                'h2h_away_goals_avg': 0.0,
                'h2h_total_goals_avg': 0.0,
            }

        home_wins = 0
        away_wins = 0
        draws = 0
        home_goals = 0
        away_goals = 0

        for match in h2h_matches:
            # Normalize so home_team_id is always "home" in our calculation
            if match.home_team_id == home_team_id:
                hg = match.home_score or 0
                ag = match.away_score or 0
            else:
                hg = match.away_score or 0
                ag = match.home_score or 0

            home_goals += hg
            away_goals += ag

            if hg > ag:
                home_wins += 1
            elif hg < ag:
                away_wins += 1
            else:
                draws += 1

        n = h2h_matches.count()
        return {
            'h2h_matches': n,
            'h2h_home_wins': home_wins / n,
            'h2h_away_wins': away_wins / n,
            'h2h_draws': draws / n,
            'h2h_home_goals_avg': home_goals / n,
            'h2h_away_goals_avg': away_goals / n,
            'h2h_total_goals_avg': (home_goals + away_goals) / n,
        }

    def _calculate_context_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: date
    ) -> Dict[str, float]:
        """
        Calculate contextual features.

        Returns:
            Dict of context features
        """
        from apps.matches.models import Match

        features = {}

        # Rest days for home team
        home_last_match = Match.objects.filter(
            Q(home_team_id=home_team_id) | Q(away_team_id=home_team_id),
            match_date__lt=match_date,
            status=Match.Status.FINISHED,
        ).order_by('-match_date').first()

        if home_last_match:
            home_rest = (match_date - home_last_match.match_date).days
        else:
            home_rest = 7  # Default

        # Rest days for away team
        away_last_match = Match.objects.filter(
            Q(home_team_id=away_team_id) | Q(away_team_id=away_team_id),
            match_date__lt=match_date,
            status=Match.Status.FINISHED,
        ).order_by('-match_date').first()

        if away_last_match:
            away_rest = (match_date - away_last_match.match_date).days
        else:
            away_rest = 7  # Default

        features['home_rest_days'] = min(home_rest, 14)  # Cap at 14
        features['away_rest_days'] = min(away_rest, 14)
        features['rest_diff'] = home_rest - away_rest

        # Day of week (weekend games might be different)
        features['is_weekend'] = 1.0 if match_date.weekday() >= 5 else 0.0

        # Month (early/late season effects)
        month = match_date.month
        features['is_early_season'] = 1.0 if month in [8, 9] else 0.0
        features['is_late_season'] = 1.0 if month in [4, 5] else 0.0

        return features

    def _get_odds_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: date
    ) -> Dict[str, float]:
        """
        Get betting odds features (implied probabilities).

        Returns:
            Dict of odds-based features
        """
        from apps.matches.models import Match, MatchOdds

        try:
            match = Match.objects.get(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                match_date=match_date,
            )

            odds = MatchOdds.objects.filter(match=match).first()

            if odds:
                # Convert odds to implied probabilities
                home_prob = self._odds_to_probability(odds.home_odds)
                draw_prob = self._odds_to_probability(odds.draw_odds)
                away_prob = self._odds_to_probability(odds.away_odds)

                # Normalize to sum to 1
                total = home_prob + draw_prob + away_prob
                if total > 0:
                    home_prob /= total
                    draw_prob /= total
                    away_prob /= total

                return {
                    'implied_home_prob': home_prob,
                    'implied_draw_prob': draw_prob,
                    'implied_away_prob': away_prob,
                    'odds_home': float(odds.home_odds or 0),
                    'odds_draw': float(odds.draw_odds or 0),
                    'odds_away': float(odds.away_odds or 0),
                }

        except Match.DoesNotExist:
            pass

        return {
            'implied_home_prob': 0.0,
            'implied_draw_prob': 0.0,
            'implied_away_prob': 0.0,
            'odds_home': 0.0,
            'odds_draw': 0.0,
            'odds_away': 0.0,
        }

    def _odds_to_probability(self, odds) -> float:
        """Convert decimal odds to probability."""
        if odds is None or float(odds) <= 1:
            return 0.0
        return 1.0 / float(odds)

    def build_training_dataset(
        self,
        season_codes: List[str],
        league_codes: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Build training dataset from historical matches.

        Args:
            season_codes: List of season codes to include
            league_codes: Optional list of league codes

        Returns:
            Tuple of (features_df, target_result, target_goals)
        """
        from apps.matches.models import Match
        from apps.leagues.models import Season

        logger.info(f"Building training dataset for seasons: {season_codes}")

        matches_query = Match.objects.filter(
            season__code__in=season_codes,
            status=Match.Status.FINISHED,
        ).select_related('home_team', 'away_team', 'season')

        if league_codes:
            matches_query = matches_query.filter(
                season__league__code__in=league_codes
            )

        matches = list(matches_query.order_by('match_date'))
        logger.info(f"Found {len(matches)} matches")

        features_list = []
        results = []
        total_goals = []

        for i, match in enumerate(matches):
            try:
                # Build features
                features = self.build_features(
                    home_team_id=match.home_team_id,
                    away_team_id=match.away_team_id,
                    match_date=match.match_date,
                    season_code=match.season.code,
                    include_odds=True
                )

                if features:
                    features_list.append(features)

                    # Target: match result (0=home win, 1=draw, 2=away win)
                    if match.home_score > match.away_score:
                        results.append(0)
                    elif match.home_score == match.away_score:
                        results.append(1)
                    else:
                        results.append(2)

                    total_goals.append(match.home_score + match.away_score)

                if (i + 1) % 500 == 0:
                    logger.info(f"Processed {i + 1}/{len(matches)} matches")

            except Exception as e:
                logger.error(f"Error processing match {match.id}: {e}")
                continue

        # Clear cache to free memory
        self.clear_cache()
        self.team_builder.clear_cache()

        df = pd.DataFrame(features_list)
        return df, pd.Series(results), pd.Series(total_goals)

    def clear_cache(self):
        """Clear the feature cache."""
        self._cache.clear()
