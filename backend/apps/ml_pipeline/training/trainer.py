"""
Model Training Module

Handles training of prediction models:
- XGBoost classifiers for match outcome
- XGBoost regressors for goals prediction
- Ensemble combining multiple models
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import pickle
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    TimeSeriesSplit,
    GridSearchCV,
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    log_loss,
    classification_report,
    mean_squared_error,
    mean_absolute_error,
)
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Optional imports
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("xgboost not installed")

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class ModelTrainer:
    """
    Trains prediction models for football match outcomes.

    Supports:
    - Match result prediction (Home/Draw/Away)
    - Total goals prediction
    - Over/Under 2.5 goals
    - Both teams to score (BTTS)
    """

    # Default XGBoost parameters
    DEFAULT_XGB_PARAMS = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 200,
        'min_child_weight': 1,
        'gamma': 0,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 0,
        'reg_lambda': 1,
        'random_state': 42,
        'use_label_encoder': False,
        'eval_metric': 'mlogloss',
    }

    # Parameter grid for tuning
    PARAM_GRID = {
        'max_depth': [4, 6, 8],
        'learning_rate': [0.05, 0.1, 0.15],
        'n_estimators': [100, 200, 300],
        'min_child_weight': [1, 3, 5],
        'subsample': [0.7, 0.8, 0.9],
    }

    def __init__(
        self,
        model_dir: Optional[Path] = None,
        use_gpu: bool = False
    ):
        """
        Initialize the trainer.

        Args:
            model_dir: Directory to save trained models
            use_gpu: Whether to use GPU for training
        """
        self.model_dir = model_dir or Path(settings.BASE_DIR) / 'models'
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.use_gpu = use_gpu
        self.scaler = StandardScaler()
        self.feature_columns = []

        # Model instances
        self.result_model = None
        self.goals_model = None
        self.over25_model = None
        self.btts_model = None

    def train_result_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        tune_hyperparams: bool = False,
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train match result prediction model.

        Args:
            X: Feature DataFrame
            y: Target series (0=home, 1=draw, 2=away)
            tune_hyperparams: Whether to perform hyperparameter tuning
            validation_split: Fraction for validation

        Returns:
            Dict with training metrics
        """
        if not XGB_AVAILABLE:
            raise ImportError("xgboost is required for training")

        logger.info("Training result prediction model...")

        # Store feature columns
        self.feature_columns = list(X.columns)

        # Handle missing values
        X = X.fillna(0)

        # Split data (using time-based split for temporal data)
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=validation_split,
            shuffle=False  # Preserve temporal order
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Get model parameters
        params = self.DEFAULT_XGB_PARAMS.copy()
        if self.use_gpu:
            params['tree_method'] = 'gpu_hist'

        # Hyperparameter tuning
        if tune_hyperparams:
            logger.info("Performing hyperparameter tuning...")
            best_params = self._tune_hyperparameters(X_train_scaled, y_train)
            params.update(best_params)

        # Train model
        self.result_model = xgb.XGBClassifier(**params)
        self.result_model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            verbose=False
        )

        # Evaluate
        y_pred = self.result_model.predict(X_val_scaled)
        y_proba = self.result_model.predict_proba(X_val_scaled)

        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'log_loss': log_loss(y_val, y_proba),
            'train_size': len(X_train),
            'val_size': len(X_val),
            'n_features': len(self.feature_columns),
        }

        # Class-wise metrics
        report = classification_report(y_val, y_pred, output_dict=True)
        metrics['class_report'] = report

        logger.info(f"Result model metrics: Accuracy={metrics['accuracy']:.3f}, LogLoss={metrics['log_loss']:.3f}")

        return metrics

    def train_goals_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train total goals prediction model.

        Args:
            X: Feature DataFrame
            y: Target series (total goals)
            validation_split: Fraction for validation

        Returns:
            Dict with training metrics
        """
        if not XGB_AVAILABLE:
            raise ImportError("xgboost is required for training")

        logger.info("Training goals prediction model...")

        X = X.fillna(0)

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=validation_split,
            shuffle=False
        )

        # Scale
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Configure for regression
        params = {
            'objective': 'reg:squarederror',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
        }

        self.goals_model = xgb.XGBRegressor(**params)
        self.goals_model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            verbose=False
        )

        # Evaluate
        y_pred = self.goals_model.predict(X_val_scaled)

        metrics = {
            'rmse': np.sqrt(mean_squared_error(y_val, y_pred)),
            'mae': mean_absolute_error(y_val, y_pred),
            'train_size': len(X_train),
            'val_size': len(X_val),
        }

        logger.info(f"Goals model metrics: RMSE={metrics['rmse']:.3f}, MAE={metrics['mae']:.3f}")

        return metrics

    def train_over25_model(
        self,
        X: pd.DataFrame,
        y_goals: pd.Series,
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train Over/Under 2.5 goals prediction model.

        Args:
            X: Feature DataFrame
            y_goals: Total goals series
            validation_split: Fraction for validation

        Returns:
            Dict with training metrics
        """
        if not XGB_AVAILABLE:
            raise ImportError("xgboost is required")

        logger.info("Training Over 2.5 model...")

        # Create binary target
        y = (y_goals > 2.5).astype(int)
        X = X.fillna(0)

        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=validation_split,
            shuffle=False
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        params = {
            'objective': 'binary:logistic',
            'max_depth': 5,
            'learning_rate': 0.1,
            'n_estimators': 150,
            'subsample': 0.8,
            'random_state': 42,
            'eval_metric': 'logloss',
        }

        self.over25_model = xgb.XGBClassifier(**params)
        self.over25_model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            verbose=False
        )

        y_pred = self.over25_model.predict(X_val_scaled)
        y_proba = self.over25_model.predict_proba(X_val_scaled)[:, 1]

        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'log_loss': log_loss(y_val, self.over25_model.predict_proba(X_val_scaled)),
            'over_rate': y_train.mean(),
        }

        logger.info(f"Over 2.5 model: Accuracy={metrics['accuracy']:.3f}")

        return metrics

    def _tune_hyperparameters(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv: int = 3
    ) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning with cross-validation.

        Returns:
            Dict of best parameters
        """
        logger.info("Starting hyperparameter search...")

        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            use_label_encoder=False,
            random_state=42,
        )

        # Use TimeSeriesSplit for temporal data
        tscv = TimeSeriesSplit(n_splits=cv)

        search = GridSearchCV(
            model,
            self.PARAM_GRID,
            cv=tscv,
            scoring='neg_log_loss',
            n_jobs=-1,
            verbose=1
        )

        search.fit(X, y)

        logger.info(f"Best params: {search.best_params_}")
        logger.info(f"Best score: {-search.best_score_:.4f}")

        return search.best_params_

    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5
    ) -> Dict[str, Any]:
        """
        Perform time-series cross-validation.

        Returns:
            Dict with CV metrics
        """
        if not XGB_AVAILABLE:
            raise ImportError("xgboost is required")

        X = X.fillna(0)
        X_scaled = self.scaler.fit_transform(X)

        model = xgb.XGBClassifier(**self.DEFAULT_XGB_PARAMS)

        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores = cross_val_score(
            model, X_scaled, y,
            cv=tscv,
            scoring='accuracy'
        )

        return {
            'cv_scores': scores.tolist(),
            'mean_accuracy': scores.mean(),
            'std_accuracy': scores.std(),
        }

    def save_models(
        self,
        version: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Save trained models to disk.

        Args:
            version: Optional version string
            metadata: Optional metadata dict

        Returns:
            Path to saved model directory
        """
        from apps.predictions.models import ModelVersion

        version = version or datetime.now().strftime('%Y%m%d_%H%M%S')
        save_dir = self.model_dir / version
        save_dir.mkdir(parents=True, exist_ok=True)

        # Save models
        if self.result_model:
            with open(save_dir / 'result_model.pkl', 'wb') as f:
                pickle.dump(self.result_model, f)

        if self.goals_model:
            with open(save_dir / 'goals_model.pkl', 'wb') as f:
                pickle.dump(self.goals_model, f)

        if self.over25_model:
            with open(save_dir / 'over25_model.pkl', 'wb') as f:
                pickle.dump(self.over25_model, f)

        # Save scaler
        with open(save_dir / 'scaler.pkl', 'wb') as f:
            pickle.dump(self.scaler, f)

        # Save feature columns
        with open(save_dir / 'features.json', 'w') as f:
            json.dump(self.feature_columns, f)

        # Save metadata
        meta = metadata or {}
        meta.update({
            'version': version,
            'created_at': datetime.now().isoformat(),
            'n_features': len(self.feature_columns),
        })
        with open(save_dir / 'metadata.json', 'w') as f:
            json.dump(meta, f, indent=2)

        # Save to database
        try:
            from django.utils import timezone
            # Deactivate previous versions
            ModelVersion.objects.filter(status=ModelVersion.Status.ACTIVE).update(
                status=ModelVersion.Status.ARCHIVED
            )
            # Create new active version
            ModelVersion.objects.create(
                version=version,
                status=ModelVersion.Status.ACTIVE,
                model_type='ensemble',
                model_path=str(save_dir),
                trained_at=timezone.now(),
                training_samples=meta.get('n_samples', 0),
                training_seasons=meta.get('seasons', []),
                training_leagues=meta.get('leagues', []) or [],
                accuracy=meta.get('accuracy'),
                log_loss=meta.get('log_loss'),
                feature_names=self.feature_columns,
            )
        except Exception as e:
            logger.warning(f"Could not save to database: {e}")

        logger.info(f"Models saved to: {save_dir}")
        return str(save_dir)

    def load_models(self, version: Optional[str] = None) -> bool:
        """
        Load models from disk.

        Args:
            version: Optional version to load (latest if None)

        Returns:
            True if successful
        """
        from apps.predictions.models import ModelVersion

        # Get version path
        if version:
            load_dir = self.model_dir / version
        else:
            # Try to get active version from database
            try:
                active = ModelVersion.objects.filter(status=ModelVersion.Status.ACTIVE).first()
                if active:
                    load_dir = Path(active.model_path)
                else:
                    # Fall back to latest directory
                    versions = sorted(self.model_dir.iterdir())
                    if not versions:
                        logger.error("No saved models found")
                        return False
                    load_dir = versions[-1]
            except Exception:
                versions = sorted(self.model_dir.iterdir())
                if not versions:
                    return False
                load_dir = versions[-1]

        logger.info(f"Loading models from: {load_dir}")

        try:
            # Load models
            if (load_dir / 'result_model.pkl').exists():
                with open(load_dir / 'result_model.pkl', 'rb') as f:
                    self.result_model = pickle.load(f)

            if (load_dir / 'goals_model.pkl').exists():
                with open(load_dir / 'goals_model.pkl', 'rb') as f:
                    self.goals_model = pickle.load(f)

            if (load_dir / 'over25_model.pkl').exists():
                with open(load_dir / 'over25_model.pkl', 'rb') as f:
                    self.over25_model = pickle.load(f)

            # Load scaler
            if (load_dir / 'scaler.pkl').exists():
                with open(load_dir / 'scaler.pkl', 'rb') as f:
                    self.scaler = pickle.load(f)
            else:
                logger.warning("scaler.pkl not found, using default StandardScaler")
                self.scaler = StandardScaler()

            # Load feature columns
            if (load_dir / 'features.json').exists():
                with open(load_dir / 'features.json', 'r') as f:
                    self.feature_columns = json.load(f)
            else:
                logger.warning("features.json not found")
                self.feature_columns = []

            logger.info("Models loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False

    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get feature importance from the result model.

        Returns:
            DataFrame with feature importances
        """
        if not self.result_model:
            raise ValueError("No result model trained")

        importances = self.result_model.feature_importances_

        df = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importances
        })

        return df.sort_values('importance', ascending=False)
