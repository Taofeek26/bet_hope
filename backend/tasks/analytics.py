"""
Analytics Tasks

Tasks for calculating model performance metrics and statistics
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def calculate_model_metrics():
    """
    Calculate and store model performance metrics.
    Runs daily at 7:00 AM UTC.
    """
    logger.info("Calculating model performance metrics...")

    try:
        from apps.predictions.models import Prediction, ModelVersion
        from apps.matches.models import Match
        from django.db.models import Count, Q, Avg

        # Get predictions from last 30 days for finished matches
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        predictions = Prediction.objects.filter(
            match__match_date__gte=thirty_days_ago,
            match__status=Match.Status.FINISHED,
        ).select_related('match')

        if not predictions.exists():
            logger.warning("No predictions to analyze")
            return {'status': 'warning', 'message': 'No predictions to analyze'}

        total = 0
        correct = 0
        by_confidence = {'high': {'total': 0, 'correct': 0}, 'medium': {'total': 0, 'correct': 0}, 'low': {'total': 0, 'correct': 0}}
        by_outcome = {'H': {'total': 0, 'correct': 0}, 'D': {'total': 0, 'correct': 0}, 'A': {'total': 0, 'correct': 0}}

        for pred in predictions:
            match = pred.match
            if match.home_score is None or match.away_score is None:
                continue

            # Determine actual outcome
            if match.home_score > match.away_score:
                actual = 'H'
            elif match.home_score < match.away_score:
                actual = 'A'
            else:
                actual = 'D'

            # Map recommended outcome
            outcome_map = {'HOME': 'H', 'DRAW': 'D', 'AWAY': 'A'}
            predicted = outcome_map.get(pred.recommended_outcome, pred.recommended_outcome)
            is_correct = predicted == actual

            total += 1
            if is_correct:
                correct += 1

            # Track by confidence
            conf = float(pred.confidence_score)
            if conf >= 0.6:
                conf_level = 'high'
            elif conf >= 0.45:
                conf_level = 'medium'
            else:
                conf_level = 'low'

            by_confidence[conf_level]['total'] += 1
            if is_correct:
                by_confidence[conf_level]['correct'] += 1

            # Track by outcome
            if predicted in by_outcome:
                by_outcome[predicted]['total'] += 1
                if is_correct:
                    by_outcome[predicted]['correct'] += 1

        # Calculate accuracies
        overall_accuracy = correct / total if total > 0 else 0

        metrics = {
            'period': 'last_30_days',
            'total_predictions': total,
            'correct_predictions': correct,
            'overall_accuracy': round(overall_accuracy, 4),
            'by_confidence': {},
            'by_outcome': {},
        }

        for level, data in by_confidence.items():
            if data['total'] > 0:
                metrics['by_confidence'][level] = {
                    'total': data['total'],
                    'correct': data['correct'],
                    'accuracy': round(data['correct'] / data['total'], 4)
                }

        for outcome, data in by_outcome.items():
            if data['total'] > 0:
                metrics['by_outcome'][outcome] = {
                    'total': data['total'],
                    'correct': data['correct'],
                    'accuracy': round(data['correct'] / data['total'], 4)
                }

        # Update active model version with new accuracy
        active_model = ModelVersion.objects.filter(is_active=True).first()
        if active_model:
            active_model.accuracy = overall_accuracy
            active_model.save(update_fields=['accuracy'])

        logger.info(f"Model metrics calculated: {overall_accuracy:.1%} accuracy over {total} predictions")

        return {'status': 'success', 'metrics': metrics}

    except Exception as e:
        logger.error(f"Metrics calculation failed: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def calculate_league_metrics(league_code: str):
    """
    Calculate metrics for a specific league.
    """
    logger.info(f"Calculating metrics for league {league_code}...")

    try:
        from apps.predictions.models import Prediction
        from apps.matches.models import Match
        from django.db.models import Count, Q

        predictions = Prediction.objects.filter(
            match__season__league__code=league_code,
            match__status=Match.Status.FINISHED,
            is_correct__isnull=False
        ).aggregate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True))
        )

        total = predictions['total']
        correct = predictions['correct']
        accuracy = correct / total if total > 0 else 0

        return {
            'status': 'success',
            'league': league_code,
            'total': total,
            'correct': correct,
            'accuracy': round(accuracy, 4)
        }

    except Exception as e:
        logger.error(f"League metrics calculation failed: {e}")
        return {'status': 'error', 'message': str(e)}
