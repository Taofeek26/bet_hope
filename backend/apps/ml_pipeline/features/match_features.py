"""
Match Feature Engineering

Combines team features with head-to-head and contextual features
to create a complete feature vector for match prediction.
"""
import bisect
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
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
        self._warmed = False
        self._odds_by_match_id: Dict[int, Any] = {}
        self._injury_dates_by_team: Dict[int, List[date]] = {}
        self._injury_counts_by_team_date: Dict[tuple, int] = {}

    def warm_cache(self, team_ids: List[int], matches: List) -> None:
        """
        Bulk-load everything H2H/context/odds/injury features need for
        this batch of matches, once — see TeamFeatureBuilder.warm_cache
        for why. `matches` must already be select_related('odds') so odds
        come for free from what build_training_dataset already fetched,
        no extra query.
        """
        from apps.teams.models import TeamInjury

        self.team_builder.warm_cache(team_ids)

        self._odds_by_match_id = {}
        for m in matches:
            try:
                if m.odds:
                    self._odds_by_match_id[m.id] = m.odds
            except Exception:
                pass

        injuries = list(
            TeamInjury.objects.filter(team_id__in=team_ids).values('team_id', 'as_of_date')
        )
        counts = defaultdict(int)
        for i in injuries:
            counts[(i['team_id'], i['as_of_date'])] += 1
        self._injury_counts_by_team_date = dict(counts)

        dates_by_team = defaultdict(set)
        for team_id, as_of_date in self._injury_counts_by_team_date:
            dates_by_team[team_id].add(as_of_date)
        self._injury_dates_by_team = {
            team_id: sorted(dates) for team_id, dates in dates_by_team.items()
        }

        self._warmed = True

    def build_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: date,
        season_code: Optional[str] = None,
        include_odds: bool = True,
        include_ai_signals: bool = False,
        match_id: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Build complete feature vector for a match.

        Args:
            home_team_id: Home team database ID
            away_team_id: Away team database ID
            match_date: Date of the match
            season_code: Optional season filter
            include_odds: Whether to include betting odds features
            match_id: Optional — when the caller already has the Match row
                (e.g. the training loop), passing its id lets odds come
                from the warmed cache instead of a redundant re-query.

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
                home_team_id, away_team_id, match_date, match_id=match_id
            )
            features.update(odds_features)

        # Injury/unavailability features (0.0 default for teams/dates with
        # no synced injury data, e.g. all historical training matches from
        # before this feature existed)
        injury_features = self._get_injury_features(
            home_team_id, away_team_id, match_date
        )
        features.update(injury_features)

        # LLM-derived news signals — off by default (see
        # NewsSignalExtractionService docstring): experimental until
        # backtested to actually improve holdout accuracy, since sparse
        # news coverage could just add noise rather than signal.
        if include_ai_signals:
            ai_features = self._get_ai_signal_features(
                home_team_id, away_team_id, match_date
            )
            features.update(ai_features)

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
        if self._warmed:
            team_matches = self.team_builder._matches_by_team.get(home_team_id, [])
            h2h_matches = [
                m for m in team_matches
                if m.match_date < as_of_date
                and (m.home_team_id == away_team_id or m.away_team_id == away_team_id)
            ][-limit:][::-1]
        else:
            h2h_matches = list(Match.objects.filter(
                Q(home_team_id=home_team_id, away_team_id=away_team_id) |
                Q(home_team_id=away_team_id, away_team_id=home_team_id),
                match_date__lt=as_of_date,
                status=Match.Status.FINISHED,
            ).order_by('-match_date')[:limit])

        if not h2h_matches:
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

        n = len(h2h_matches)
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

        def last_match_before(team_id):
            if self._warmed:
                recent = self.team_builder._recent_matches_from_cache(team_id, match_date, limit=1)
                return recent[0] if recent else None
            return Match.objects.filter(
                Q(home_team_id=team_id) | Q(away_team_id=team_id),
                match_date__lt=match_date,
                status=Match.Status.FINISHED,
            ).order_by('-match_date').first()

        # Rest days for home team
        home_last_match = last_match_before(home_team_id)
        if home_last_match:
            home_rest = (match_date - home_last_match.match_date).days
        else:
            home_rest = 7  # Default

        # Rest days for away team
        away_last_match = last_match_before(away_team_id)
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
        match_date: date,
        match_id: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Get betting odds features (implied probabilities).

        Returns:
            Dict of odds-based features
        """
        from apps.matches.models import Match, MatchOdds

        try:
            if self._warmed and match_id is not None:
                odds = self._odds_by_match_id.get(match_id)
            else:
                # .filter().first(), not .get() — a data-quality bug in the
                # fixture sync (fixed separately) could produce duplicate
                # Match rows for the same fixture; this path shouldn't take
                # the whole prediction down if that ever happens again.
                match = Match.objects.filter(
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    match_date=match_date,
                ).order_by('-id').first()
                if match is None:
                    raise Match.DoesNotExist
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

    def _get_injury_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: date
    ) -> Dict[str, float]:
        """
        Count of reported unavailable players (injuries/suspensions) as of
        the most recent synced snapshot before the match. TeamInjury rows
        are periodic snapshots (see sync_injuries_to_database), not a
        continuous history, so this uses "most recent as_of_date <=
        match_date" per team rather than an ever-growing cumulative count.

        Returns:
            Dict of injury-count features (0.0 when no data is available,
            e.g. for historical matches predating this feature)
        """
        from apps.teams.models import TeamInjury

        def count_for(team_id: int) -> float:
            if self._warmed:
                dates = self._injury_dates_by_team.get(team_id, [])
                idx = bisect.bisect_right(dates, match_date) - 1
                if idx < 0:
                    return 0.0
                latest = dates[idx]
                return float(self._injury_counts_by_team_date.get((team_id, latest), 0))

            latest = TeamInjury.objects.filter(
                team_id=team_id, as_of_date__lte=match_date
            ).order_by('-as_of_date').values_list('as_of_date', flat=True).first()
            if not latest:
                return 0.0
            return float(TeamInjury.objects.filter(team_id=team_id, as_of_date=latest).count())

        home_count = count_for(home_team_id)
        away_count = count_for(away_team_id)

        return {
            'home_injury_count': home_count,
            'away_injury_count': away_count,
            'injury_count_diff': home_count - away_count,
        }

    def _get_ai_signal_features(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: date
    ) -> Dict[str, float]:
        """
        Most recent LLM-derived news signal (injury mentions, sentiment)
        per team as of the match date. Same "most recent snapshot before
        match_date" pattern as _get_injury_features. Defaults to neutral
        (0.0) when no signal has been generated for a team/date — critical
        so historical training data (which predates this feature entirely)
        doesn't break, and matches with no news coverage aren't penalized.
        """
        from apps.documents.models import TeamNewsSignal

        def signal_for(team_id: int) -> Dict[str, float]:
            signal = TeamNewsSignal.objects.filter(
                team_id=team_id, as_of_date__lte=match_date
            ).order_by('-as_of_date').first()
            if not signal:
                return {'injury_mention_score': 0.0, 'sentiment_score': 0.0}
            return {
                'injury_mention_score': signal.injury_mention_score,
                'sentiment_score': signal.sentiment_score,
            }

        home_signal = signal_for(home_team_id)
        away_signal = signal_for(away_team_id)

        return {
            'home_injury_mention_score': home_signal['injury_mention_score'],
            'away_injury_mention_score': away_signal['injury_mention_score'],
            'home_news_sentiment': home_signal['sentiment_score'],
            'away_news_sentiment': away_signal['sentiment_score'],
        }

    def _odds_to_probability(self, odds) -> float:
        """Convert decimal odds to probability."""
        if odds is None or float(odds) <= 1:
            return 0.0
        return 1.0 / float(odds)

    def build_training_dataset(
        self,
        season_codes: List[str],
        league_codes: Optional[List[str]] = None,
        include_ai_signals: bool = False
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Build training dataset from historical matches.

        Args:
            season_codes: List of season codes to include
            league_codes: Optional list of league codes
            include_ai_signals: Whether to include the experimental
                LLM-derived news signal features (default off — see
                NewsSignalExtractionService docstring on why this needs a
                backtest before becoming a default-on feature)

        Returns:
            Tuple of (features_df, target_result, target_goals)
        """
        from apps.matches.models import Match
        from apps.leagues.models import Season

        logger.info(f"Building training dataset for seasons: {season_codes}")

        matches_query = Match.objects.filter(
            season__code__in=season_codes,
            status=Match.Status.FINISHED,
        ).select_related('home_team', 'away_team', 'season', 'odds')

        if league_codes:
            matches_query = matches_query.filter(
                season__league__code__in=league_codes
            )

        matches = list(matches_query.order_by('match_date'))
        logger.info(f"Found {len(matches)} matches")

        team_ids = set()
        for m in matches:
            team_ids.add(m.home_team_id)
            team_ids.add(m.away_team_id)
        self.warm_cache(team_ids, matches)
        logger.info(f"Warmed cache for {len(team_ids)} teams")

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
                    include_odds=True,
                    include_ai_signals=include_ai_signals,
                    match_id=match.id,
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
        """Clear the feature cache, including anything warm_cache loaded."""
        self._cache.clear()
        self._warmed = False
        self._odds_by_match_id = {}
        self._injury_dates_by_team = {}
        self._injury_counts_by_team_date = {}
