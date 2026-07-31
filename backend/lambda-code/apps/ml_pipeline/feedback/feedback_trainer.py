"""
Feedback-Driven Model Training

Improves model accuracy by learning from past prediction outcomes.
Uses sample weighting to emphasize:
- Recent matches (time decay)
- Incorrectly predicted matches (hard negative mining)
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from django.utils import timezone

logger = logging.getLogger(__name__)


class FeedbackTrainer:
    """
    Implements feedback-driven learning for match predictions.

    Key Features:
    - Time decay weighting: Recent matches are more important
    - Hard negative mining: Incorrectly predicted matches get higher weight
    - Confidence-based weighting: High-confidence wrong predictions penalized more
    """

    # Weight configuration
    DEFAULT_CONFIG = {
        'time_decay_factor': 0.98,      # Daily decay factor (0.98^30 ≈ 0.55 after 30 days)
        'wrong_prediction_boost': 2.0,   # Multiplier for wrong predictions
        'high_confidence_wrong_boost': 1.5,  # Extra boost for high-confidence wrong
        'min_weight': 0.1,               # Minimum sample weight
        'max_weight': 5.0,               # Maximum sample weight
        'recent_days': 90,               # Days to consider "recent"
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the feedback trainer.

        Args:
            config: Optional configuration overrides
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

    def build_weighted_training_data(
        self,
        season_codes: List[str],
        league_codes: Optional[List[str]] = None,
        include_prediction_feedback: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series, np.ndarray]:
        """
        Build training dataset with sample weights based on prediction feedback.

        Args:
            season_codes: List of season codes to include
            league_codes: Optional league filter
            include_prediction_feedback: Whether to use prediction feedback for weighting

        Returns:
            Tuple of (features_df, result_labels, goals_labels, sample_weights)
        """
        from apps.matches.models import Match
        from apps.predictions.models import Prediction
        from apps.ml_pipeline.features.match_features import MatchFeatureBuilder

        logger.info(f"Building weighted training dataset for seasons: {season_codes}")

        # Get all finished matches
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

        # Get predictions with feedback
        predictions_map = {}
        if include_prediction_feedback:
            predictions = Prediction.objects.filter(
                match__in=matches,
                is_correct__isnull=False  # Only validated predictions
            ).select_related('match')

            for pred in predictions:
                predictions_map[pred.match_id] = {
                    'is_correct': pred.is_correct,
                    'confidence': float(pred.confidence_score) if pred.confidence_score else 0.5,
                    'recommended_outcome': pred.recommended_outcome,
                }
            logger.info(f"Found {len(predictions_map)} validated predictions")

        # Build features with weights
        match_builder = MatchFeatureBuilder()
        today = timezone.now().date()

        features_list = []
        results = []
        total_goals = []
        weights = []

        for i, match in enumerate(matches):
            try:
                # Build features
                features = match_builder.build_features(
                    home_team_id=match.home_team_id,
                    away_team_id=match.away_team_id,
                    match_date=match.match_date,
                    season_code=match.season.code,
                    include_odds=True
                )

                if not features:
                    continue

                features_list.append(features)

                # Target: match result (0=home win, 1=draw, 2=away win)
                if match.home_score > match.away_score:
                    results.append(0)
                elif match.home_score == match.away_score:
                    results.append(1)
                else:
                    results.append(2)

                total_goals.append(match.home_score + match.away_score)

                # Calculate sample weight
                weight = self._calculate_sample_weight(
                    match=match,
                    prediction_info=predictions_map.get(match.id),
                    reference_date=today
                )
                weights.append(weight)

                if (i + 1) % 500 == 0:
                    logger.info(f"Processed {i + 1}/{len(matches)} matches")

            except Exception as e:
                logger.error(f"Error processing match {match.id}: {e}")
                continue

        # Clear cache
        match_builder.clear_cache()

        df = pd.DataFrame(features_list)
        weights_array = np.array(weights)

        # Log weight statistics
        logger.info(f"Sample weight stats: min={weights_array.min():.3f}, "
                   f"max={weights_array.max():.3f}, mean={weights_array.mean():.3f}")

        return df, pd.Series(results), pd.Series(total_goals), weights_array

    def _calculate_sample_weight(
        self,
        match,
        prediction_info: Optional[Dict],
        reference_date: date
    ) -> float:
        """
        Calculate sample weight for a match.

        Weight is increased for:
        - Recent matches (time decay)
        - Incorrectly predicted matches
        - High-confidence wrong predictions

        Args:
            match: Match object
            prediction_info: Dict with prediction feedback (or None)
            reference_date: Reference date for time decay

        Returns:
            Sample weight (float)
        """
        weight = 1.0

        # 1. Time decay - recent matches weighted more
        days_ago = (reference_date - match.match_date).days
        if days_ago > 0:
            time_weight = self.config['time_decay_factor'] ** days_ago
            weight *= max(time_weight, self.config['min_weight'])

        # 2. Prediction feedback weighting
        if prediction_info:
            if not prediction_info['is_correct']:
                # Wrong prediction - boost weight to learn from mistake
                weight *= self.config['wrong_prediction_boost']

                # Extra boost for high-confidence wrong predictions
                if prediction_info['confidence'] > 0.6:
                    weight *= self.config['high_confidence_wrong_boost']

        # Clamp weight
        weight = max(self.config['min_weight'], min(weight, self.config['max_weight']))

        return weight

    def analyze_prediction_errors(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze recent prediction errors to identify patterns.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with error analysis
        """
        from apps.predictions.models import Prediction
        from apps.matches.models import Match
        from django.db.models import Count, Q, Avg

        cutoff_date = timezone.now().date() - timedelta(days=days)

        # Get recent validated predictions
        predictions = Prediction.objects.filter(
            match__match_date__gte=cutoff_date,
            match__status=Match.Status.FINISHED,
            is_correct__isnull=False
        ).select_related('match', 'match__season__league')

        total = predictions.count()
        if total == 0:
            return {'status': 'no_data', 'message': 'No validated predictions found'}

        correct = predictions.filter(is_correct=True).count()

        # Analyze by outcome type
        by_outcome = {}
        for outcome in ['HOME', 'DRAW', 'AWAY']:
            outcome_preds = predictions.filter(recommended_outcome=outcome)
            outcome_total = outcome_preds.count()
            outcome_correct = outcome_preds.filter(is_correct=True).count()
            by_outcome[outcome] = {
                'total': outcome_total,
                'correct': outcome_correct,
                'accuracy': outcome_correct / outcome_total if outcome_total > 0 else 0
            }

        # Analyze by confidence level
        by_confidence = {
            'high': {'total': 0, 'correct': 0},
            'medium': {'total': 0, 'correct': 0},
            'low': {'total': 0, 'correct': 0},
        }

        for pred in predictions:
            conf = float(pred.confidence_score) if pred.confidence_score else 0.5
            if conf >= 0.6:
                level = 'high'
            elif conf >= 0.45:
                level = 'medium'
            else:
                level = 'low'

            by_confidence[level]['total'] += 1
            if pred.is_correct:
                by_confidence[level]['correct'] += 1

        for level, data in by_confidence.items():
            data['accuracy'] = data['correct'] / data['total'] if data['total'] > 0 else 0

        # Analyze by league
        by_league = {}
        league_stats = predictions.values(
            'match__season__league__code'
        ).annotate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True))
        )

        for stat in league_stats:
            code = stat['match__season__league__code']
            by_league[code] = {
                'total': stat['total'],
                'correct': stat['correct'],
                'accuracy': stat['correct'] / stat['total'] if stat['total'] > 0 else 0
            }

        return {
            'status': 'success',
            'period_days': days,
            'total_predictions': total,
            'correct_predictions': correct,
            'overall_accuracy': correct / total,
            'by_outcome': by_outcome,
            'by_confidence': by_confidence,
            'by_league': by_league,
            'recommendations': self._generate_recommendations(by_outcome, by_confidence, by_league)
        }

    def _generate_recommendations(
        self,
        by_outcome: Dict,
        by_confidence: Dict,
        by_league: Dict
    ) -> List[str]:
        """Generate training recommendations based on error analysis."""
        recommendations = []

        # Check outcome imbalance
        accuracies = {k: v['accuracy'] for k, v in by_outcome.items()}
        if accuracies:
            worst_outcome = min(accuracies, key=accuracies.get)
            if accuracies[worst_outcome] < 0.35:
                recommendations.append(
                    f"Focus on improving {worst_outcome} predictions "
                    f"(accuracy: {accuracies[worst_outcome]:.1%})"
                )

        # Check confidence calibration
        if by_confidence['high']['accuracy'] < by_confidence['low']['accuracy']:
            recommendations.append(
                "Model confidence is poorly calibrated - high confidence predictions "
                "are less accurate than low confidence ones"
            )

        # Check league performance
        if by_league:
            worst_league = min(by_league.items(), key=lambda x: x[1]['accuracy'])
            if worst_league[1]['accuracy'] < 0.30 and worst_league[1]['total'] >= 10:
                recommendations.append(
                    f"Consider excluding or adding more features for {worst_league[0]} "
                    f"(accuracy: {worst_league[1]['accuracy']:.1%})"
                )

        if not recommendations:
            recommendations.append("Model is performing reasonably well across all dimensions")

        return recommendations

    def get_hard_negatives(
        self,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get hardest negative examples (high-confidence wrong predictions).

        These are the most valuable for retraining.

        Args:
            limit: Maximum number of examples to return

        Returns:
            List of hard negative examples with details
        """
        from apps.predictions.models import Prediction
        from apps.matches.models import Match

        # Get high-confidence wrong predictions
        hard_negatives = Prediction.objects.filter(
            is_correct=False,
            match__status=Match.Status.FINISHED,
            confidence_score__gte=0.5
        ).select_related(
            'match', 'match__home_team', 'match__away_team'
        ).order_by('-confidence_score')[:limit]

        results = []
        for pred in hard_negatives:
            results.append({
                'match_id': pred.match_id,
                'date': pred.match.match_date.isoformat(),
                'home_team': pred.match.home_team.name,
                'away_team': pred.match.away_team.name,
                'predicted': pred.recommended_outcome,
                'actual': pred.actual_outcome,
                'confidence': float(pred.confidence_score),
                'home_prob': float(pred.home_win_probability),
                'draw_prob': float(pred.draw_probability),
                'away_prob': float(pred.away_win_probability),
            })

        return results
