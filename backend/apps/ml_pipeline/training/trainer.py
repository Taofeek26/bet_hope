"""
Model Training Module

Handles training of prediction models:
- XGBoost classifiers for match outcome
- XGBoost regressors for goals prediction
- Ensemble combining multiple models
"""
import os
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
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.calibration import CalibratedClassifierCV

try:
    # sklearn >=1.6 replaced CalibratedClassifierCV(cv='prefit') with
    # wrapping the fitted estimator in FrozenEstimator instead.
    from sklearn.frozen import FrozenEstimator
except ImportError:
    FrozenEstimator = None
from sklearn.metrics import (
    accuracy_score,
    log_loss,
    classification_report,
    mean_squared_error,
    mean_absolute_error,
)

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
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
        self.version = None

        # Model instances
        self.result_model = None
        self.goals_model = None
        self.over25_model = None
        self.btts_model = None

        # Uncalibrated versions, kept for feature_importances_ (a calibrated
        # wrapper doesn't expose it directly)
        self._raw_result_model = None
        self._raw_over25_model = None

    @staticmethod
    def _calibrate(raw_model, X_val: np.ndarray, y_val) -> CalibratedClassifierCV:
        """Wrap an already-fit classifier with probability calibration."""
        method = 'isotonic' if len(X_val) >= 500 else 'sigmoid'
        if FrozenEstimator is not None:
            calibrated = CalibratedClassifierCV(FrozenEstimator(raw_model), method=method)
        else:
            calibrated = CalibratedClassifierCV(estimator=raw_model, method=method, cv='prefit')
        calibrated.fit(X_val, y_val)
        return calibrated

    def train_result_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        sample_weights: Optional[np.ndarray] = None,
        tune_hyperparams: bool = False,
        validation_split: float = 0.2,
        calibrate: bool = True
    ) -> Dict[str, Any]:
        """
        Train match result prediction model.

        Args:
            X: Feature DataFrame
            y: Target series (0=home, 1=draw, 2=away)
            sample_weights: Optional sample weights for weighted training
            tune_hyperparams: Whether to perform hyperparameter tuning
            validation_split: Fraction for validation

        Returns:
            Dict with training metrics
        """
        if not XGB_AVAILABLE:
            raise ImportError("xgboost is required for training")

        logger.info("Training result prediction model...")
        if sample_weights is not None:
            logger.info("Using sample weights for feedback-driven learning")

        # Store feature columns
        self.feature_columns = list(X.columns)

        # Handle missing values
        X = X.fillna(0)

        # Split data (using time-based split for temporal data)
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        # Split weights if provided
        weights_train = None
        if sample_weights is not None:
            weights_train = sample_weights[:split_idx]

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

        # Train model with optional sample weights
        self.result_model = xgb.XGBClassifier(**params)
        self.result_model.fit(
            X_train_scaled, y_train,
            sample_weight=weights_train,
            eval_set=[(X_val_scaled, y_val)],
            verbose=False
        )
        self._raw_result_model = self.result_model

        # Calibrate probabilities against the held-out validation split (not
        # used for training) — raw XGBoost predict_proba tends to be
        # overconfident, which matters directly for a betting app where the
        # displayed percentage is the product. cv='prefit' wraps the already
        # -fit model rather than retraining. Isotonic needs more data to
        # avoid overfitting than sigmoid/Platt, so pick by validation size.
        calibrated = False
        if calibrate and len(X_val) >= 30:
            self.result_model = self._calibrate(self._raw_result_model, X_val_scaled, y_val)
            calibrated = True

        # Evaluate (using final — possibly calibrated — model)
        y_pred = self.result_model.predict(X_val_scaled)
        y_proba = self.result_model.predict_proba(X_val_scaled)

        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'log_loss': log_loss(y_val, y_proba),
            'train_size': len(X_train),
            'val_size': len(X_val),
            'n_features': len(self.feature_columns),
            'used_sample_weights': sample_weights is not None,
            'calibrated': calibrated,
        }

        # Class-wise metrics
        report = classification_report(y_val, y_pred, output_dict=True)
        metrics['class_report'] = report

        logger.info(f"Result model metrics: Accuracy={metrics['accuracy']:.3f}, LogLoss={metrics['log_loss']:.3f}, Calibrated={calibrated}")

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
        validation_split: float = 0.2,
        calibrate: bool = True
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
        self._raw_over25_model = self.over25_model

        calibrated = False
        if calibrate and len(X_val) >= 30:
            self.over25_model = self._calibrate(self._raw_over25_model, X_val_scaled, y_val)
            calibrated = True

        y_pred = self.over25_model.predict(X_val_scaled)
        y_proba_full = self.over25_model.predict_proba(X_val_scaled)

        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'log_loss': log_loss(y_val, y_proba_full),
            'over_rate': y_train.mean(),
            'calibrated': calibrated,
        }

        logger.info(f"Over 2.5 model: Accuracy={metrics['accuracy']:.3f}, Calibrated={calibrated}")

        return metrics

    def _tune_hyperparameters(
        self,
        X: np.ndarray,
        y: pd.Series,
        cv: int = 3,
        n_trials: int = 30
    ) -> Dict[str, Any]:
        """
        Hyperparameter search via Optuna's TPE sampler over time-series CV
        folds. Replaces the previous GridSearchCV grid, which only checked
        a small fixed set of combinations — TPE explores a wider continuous
        space and concentrates trials around what's working.

        Returns:
            Dict of best parameters
        """
        if not OPTUNA_AVAILABLE:
            logger.warning("optuna not installed, skipping hyperparameter tuning")
            return {}

        logger.info(f"Starting Optuna hyperparameter search ({n_trials} trials)...")

        tscv = TimeSeriesSplit(n_splits=cv)
        y_arr = y.reset_index(drop=True) if hasattr(y, 'reset_index') else pd.Series(y)

        def objective(trial: 'optuna.Trial') -> float:
            params = {
                'objective': 'multi:softprob',
                'num_class': 3,
                'random_state': 42,
                'use_label_encoder': False,
                'eval_metric': 'mlogloss',
                'max_depth': trial.suggest_int('max_depth', 3, 9),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 100, 500, step=50),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 8),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True),
            }

            fold_scores = []
            for train_idx, val_idx in tscv.split(X):
                model = xgb.XGBClassifier(**params)
                model.fit(X[train_idx], y_arr.iloc[train_idx])
                proba = model.predict_proba(X[val_idx])
                fold_scores.append(log_loss(y_arr.iloc[val_idx], proba, labels=[0, 1, 2]))

            return float(np.mean(fold_scores))

        study = optuna.create_study(
            direction='minimize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

        logger.info(f"Best params: {study.best_params}")
        logger.info(f"Best log_loss: {study.best_value:.4f}")

        return study.best_params

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

        # Persist to S3 too — /tmp (where save_dir lives on Lambda) is wiped
        # between cold starts, so local disk alone isn't durable there.
        if os.getenv('S3_MODEL_BUCKET'):
            try:
                from apps.ml_pipeline.storage import S3ModelStorage
                S3ModelStorage().upload_artifacts(str(save_dir), version)
            except Exception as e:
                logger.warning(f"Could not upload models to S3: {e}")

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

        # /tmp (where load_dir lives on Lambda) is wiped between cold
        # starts — if it's not there locally, pull it from S3 first.
        if not load_dir.exists() and os.getenv('S3_MODEL_BUCKET'):
            try:
                from apps.ml_pipeline.storage import S3ModelStorage
                version_name = load_dir.name
                downloaded = S3ModelStorage().download_artifacts(version_name, str(load_dir))
                logger.info(f"Downloaded models from S3: {downloaded}")
            except Exception as e:
                logger.error(f"Could not download models from S3: {e}")
                return False

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

            self.version = load_dir.name
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

        if self._raw_result_model is not None:
            importances = self._raw_result_model.feature_importances_
        elif isinstance(self.result_model, CalibratedClassifierCV):
            # Calibration wraps the base estimator (possibly inside a
            # FrozenEstimator, which proxies attribute access) — there's
            # only ever one inner estimator here since we always calibrate
            # a single already-fit model, not cross-validated folds.
            inner = self.result_model.calibrated_classifiers_[0].estimator
            importances = getattr(inner, 'feature_importances_', None)
            if importances is None:
                importances = inner.estimator.feature_importances_
        else:
            importances = self.result_model.feature_importances_

        df = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importances
        })

        return df.sort_values('importance', ascending=False)
