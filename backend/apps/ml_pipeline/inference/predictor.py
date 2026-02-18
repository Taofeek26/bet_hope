"""
Match Predictor

Production inference module for generating match predictions.
Loads trained models and generates predictions for upcoming matches.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class MatchPredictor:
    """
    Production predictor for match outcomes.

    Handles:
    - Model loading and management
    - Feature extraction for prediction
    - Prediction generation
    - Saving predictions to database
    """

    def __init__(self, model_version: Optional[str] = None):
        """
        Initialize the predictor.

        Args:
            model_version: Optional specific model version to load
        """
        from apps.ml_pipeline.features import FeatureExtractor
        from apps.ml_pipeline.training import ModelTrainer

        self.feature_extractor = FeatureExtractor()
        self.trainer = ModelTrainer()

        self.model_loaded = False
        self.model_version = model_version

    def load_model(self, version: Optional[str] = None) -> bool:
        """
        Load prediction model.

        Args:
            version: Optional version to load

        Returns:
            True if successful
        """
        version = version or self.model_version
        success = self.trainer.load_models(version)

        if success:
            self.model_loaded = True
            logger.info(f"Model loaded successfully")
        else:
            logger.error("Failed to load model")

        return success

    def predict_match(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: date,
        season_code: Optional[str] = None,
        save_to_db: bool = False,
        match_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate prediction for a single match.

        Args:
            home_team_id: Home team database ID
            away_team_id: Away team database ID
            match_date: Date of the match
            season_code: Optional season code
            save_to_db: Whether to save prediction to database
            match_id: Optional match ID for database save

        Returns:
            Dict with prediction results
        """
        if not self.model_loaded:
            if not self.load_model():
                return {'error': 'Model not loaded'}

        # Extract features
        features = self.feature_extractor.extract_match_features(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            match_date=match_date,
            season_code=season_code
        )

        if not features:
            return {'error': 'Failed to extract features'}

        # Prepare feature vector
        X = self._prepare_features(features)

        # Generate predictions
        prediction = self._predict(X)

        # Add metadata
        prediction['home_team_id'] = home_team_id
        prediction['away_team_id'] = away_team_id
        prediction['match_date'] = match_date.isoformat()
        prediction['predicted_at'] = timezone.now().isoformat()
        prediction['model_version'] = self.trainer.feature_columns[:5] if self.trainer.feature_columns else None

        # Save to database if requested
        if save_to_db and match_id:
            self._save_prediction(match_id, prediction)

        return prediction

    def predict_batch(
        self,
        matches: List[Dict[str, Any]],
        save_to_db: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generate predictions for multiple matches.

        Args:
            matches: List of match dicts with required fields
            save_to_db: Whether to save predictions

        Returns:
            List of prediction dicts
        """
        if not self.model_loaded:
            if not self.load_model():
                return [{'error': 'Model not loaded'}]

        predictions = []

        for match in matches:
            try:
                pred = self.predict_match(
                    home_team_id=match['home_team_id'],
                    away_team_id=match['away_team_id'],
                    match_date=match['match_date'],
                    season_code=match.get('season_code'),
                    save_to_db=save_to_db,
                    match_id=match.get('match_id')
                )
                pred['match_id'] = match.get('match_id')
                predictions.append(pred)

            except Exception as e:
                logger.error(f"Prediction error for match: {e}")
                predictions.append({
                    'match_id': match.get('match_id'),
                    'error': str(e)
                })

        return predictions

    def predict_upcoming(
        self,
        days_ahead: int = 7,
        league_codes: Optional[List[str]] = None,
        save_to_db: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate predictions for all upcoming matches.

        Args:
            days_ahead: Number of days to look ahead
            league_codes: Optional filter by leagues
            save_to_db: Whether to save predictions

        Returns:
            List of predictions
        """
        from apps.matches.models import Match
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        end_date = today + timedelta(days=days_ahead)

        # Get upcoming matches
        matches_query = Match.objects.filter(
            match_date__gte=today,
            match_date__lte=end_date,
            status=Match.Status.SCHEDULED,
        ).select_related('home_team', 'away_team', 'season')

        if league_codes:
            matches_query = matches_query.filter(
                season__league__code__in=league_codes
            )

        matches = []
        for match in matches_query:
            matches.append({
                'match_id': match.id,
                'home_team_id': match.home_team_id,
                'away_team_id': match.away_team_id,
                'match_date': match.match_date,
                'season_code': match.season.code,
            })

        logger.info(f"Generating predictions for {len(matches)} upcoming matches")

        return self.predict_batch(matches, save_to_db=save_to_db)

    def _prepare_features(self, features: Dict[str, float]) -> np.ndarray:
        """
        Prepare feature vector for prediction.

        Ensures features are in correct order and handles missing values.
        """
        # Get expected feature columns
        expected_cols = self.trainer.feature_columns

        # Build feature vector in correct order
        feature_vector = []
        for col in expected_cols:
            value = features.get(col, 0.0)
            if pd.isna(value):
                value = 0.0
            feature_vector.append(value)

        X = np.array([feature_vector])

        # Scale features
        X_scaled = self.trainer.scaler.transform(X)

        return X_scaled

    def _predict(self, X: np.ndarray) -> Dict[str, Any]:
        """
        Run prediction through models.

        Returns:
            Dict with prediction results
        """
        result = {}

        # Result prediction (Home/Draw/Away)
        if self.trainer.result_model:
            proba = self.trainer.result_model.predict_proba(X)[0]
            pred_class = np.argmax(proba)

            result['home_win_prob'] = float(proba[0])
            result['draw_prob'] = float(proba[1])
            result['away_win_prob'] = float(proba[2])

            result['predicted_outcome'] = ['H', 'D', 'A'][pred_class]
            result['confidence'] = float(proba[pred_class])

            # Risk assessment
            result['risk_level'] = self._assess_risk(proba)

        # Goals prediction
        if self.trainer.goals_model:
            goals_pred = self.trainer.goals_model.predict(X)[0]
            result['predicted_total_goals'] = float(goals_pred)

        # Over 2.5 prediction
        if self.trainer.over25_model:
            over_proba = self.trainer.over25_model.predict_proba(X)[0]
            result['over_25_prob'] = float(over_proba[1])
            result['under_25_prob'] = float(over_proba[0])

        # Calculate value bets
        result['value_bets'] = self._calculate_value_bets(result)

        return result

    def _assess_risk(self, probabilities: np.ndarray) -> str:
        """
        Assess prediction risk based on probability distribution.

        Returns:
            Risk level: 'low', 'medium', or 'high'
        """
        max_prob = probabilities.max()

        if max_prob >= 0.6:
            return 'low'
        elif max_prob >= 0.45:
            return 'medium'
        else:
            return 'high'

    def _calculate_value_bets(
        self,
        prediction: Dict[str, Any],
        margin: float = 0.05
    ) -> List[Dict[str, Any]]:
        """
        Calculate potential value bets based on prediction vs market.

        Args:
            prediction: Prediction dict with probabilities
            margin: Minimum edge required

        Returns:
            List of value bet opportunities
        """
        value_bets = []

        # This would typically compare with actual market odds
        # For now, we identify high-confidence predictions

        outcomes = [
            ('home_win', prediction.get('home_win_prob', 0)),
            ('draw', prediction.get('draw_prob', 0)),
            ('away_win', prediction.get('away_win_prob', 0)),
        ]

        for outcome, prob in outcomes:
            if prob > 0.5 + margin:  # High confidence
                # Calculate fair odds
                fair_odds = 1.0 / prob if prob > 0 else 0
                value_bets.append({
                    'market': outcome,
                    'probability': prob,
                    'fair_odds': round(fair_odds, 2),
                    'confidence': 'high' if prob > 0.6 else 'medium',
                })

        # Over/Under
        over_prob = prediction.get('over_25_prob', 0)
        if over_prob > 0.55:
            value_bets.append({
                'market': 'over_2.5',
                'probability': over_prob,
                'fair_odds': round(1.0 / over_prob, 2) if over_prob > 0 else 0,
                'confidence': 'high' if over_prob > 0.65 else 'medium',
            })
        elif over_prob < 0.45:
            value_bets.append({
                'market': 'under_2.5',
                'probability': 1 - over_prob,
                'fair_odds': round(1.0 / (1 - over_prob), 2) if over_prob < 1 else 0,
                'confidence': 'high' if over_prob < 0.35 else 'medium',
            })

        return value_bets

    def _save_prediction(
        self,
        match_id: int,
        prediction: Dict[str, Any]
    ):
        """Save prediction to database."""
        from apps.predictions.models import Prediction, ModelVersion
        from apps.matches.models import Match

        try:
            match = Match.objects.get(id=match_id)

            # Get active model version
            model_version = ModelVersion.objects.filter(is_active=True).first()

            Prediction.objects.update_or_create(
                match=match,
                defaults={
                    'model_version': model_version,
                    'home_win_prob': Decimal(str(prediction.get('home_win_prob', 0))),
                    'draw_prob': Decimal(str(prediction.get('draw_prob', 0))),
                    'away_win_prob': Decimal(str(prediction.get('away_win_prob', 0))),
                    'over_25_prob': Decimal(str(prediction.get('over_25_prob', 0))),
                    'predicted_outcome': prediction.get('predicted_outcome'),
                    'confidence': Decimal(str(prediction.get('confidence', 0))),
                    'predicted_total_goals': Decimal(str(prediction.get('predicted_total_goals', 0))),
                }
            )

            logger.debug(f"Saved prediction for match {match_id}")

        except Match.DoesNotExist:
            logger.error(f"Match {match_id} not found")
        except Exception as e:
            logger.error(f"Error saving prediction: {e}")

    def get_prediction_summary(
        self,
        match_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get formatted prediction summary for display.

        Args:
            match_id: Match ID

        Returns:
            Formatted prediction dict or None
        """
        from apps.predictions.models import Prediction
        from apps.matches.models import Match

        try:
            prediction = Prediction.objects.select_related(
                'match__home_team',
                'match__away_team'
            ).get(match_id=match_id)

            return {
                'match': {
                    'id': match_id,
                    'home_team': prediction.match.home_team.name,
                    'away_team': prediction.match.away_team.name,
                    'date': prediction.match.match_date.isoformat(),
                },
                'prediction': {
                    'outcome': prediction.predicted_outcome,
                    'confidence': float(prediction.confidence),
                    'probabilities': {
                        'home': float(prediction.home_win_prob),
                        'draw': float(prediction.draw_prob),
                        'away': float(prediction.away_win_prob),
                    },
                    'total_goals': float(prediction.predicted_total_goals),
                    'over_25': float(prediction.over_25_prob),
                },
                'predicted_at': prediction.created_at.isoformat(),
            }

        except Prediction.DoesNotExist:
            return None


# Celery task for batch predictions
from celery import shared_task


@shared_task(bind=True)
def generate_predictions_task(
    self,
    days_ahead: int = 7,
    league_codes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Celery task to generate predictions for upcoming matches.

    Args:
        days_ahead: Number of days to look ahead
        league_codes: Optional league filter

    Returns:
        Dict with task results
    """
    predictor = MatchPredictor()

    predictions = predictor.predict_upcoming(
        days_ahead=days_ahead,
        league_codes=league_codes,
        save_to_db=True
    )

    successful = sum(1 for p in predictions if 'error' not in p)
    failed = sum(1 for p in predictions if 'error' in p)

    return {
        'total': len(predictions),
        'successful': successful,
        'failed': failed,
        'generated_at': timezone.now().isoformat(),
    }


@shared_task(bind=True)
def retrain_model_task(
    self,
    season_codes: Optional[List[str]] = None,
    tune_hyperparams: bool = False
) -> Dict[str, Any]:
    """
    Celery task to retrain the prediction model.

    Args:
        season_codes: Seasons to train on
        tune_hyperparams: Whether to tune hyperparameters

    Returns:
        Dict with training results
    """
    from apps.ml_pipeline.features import FeatureExtractor
    from apps.ml_pipeline.training import ModelTrainer

    logger.info("Starting model retraining...")

    # Default to recent seasons
    season_codes = season_codes or ['2324', '2223', '2122', '2021', '1920']

    # Build training data
    extractor = FeatureExtractor()
    X, y_result, y_goals = extractor.build_training_data(
        season_codes=season_codes
    )

    if X.empty:
        return {'error': 'No training data available'}

    # Train models
    trainer = ModelTrainer()

    result_metrics = trainer.train_result_model(
        X, y_result,
        tune_hyperparams=tune_hyperparams
    )

    goals_metrics = trainer.train_goals_model(X, y_goals)
    over25_metrics = trainer.train_over25_model(X, y_goals)

    # Save models
    version = trainer.save_models(metadata={
        'result_accuracy': result_metrics.get('accuracy'),
        'seasons': season_codes,
    })

    return {
        'version': version,
        'result_metrics': result_metrics,
        'goals_metrics': goals_metrics,
        'over25_metrics': over25_metrics,
        'trained_at': timezone.now().isoformat(),
    }
