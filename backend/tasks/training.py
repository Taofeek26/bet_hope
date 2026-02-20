"""
Model Training Tasks

Tasks for training and updating ML models
"""
import logging
from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def retrain_model(self):
    """
    Retrain the ML model with latest data.
    Runs daily at 5:00 AM UTC (after data sync).
    """
    logger.info("Starting daily model retraining...")

    try:
        # Train new model version
        call_command(
            'train_model',
            verbosity=1
        )
        logger.info("Model retraining completed successfully")
        return {'status': 'success', 'message': 'Model retrained'}

    except Exception as e:
        logger.error(f"Model retraining failed: {e}")
        raise self.retry(exc=e)


@shared_task
def train_model_for_league(league_code: str):
    """
    Train a model specifically for one league.
    Can be triggered manually for league-specific models.
    """
    logger.info(f"Training model for league {league_code}...")

    try:
        call_command(
            'train_model',
            leagues=[league_code],
            verbosity=1
        )
        return {'status': 'success', 'league': league_code}

    except Exception as e:
        logger.error(f"League-specific training failed: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def evaluate_model():
    """
    Evaluate current model performance.
    Can be triggered manually to check model accuracy.
    """
    logger.info("Evaluating model performance...")

    try:
        from apps.predictions.models import Prediction, ModelVersion
        from apps.matches.models import Match
        from django.db.models import Count, Q

        # Get active model
        active_model = ModelVersion.get_active_version()
        if not active_model:
            return {'status': 'error', 'message': 'No active model found'}

        # Calculate accuracy for recent predictions
        recent_predictions = Prediction.objects.filter(
            match__status=Match.Status.FINISHED,
            is_correct__isnull=False
        ).aggregate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True))
        )

        total = recent_predictions['total']
        correct = recent_predictions['correct']
        accuracy = correct / total if total > 0 else 0

        return {
            'status': 'success',
            'model_version': active_model.version,
            'total_predictions': total,
            'correct_predictions': correct,
            'accuracy': round(accuracy, 4)
        }

    except Exception as e:
        logger.error(f"Model evaluation failed: {e}")
        return {'status': 'error', 'message': str(e)}
