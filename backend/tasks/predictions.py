"""
Prediction Tasks

Tasks for generating and validating predictions
"""
import logging
from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_predictions(self):
    """
    Generate predictions for upcoming matches.
    Runs every 6 hours to catch new fixtures.
    """
    logger.info("Generating predictions for upcoming matches...")

    try:
        call_command(
            'generate_predictions',
            upcoming=True,
            days=14,  # Predict 2 weeks ahead
            verbosity=1
        )
        logger.info("Prediction generation completed successfully")
        return {'status': 'success', 'message': 'Predictions generated'}

    except Exception as e:
        logger.error(f"Prediction generation failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def validate_predictions(self):
    """
    Validate predictions against actual match results.
    Runs daily at 6:00 AM UTC.
    """
    logger.info("Validating predictions against results...")

    try:
        call_command(
            'generate_predictions',
            validate=True,
            verbosity=1
        )
        logger.info("Prediction validation completed successfully")
        return {'status': 'success', 'message': 'Predictions validated'}

    except Exception as e:
        logger.error(f"Prediction validation failed: {e}")
        raise self.retry(exc=e)


@shared_task
def generate_prediction_for_match(match_id: int):
    """
    Generate prediction for a specific match.
    Can be triggered manually or on-demand via API.
    """
    logger.info(f"Generating prediction for match {match_id}...")

    try:
        from apps.matches.models import Match
        from apps.predictions.models import Prediction
        from apps.ml_pipeline.inference.predictor import MatchPredictor
        from decimal import Decimal

        match = Match.objects.select_related(
            'home_team', 'away_team', 'season'
        ).get(id=match_id)

        predictor = MatchPredictor()
        if not predictor.load_model():
            return {'status': 'error', 'message': 'Failed to load model'}

        prediction_data = predictor.predict_match(
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
            match_date=match.match_date,
            season_code=match.season.code,
        )

        if 'error' in prediction_data:
            return {'status': 'error', 'message': prediction_data['error']}

        # Save prediction
        pred, created = Prediction.objects.update_or_create(
            match=match,
            defaults={
                'model_version': predictor.model_version or 'current',
                'home_win_probability': Decimal(str(prediction_data.get('home_win_prob', 0.33))),
                'draw_probability': Decimal(str(prediction_data.get('draw_prob', 0.33))),
                'away_win_probability': Decimal(str(prediction_data.get('away_win_prob', 0.33))),
                'confidence_score': Decimal(str(prediction_data.get('confidence', 0.4))),
                'model_type': 'xgboost',
            }
        )

        return {
            'status': 'success',
            'match_id': match_id,
            'prediction_id': pred.id,
            'created': created
        }

    except Match.DoesNotExist:
        return {'status': 'error', 'message': f'Match {match_id} not found'}
    except Exception as e:
        logger.error(f"Single prediction failed: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def regenerate_all_predictions():
    """
    Regenerate all predictions using current model.
    Use with caution - clears existing predictions.
    """
    logger.info("Regenerating all predictions...")

    try:
        call_command(
            'generate_predictions',
            upcoming=True,
            historical=True,
            clear=True,
            verbosity=1
        )
        return {'status': 'success', 'message': 'All predictions regenerated'}

    except Exception as e:
        logger.error(f"Prediction regeneration failed: {e}")
        return {'status': 'error', 'message': str(e)}
