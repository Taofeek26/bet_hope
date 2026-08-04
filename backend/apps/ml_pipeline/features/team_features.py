"""
Team Feature Engineering

Extracts features for teams including:
- Form metrics (recent performance)
- Season statistics
- xG-based metrics
- Home/Away splits
"""
import bisect
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Any
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from django.db.models import Avg, Sum, Count, Q, F

logger = logging.getLogger(__name__)


class TeamFeatureBuilder:
    """
    Builds feature vectors for teams based on historical performance.
    """

    # Number of recent matches for form calculation
    FORM_MATCHES = 5

    # Exponential decay factor for weighted averages
    DECAY_FACTOR = 0.9

    def __init__(self):
        """Initialize the feature builder."""
        self._cache = {}
        self._warmed = False
        self._matches_by_team: Dict[int, List] = {}
        self._match_dates_by_team: Dict[int, List[date]] = {}
        self._season_stats_by_team_season: Dict[tuple, Any] = {}
        self._season_stats_latest_by_team: Dict[int, Any] = {}

    def warm_cache(self, team_ids: List[int]) -> None:
        """
        Bulk-load everything build_features() would otherwise query per
        (team, as_of_date) call — recent matches and season stats — for
        the given teams, once. Training loops over thousands of matches
        were each triggering their own DB round trips per team per match
        (15-40+ queries/match with the H2H/context/odds/injury lookups in
        MatchFeatureBuilder on top), which is why training any scope
        beyond a single league/season timed out on Lambda's 900s ceiling.
        After this, _get_recent_matches/_get_season_stats serve from
        memory. Single-match inference (predict_match) doesn't call this
        and keeps using the original per-call DB path — warming the cache
        for one match isn't worth it.
        """
        from apps.matches.models import Match
        from apps.teams.models import TeamSeasonStats

        team_ids = set(team_ids)

        matches = list(
            Match.objects.filter(
                Q(home_team_id__in=team_ids) | Q(away_team_id__in=team_ids),
                status=Match.Status.FINISHED,
            )
            .select_related('statistics')
            .order_by('match_date')
        )

        self._matches_by_team = defaultdict(list)
        for m in matches:
            if m.home_team_id in team_ids:
                self._matches_by_team[m.home_team_id].append(m)
            if m.away_team_id in team_ids:
                self._matches_by_team[m.away_team_id].append(m)

        self._match_dates_by_team = {
            team_id: [m.match_date for m in team_matches]
            for team_id, team_matches in self._matches_by_team.items()
        }

        stats_list = list(
            TeamSeasonStats.objects.filter(team_id__in=team_ids).select_related('season')
        )
        self._season_stats_by_team_season = {
            (s.team_id, s.season.code): s for s in stats_list
        }
        by_team = defaultdict(list)
        for s in stats_list:
            by_team[s.team_id].append(s)
        self._season_stats_latest_by_team = {
            team_id: max(team_stats, key=lambda s: s.season.code)
            for team_id, team_stats in by_team.items()
        }

        self._warmed = True

    def _recent_matches_from_cache(self, team_id: int, as_of_date: date, limit: int) -> List:
        """Slice of this team's warmed match list strictly before as_of_date, most-recent-first."""
        dates = self._match_dates_by_team.get(team_id, [])
        idx = bisect.bisect_left(dates, as_of_date)
        recent = self._matches_by_team[team_id][max(0, idx - limit):idx]
        return list(reversed(recent))

    def build_features(
        self,
        team_id: int,
        as_of_date: date,
        is_home: bool = True,
        season_code: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Build feature vector for a team.

        Args:
            team_id: Team database ID
            as_of_date: Calculate features as of this date
            is_home: Whether this is a home match
            season_code: Optional season filter

        Returns:
            Dict of feature name -> value
        """
        from apps.teams.models import Team, TeamSeasonStats
        from apps.matches.models import Match

        cache_key = f"{team_id}_{as_of_date}_{is_home}_{season_code}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            logger.error(f"Team {team_id} not found")
            return {}

        features = {}

        # Get recent matches before the as_of_date
        recent_matches = self._get_recent_matches(team, as_of_date, self.FORM_MATCHES * 2)

        # Form features (last N matches)
        form_features = self._calculate_form_features(team, recent_matches[:self.FORM_MATCHES])
        features.update(form_features)

        # Extended form (last 2N matches)
        extended_form = self._calculate_form_features(team, recent_matches, prefix='extended_')
        features.update(extended_form)

        # Home/Away specific form
        venue_matches = [m for m in recent_matches if self._is_home_match(team, m) == is_home]
        venue_form = self._calculate_form_features(team, venue_matches[:self.FORM_MATCHES], prefix='venue_')
        features.update(venue_form)

        # Season statistics
        season_stats = self._get_season_stats(team, season_code)
        features.update(season_stats)

        # xG-based features
        xg_features = self._calculate_xg_features(team, recent_matches)
        features.update(xg_features)

        # Scoring patterns
        scoring_features = self._calculate_scoring_patterns(team, recent_matches)
        features.update(scoring_features)

        # Add home/away indicator
        features['is_home'] = 1.0 if is_home else 0.0

        self._cache[cache_key] = features
        return features

    def _get_recent_matches(
        self,
        team,
        as_of_date: date,
        limit: int = 10
    ) -> List:
        """Get recent finished matches for a team."""
        if self._warmed:
            return self._recent_matches_from_cache(team.id, as_of_date, limit)

        from apps.matches.models import Match

        matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            match_date__lt=as_of_date,
            status=Match.Status.FINISHED,
        ).order_by('-match_date')[:limit]

        return list(matches)

    def _is_home_match(self, team, match) -> bool:
        """Check if team played at home."""
        return match.home_team_id == team.id

    def _calculate_form_features(
        self,
        team,
        matches: List,
        prefix: str = ''
    ) -> Dict[str, float]:
        """
        Calculate form features from recent matches.

        Returns:
            Dict with form metrics
        """
        if not matches:
            return {
                f'{prefix}form_points': 0.0,
                f'{prefix}form_goals_scored': 0.0,
                f'{prefix}form_goals_conceded': 0.0,
                f'{prefix}form_goal_diff': 0.0,
                f'{prefix}form_win_rate': 0.0,
                f'{prefix}form_draw_rate': 0.0,
                f'{prefix}form_loss_rate': 0.0,
                f'{prefix}form_clean_sheets': 0.0,
                f'{prefix}form_failed_to_score': 0.0,
            }

        points = 0
        goals_scored = 0
        goals_conceded = 0
        wins = 0
        draws = 0
        losses = 0
        clean_sheets = 0
        failed_to_score = 0
        weighted_points = 0.0

        for i, match in enumerate(matches):
            is_home = self._is_home_match(team, match)

            if is_home:
                gf = match.home_score or 0
                ga = match.away_score or 0
            else:
                gf = match.away_score or 0
                ga = match.home_score or 0

            goals_scored += gf
            goals_conceded += ga

            if ga == 0:
                clean_sheets += 1
            if gf == 0:
                failed_to_score += 1

            # Points calculation
            if gf > ga:
                match_points = 3
                wins += 1
            elif gf == ga:
                match_points = 1
                draws += 1
            else:
                match_points = 0
                losses += 1

            points += match_points
            # Weighted points (more recent = higher weight)
            weight = self.DECAY_FACTOR ** i
            weighted_points += match_points * weight

        n = len(matches)
        return {
            f'{prefix}form_points': points / (n * 3) if n > 0 else 0.0,
            f'{prefix}form_goals_scored': goals_scored / n if n > 0 else 0.0,
            f'{prefix}form_goals_conceded': goals_conceded / n if n > 0 else 0.0,
            f'{prefix}form_goal_diff': (goals_scored - goals_conceded) / n if n > 0 else 0.0,
            f'{prefix}form_win_rate': wins / n if n > 0 else 0.0,
            f'{prefix}form_draw_rate': draws / n if n > 0 else 0.0,
            f'{prefix}form_loss_rate': losses / n if n > 0 else 0.0,
            f'{prefix}form_clean_sheets': clean_sheets / n if n > 0 else 0.0,
            f'{prefix}form_failed_to_score': failed_to_score / n if n > 0 else 0.0,
            f'{prefix}form_weighted_points': weighted_points / n if n > 0 else 0.0,
        }

    def _get_season_stats(
        self,
        team,
        season_code: Optional[str] = None
    ) -> Dict[str, float]:
        """Get season aggregate statistics."""
        from apps.teams.models import TeamSeasonStats
        from apps.leagues.models import Season

        try:
            if self._warmed:
                if season_code:
                    stats = self._season_stats_by_team_season.get((team.id, season_code))
                else:
                    stats = self._season_stats_latest_by_team.get(team.id)
            elif season_code:
                stats = TeamSeasonStats.objects.get(
                    team=team,
                    season__code=season_code
                )
            else:
                stats = TeamSeasonStats.objects.filter(
                    team=team
                ).order_by('-season__code').first()

            if not stats:
                raise TeamSeasonStats.DoesNotExist

            played = stats.wins + stats.draws + stats.losses
            return {
                'season_points': (stats.wins * 3 + stats.draws) / played if played > 0 else 0.0,
                'season_goals_per_game': stats.goals_for / played if played > 0 else 0.0,
                'season_conceded_per_game': stats.goals_against / played if played > 0 else 0.0,
                'season_goal_diff': (stats.goals_for - stats.goals_against) / played if played > 0 else 0.0,
                'season_win_rate': stats.wins / played if played > 0 else 0.0,
                'season_xg_diff': float(stats.xg_for or 0) - float(stats.xg_against or 0),
                'season_matches_played': played,
            }

        except TeamSeasonStats.DoesNotExist:
            return {
                'season_points': 0.0,
                'season_goals_per_game': 0.0,
                'season_conceded_per_game': 0.0,
                'season_goal_diff': 0.0,
                'season_win_rate': 0.0,
                'season_xg_diff': 0.0,
                'season_matches_played': 0,
            }

    def _calculate_xg_features(
        self,
        team,
        matches: List
    ) -> Dict[str, float]:
        """Calculate xG-based features."""
        xg_for = []
        xg_against = []
        xg_overperformance = []

        for match in matches:
            is_home = self._is_home_match(team, match)

            # xG data is in MatchStatistics, not Match
            stats = getattr(match, 'statistics', None)
            if stats is None:
                try:
                    stats = match.statistics
                except Exception:
                    stats = None

            if is_home:
                xg = float(stats.xg_home or 0) if stats else 0
                xga = float(stats.xg_away or 0) if stats else 0
                actual = match.home_score or 0
            else:
                xg = float(stats.xg_away or 0) if stats else 0
                xga = float(stats.xg_home or 0) if stats else 0
                actual = match.away_score or 0

            if xg > 0:
                xg_for.append(xg)
                xg_overperformance.append(actual - xg)
            if xga > 0:
                xg_against.append(xga)

        return {
            'xg_for_avg': np.mean(xg_for) if xg_for else 0.0,
            'xg_against_avg': np.mean(xg_against) if xg_against else 0.0,
            'xg_diff': np.mean(xg_for) - np.mean(xg_against) if xg_for and xg_against else 0.0,
            'xg_overperformance': np.mean(xg_overperformance) if xg_overperformance else 0.0,
        }

    def _calculate_scoring_patterns(
        self,
        team,
        matches: List
    ) -> Dict[str, float]:
        """Calculate scoring pattern features."""
        if not matches:
            return {
                'btts_rate': 0.0,
                'over_25_rate': 0.0,
                'over_15_rate': 0.0,
                'first_half_goals_rate': 0.0,
            }

        btts = 0
        over_25 = 0
        over_15 = 0
        first_half_goals = 0

        for match in matches:
            home_score = match.home_score or 0
            away_score = match.away_score or 0
            total = home_score + away_score

            if home_score > 0 and away_score > 0:
                btts += 1
            if total > 2.5:
                over_25 += 1
            if total > 1.5:
                over_15 += 1

            # First half goals
            ht_home = match.home_halftime_score or 0
            ht_away = match.away_halftime_score or 0
            if (ht_home + ht_away) > 0:
                first_half_goals += 1

        n = len(matches)
        return {
            'btts_rate': btts / n,
            'over_25_rate': over_25 / n,
            'over_15_rate': over_15 / n,
            'first_half_goals_rate': first_half_goals / n,
        }

    def clear_cache(self):
        """Clear the feature cache, including anything warm_cache loaded."""
        self._cache.clear()
        self._warmed = False
        self._matches_by_team = {}
        self._match_dates_by_team = {}
        self._season_stats_by_team_season = {}
        self._season_stats_latest_by_team = {}
