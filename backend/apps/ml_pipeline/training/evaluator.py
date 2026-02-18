"""
Model Evaluation Module

Comprehensive evaluation of prediction models including:
- Classification metrics
- Calibration analysis
- Betting ROI simulation
- Confidence analysis
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    log_loss,
    confusion_matrix,
    classification_report,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.calibration import calibration_curve

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    Evaluates prediction model performance.

    Provides comprehensive metrics including:
    - Standard classification metrics
    - Probability calibration
    - Betting performance simulation
    """

    RESULT_LABELS = ['Home', 'Draw', 'Away']

    def __init__(self):
        """Initialize the evaluator."""
        self.evaluation_results = {}

    def evaluate_result_model(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: np.ndarray,
        odds: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation of result prediction model.

        Args:
            y_true: True labels (0=home, 1=draw, 2=away)
            y_pred: Predicted labels
            y_proba: Predicted probabilities (n_samples, 3)
            odds: Optional DataFrame with odds columns

        Returns:
            Dict with evaluation metrics
        """
        results = {
            'classification': self._classification_metrics(y_true, y_pred, y_proba),
            'calibration': self._calibration_metrics(y_true, y_proba),
            'confidence': self._confidence_analysis(y_true, y_pred, y_proba),
        }

        if odds is not None:
            results['betting'] = self._betting_simulation(y_true, y_proba, odds)

        self.evaluation_results = results
        return results

    def _classification_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: np.ndarray
    ) -> Dict[str, Any]:
        """Calculate classification metrics."""
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'log_loss': log_loss(y_true, y_proba),
            'n_samples': len(y_true),
        }

        # Per-class metrics
        for i, label in enumerate(self.RESULT_LABELS):
            binary_true = (y_true == i).astype(int)
            binary_pred = (y_pred == i).astype(int)

            metrics[f'{label.lower()}_precision'] = precision_score(
                binary_true, binary_pred, zero_division=0
            )
            metrics[f'{label.lower()}_recall'] = recall_score(
                binary_true, binary_pred, zero_division=0
            )
            metrics[f'{label.lower()}_f1'] = f1_score(
                binary_true, binary_pred, zero_division=0
            )

            # Brier score for probability calibration
            if y_proba.shape[1] > i:
                metrics[f'{label.lower()}_brier'] = brier_score_loss(
                    binary_true, y_proba[:, i]
                )

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm.tolist()

        return metrics

    def _calibration_metrics(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        n_bins: int = 10
    ) -> Dict[str, Any]:
        """
        Calculate probability calibration metrics.

        Returns:
            Dict with calibration data for each class
        """
        calibration = {}

        for i, label in enumerate(self.RESULT_LABELS):
            binary_true = (y_true == i).astype(int)
            probs = y_proba[:, i]

            try:
                fraction_of_positives, mean_predicted_value = calibration_curve(
                    binary_true, probs, n_bins=n_bins, strategy='uniform'
                )

                # Calculate Expected Calibration Error (ECE)
                bin_counts = np.histogram(probs, bins=n_bins, range=(0, 1))[0]
                ece = np.sum(
                    bin_counts * np.abs(fraction_of_positives - mean_predicted_value)
                ) / len(y_true)

                calibration[label.lower()] = {
                    'fraction_positives': fraction_of_positives.tolist(),
                    'mean_predicted': mean_predicted_value.tolist(),
                    'ece': ece,
                }

            except Exception as e:
                logger.warning(f"Calibration error for {label}: {e}")
                calibration[label.lower()] = {'error': str(e)}

        return calibration

    def _confidence_analysis(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: np.ndarray
    ) -> Dict[str, Any]:
        """
        Analyze prediction confidence vs accuracy.

        Returns:
            Dict with confidence-binned accuracy
        """
        max_probs = y_proba.max(axis=1)
        correct = (y_true == y_pred).astype(int)

        # Bin by confidence level
        bins = [0, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        bin_labels = ['<40%', '40-50%', '50-60%', '60-70%', '70-80%', '80-90%', '90%+']

        results = {}
        for i in range(len(bins) - 1):
            mask = (max_probs >= bins[i]) & (max_probs < bins[i + 1])
            if mask.sum() > 0:
                results[bin_labels[i]] = {
                    'count': int(mask.sum()),
                    'accuracy': float(correct[mask].mean()),
                    'avg_confidence': float(max_probs[mask].mean()),
                }

        # Overall stats
        results['overall'] = {
            'avg_confidence': float(max_probs.mean()),
            'high_conf_accuracy': float(
                correct[max_probs > 0.6].mean() if (max_probs > 0.6).sum() > 0 else 0
            ),
            'low_conf_accuracy': float(
                correct[max_probs <= 0.6].mean() if (max_probs <= 0.6).sum() > 0 else 0
            ),
        }

        return results

    def _betting_simulation(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        odds: pd.DataFrame,
        stake: float = 10.0,
        value_threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        Simulate betting performance.

        Args:
            y_true: True outcomes
            y_proba: Predicted probabilities
            odds: DataFrame with home_odds, draw_odds, away_odds
            stake: Stake per bet
            value_threshold: Minimum edge required to bet

        Returns:
            Dict with betting metrics
        """
        total_bets = 0
        total_stake = 0
        total_returns = 0
        results_by_type = {
            'home': {'bets': 0, 'won': 0, 'stake': 0, 'returns': 0},
            'draw': {'bets': 0, 'won': 0, 'stake': 0, 'returns': 0},
            'away': {'bets': 0, 'won': 0, 'stake': 0, 'returns': 0},
        }

        odds_cols = ['home_odds', 'draw_odds', 'away_odds']
        if not all(col in odds.columns for col in odds_cols):
            return {'error': 'Missing odds columns'}

        for i in range(len(y_true)):
            for j, (col, label) in enumerate(zip(odds_cols, ['home', 'draw', 'away'])):
                odd = float(odds.iloc[i][col]) if not pd.isna(odds.iloc[i][col]) else 0
                if odd <= 1:
                    continue

                implied_prob = 1 / odd
                model_prob = y_proba[i, j]

                # Value bet if model probability exceeds implied probability + threshold
                if model_prob > implied_prob + value_threshold:
                    total_bets += 1
                    total_stake += stake
                    results_by_type[label]['bets'] += 1
                    results_by_type[label]['stake'] += stake

                    # Check if bet won
                    if y_true[i] == j:
                        returns = stake * odd
                        total_returns += returns
                        results_by_type[label]['won'] += 1
                        results_by_type[label]['returns'] += returns

        roi = ((total_returns - total_stake) / total_stake * 100) if total_stake > 0 else 0

        return {
            'total_bets': total_bets,
            'total_stake': total_stake,
            'total_returns': total_returns,
            'profit': total_returns - total_stake,
            'roi_percent': roi,
            'win_rate': sum(r['won'] for r in results_by_type.values()) / total_bets if total_bets > 0 else 0,
            'by_type': results_by_type,
            'value_threshold': value_threshold,
        }

    def generate_report(self) -> str:
        """
        Generate human-readable evaluation report.

        Returns:
            Formatted report string
        """
        if not self.evaluation_results:
            return "No evaluation results available."

        lines = ["=" * 60, "MODEL EVALUATION REPORT", "=" * 60, ""]

        # Classification metrics
        if 'classification' in self.evaluation_results:
            clf = self.evaluation_results['classification']
            lines.append("CLASSIFICATION METRICS")
            lines.append("-" * 40)
            lines.append(f"Accuracy:     {clf['accuracy']:.4f}")
            lines.append(f"Log Loss:     {clf['log_loss']:.4f}")
            lines.append(f"Samples:      {clf['n_samples']}")
            lines.append("")

            for label in ['home', 'draw', 'away']:
                lines.append(f"{label.upper()}:")
                lines.append(f"  Precision: {clf.get(f'{label}_precision', 0):.4f}")
                lines.append(f"  Recall:    {clf.get(f'{label}_recall', 0):.4f}")
                lines.append(f"  F1:        {clf.get(f'{label}_f1', 0):.4f}")
            lines.append("")

        # Confidence analysis
        if 'confidence' in self.evaluation_results:
            conf = self.evaluation_results['confidence']
            lines.append("CONFIDENCE ANALYSIS")
            lines.append("-" * 40)

            for bin_name, stats in conf.items():
                if bin_name != 'overall' and isinstance(stats, dict):
                    lines.append(
                        f"{bin_name}: {stats['count']} bets, "
                        f"{stats['accuracy']:.1%} accuracy"
                    )

            if 'overall' in conf:
                overall = conf['overall']
                lines.append(f"\nHigh confidence (>60%) accuracy: {overall['high_conf_accuracy']:.1%}")
                lines.append(f"Low confidence (<=60%) accuracy: {overall['low_conf_accuracy']:.1%}")
            lines.append("")

        # Betting simulation
        if 'betting' in self.evaluation_results:
            bet = self.evaluation_results['betting']
            if 'error' not in bet:
                lines.append("BETTING SIMULATION")
                lines.append("-" * 40)
                lines.append(f"Total Bets:   {bet['total_bets']}")
                lines.append(f"Total Stake:  ${bet['total_stake']:.2f}")
                lines.append(f"Returns:      ${bet['total_returns']:.2f}")
                lines.append(f"Profit:       ${bet['profit']:.2f}")
                lines.append(f"ROI:          {bet['roi_percent']:.2f}%")
                lines.append(f"Win Rate:     {bet['win_rate']:.1%}")
                lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    def save_report(self, filepath: str):
        """Save evaluation report to file."""
        with open(filepath, 'w') as f:
            f.write(self.generate_report())
        logger.info(f"Report saved to: {filepath}")


def evaluate_predictions_batch(
    predictions: List[Dict],
    actuals: List[Dict]
) -> Dict[str, Any]:
    """
    Evaluate a batch of predictions against actual results.

    Args:
        predictions: List of prediction dicts with 'match_id', 'home_prob', etc.
        actuals: List of actual result dicts with 'match_id', 'result', etc.

    Returns:
        Dict with evaluation metrics
    """
    # Match predictions with actuals
    actual_map = {a['match_id']: a for a in actuals}

    y_true = []
    y_pred = []
    y_proba = []

    for pred in predictions:
        match_id = pred['match_id']
        if match_id not in actual_map:
            continue

        actual = actual_map[match_id]

        # Get true result
        if actual['home_score'] > actual['away_score']:
            true_result = 0
        elif actual['home_score'] == actual['away_score']:
            true_result = 1
        else:
            true_result = 2

        y_true.append(true_result)

        # Get predicted result and probabilities
        probs = [pred['home_prob'], pred['draw_prob'], pred['away_prob']]
        y_pred.append(np.argmax(probs))
        y_proba.append(probs)

    if not y_true:
        return {'error': 'No matched predictions'}

    evaluator = ModelEvaluator()
    return evaluator.evaluate_result_model(
        np.array(y_true),
        np.array(y_pred),
        np.array(y_proba)
    )
