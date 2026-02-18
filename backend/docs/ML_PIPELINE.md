# Bet_Hope Machine Learning Pipeline

## Overview

The ML pipeline transforms raw match data into probability predictions using ensemble methods.

---

## Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          TRAINING PIPELINE                                 │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Raw Data  │───►│   Feature   │───►│   Model     │───►│  Calibrated │
│  Extraction │    │ Engineering │    │  Training   │    │   Model     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼
  PostgreSQL         Feature          XGBoost +          Model
    Queries          Matrix           Hyperopt          Registry

┌────────────────────────────────────────────────────────────────────────────┐
│                         INFERENCE PIPELINE                                 │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Upcoming  │───►│   Feature   │───►│   Model     │───►│ Predictions │
│   Matches   │    │  Generation │    │  Inference  │    │    API      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Feature Engineering

### Feature Categories

#### 1. Form Features

Recent performance metrics calculated over rolling windows.

```python
FORM_FEATURES = {
    # Last N matches performance
    'points_last_5': 'Points earned in last 5 matches',
    'points_last_10': 'Points earned in last 10 matches',
    'wins_last_5': 'Wins in last 5 matches',
    'draws_last_5': 'Draws in last 5 matches',
    'losses_last_5': 'Losses in last 5 matches',

    # Goals
    'goals_scored_avg_5': 'Average goals scored (last 5)',
    'goals_conceded_avg_5': 'Average goals conceded (last 5)',
    'goals_scored_avg_10': 'Average goals scored (last 10)',
    'goals_conceded_avg_10': 'Average goals conceded (last 10)',

    # Clean sheets
    'clean_sheets_last_5': 'Clean sheets in last 5 matches',
    'failed_to_score_last_5': 'Matches without scoring (last 5)',

    # Streaks
    'current_win_streak': 'Consecutive wins',
    'current_unbeaten_streak': 'Matches without loss',
    'current_winless_streak': 'Matches without win',
}
```

**Implementation:**

```python
def calculate_form_features(team_id: int, match_date: date, n_matches: int = 5) -> dict:
    """
    Calculate form features for a team before a specific match.
    """
    recent_matches = Match.objects.filter(
        Q(home_team_id=team_id) | Q(away_team_id=team_id),
        match_date__lt=match_date,
        status='finished'
    ).order_by('-match_date')[:n_matches]

    features = {
        'points': 0,
        'wins': 0,
        'draws': 0,
        'losses': 0,
        'goals_scored': 0,
        'goals_conceded': 0,
        'clean_sheets': 0,
        'failed_to_score': 0,
    }

    for match in recent_matches:
        is_home = match.home_team_id == team_id
        team_score = match.home_score if is_home else match.away_score
        opponent_score = match.away_score if is_home else match.home_score

        features['goals_scored'] += team_score
        features['goals_conceded'] += opponent_score

        if opponent_score == 0:
            features['clean_sheets'] += 1
        if team_score == 0:
            features['failed_to_score'] += 1

        if team_score > opponent_score:
            features['points'] += 3
            features['wins'] += 1
        elif team_score == opponent_score:
            features['points'] += 1
            features['draws'] += 1
        else:
            features['losses'] += 1

    n = len(recent_matches)
    return {
        f'points_last_{n_matches}': features['points'],
        f'wins_last_{n_matches}': features['wins'],
        f'goals_scored_avg_{n_matches}': features['goals_scored'] / n if n > 0 else 0,
        f'goals_conceded_avg_{n_matches}': features['goals_conceded'] / n if n > 0 else 0,
        f'clean_sheets_last_{n_matches}': features['clean_sheets'],
        f'failed_to_score_last_{n_matches}': features['failed_to_score'],
    }
```

---

#### 2. Home/Away Split Features

Performance differences based on venue.

```python
HOME_AWAY_FEATURES = {
    # Home team - home performance
    'home_team_home_win_rate': 'Home team win % at home',
    'home_team_home_goals_avg': 'Home team avg goals at home',
    'home_team_home_conceded_avg': 'Home team avg conceded at home',
    'home_team_home_points_avg': 'Home team avg points at home',

    # Away team - away performance
    'away_team_away_win_rate': 'Away team win % away',
    'away_team_away_goals_avg': 'Away team avg goals away',
    'away_team_away_conceded_avg': 'Away team avg conceded away',
    'away_team_away_points_avg': 'Away team avg points away',

    # Differentials
    'home_advantage_diff': 'Home team home form vs Away team away form',
}
```

---

#### 3. Head-to-Head Features

Historical record between the two teams.

```python
H2H_FEATURES = {
    'h2h_total_matches': 'Total previous meetings',
    'h2h_home_team_wins': 'Home team wins in H2H',
    'h2h_away_team_wins': 'Away team wins in H2H',
    'h2h_draws': 'Draws in H2H',
    'h2h_home_team_win_rate': 'Home team H2H win percentage',
    'h2h_avg_goals': 'Average total goals in H2H',
    'h2h_last_5_home_wins': 'Home team wins in last 5 H2H',
    'h2h_home_venue_record': 'Home team record at this venue vs opponent',
}
```

**Implementation:**

```python
def calculate_h2h_features(
    home_team_id: int,
    away_team_id: int,
    match_date: date
) -> dict:
    """
    Calculate head-to-head features between two teams.
    """
    h2h_matches = Match.objects.filter(
        Q(home_team_id=home_team_id, away_team_id=away_team_id) |
        Q(home_team_id=away_team_id, away_team_id=home_team_id),
        match_date__lt=match_date,
        status='finished'
    ).order_by('-match_date')[:20]  # Last 20 meetings

    home_wins = 0
    away_wins = 0
    draws = 0
    total_goals = 0

    for match in h2h_matches:
        total_goals += match.home_score + match.away_score

        if match.home_team_id == home_team_id:
            # This match was at same venue
            if match.home_score > match.away_score:
                home_wins += 1
            elif match.home_score < match.away_score:
                away_wins += 1
            else:
                draws += 1
        else:
            # Reversed fixture
            if match.home_score > match.away_score:
                away_wins += 1
            elif match.home_score < match.away_score:
                home_wins += 1
            else:
                draws += 1

    total = len(h2h_matches)
    return {
        'h2h_total_matches': total,
        'h2h_home_team_wins': home_wins,
        'h2h_away_team_wins': away_wins,
        'h2h_draws': draws,
        'h2h_home_team_win_rate': home_wins / total if total > 0 else 0.33,
        'h2h_avg_goals': total_goals / total if total > 0 else 2.5,
    }
```

---

#### 4. League Position Features

Current standings-based features.

```python
POSITION_FEATURES = {
    'home_team_position': 'Home team league position',
    'away_team_position': 'Away team league position',
    'position_difference': 'Home position - Away position',
    'home_team_points': 'Home team total points',
    'away_team_points': 'Away team total points',
    'points_difference': 'Points gap between teams',
    'home_team_goal_diff': 'Home team goal difference',
    'away_team_goal_diff': 'Away team goal difference',

    # Relative position
    'home_in_top_4': 'Home team in Champions League spots',
    'away_in_top_4': 'Away team in Champions League spots',
    'home_in_relegation': 'Home team in relegation zone',
    'away_in_relegation': 'Away team in relegation zone',
}
```

---

#### 5. Advanced Metrics Features

xG and other advanced statistics.

```python
ADVANCED_FEATURES = {
    'home_team_xg_avg': 'Home team average xG',
    'away_team_xg_avg': 'Away team average xG',
    'home_team_xga_avg': 'Home team average xG against',
    'away_team_xga_avg': 'Away team average xG against',
    'home_team_xg_diff': 'Home team xG - xGA',
    'away_team_xg_diff': 'Away team xG - xGA',

    # Shot quality
    'home_team_shots_avg': 'Home team avg shots per game',
    'away_team_shots_avg': 'Away team avg shots per game',
    'home_team_sot_avg': 'Home team avg shots on target',
    'away_team_sot_avg': 'Away team avg shots on target',
}
```

---

#### 6. Player Availability Features

Squad strength factors.

```python
PLAYER_FEATURES = {
    'home_team_injuries': 'Number of injured players (home)',
    'away_team_injuries': 'Number of injured players (away)',
    'home_team_suspensions': 'Number of suspended players (home)',
    'away_team_suspensions': 'Number of suspended players (away)',
    'home_key_player_out': 'Key player unavailable (home)',
    'away_key_player_out': 'Key player unavailable (away)',
    'home_squad_value': 'Total squad market value (home)',
    'away_squad_value': 'Total squad market value (away)',
}
```

---

#### 7. Contextual Features

Match context and timing.

```python
CONTEXTUAL_FEATURES = {
    'is_home': 'Binary: 1 for home team perspective',
    'matchweek': 'Current matchweek number',
    'season_progress': 'Percentage of season completed',
    'days_since_last_match_home': 'Rest days for home team',
    'days_since_last_match_away': 'Rest days for away team',
    'rest_advantage': 'Rest days difference',
    'is_derby': 'Local rivalry match',
    'is_title_decider': 'Important match for title',
    'is_relegation_battle': 'Both teams in relegation zone',
}
```

---

#### 8. Document AI Features

Signals from text analysis.

```python
DOCUMENT_FEATURES = {
    'home_team_news_sentiment': 'Sentiment from recent news (home)',
    'away_team_news_sentiment': 'Sentiment from recent news (away)',
    'injury_report_severity_home': 'Injury news severity score (home)',
    'injury_report_severity_away': 'Injury news severity score (away)',
    'manager_confidence_home': 'Manager quotes sentiment (home)',
    'manager_confidence_away': 'Manager quotes sentiment (away)',
}
```

---

### Feature Matrix Generation

```python
class FeatureGenerator:
    """
    Generates complete feature matrix for model training/inference.
    """

    def __init__(self):
        self.feature_functions = [
            self._form_features,
            self._home_away_features,
            self._h2h_features,
            self._position_features,
            self._advanced_features,
            self._player_features,
            self._contextual_features,
        ]

    def generate_features(self, match: Match) -> dict:
        """
        Generate all features for a single match.
        """
        features = {}

        # Home team features
        for func in self.feature_functions:
            home_features = func(
                team_id=match.home_team_id,
                match_date=match.match_date,
                prefix='home_'
            )
            features.update(home_features)

        # Away team features
        for func in self.feature_functions:
            away_features = func(
                team_id=match.away_team_id,
                match_date=match.match_date,
                prefix='away_'
            )
            features.update(away_features)

        # H2H features (special case)
        h2h = self._h2h_features(
            match.home_team_id,
            match.away_team_id,
            match.match_date
        )
        features.update(h2h)

        # Contextual features
        context = self._contextual_features(match)
        features.update(context)

        return features

    def generate_training_matrix(
        self,
        start_date: date,
        end_date: date,
        leagues: list[int] = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate feature matrix X and target vector y for training.
        """
        matches = Match.objects.filter(
            match_date__gte=start_date,
            match_date__lte=end_date,
            status='finished'
        )

        if leagues:
            matches = matches.filter(league_id__in=leagues)

        X_data = []
        y_data = []

        for match in matches:
            try:
                features = self.generate_features(match)
                X_data.append(features)

                # Target: 0=Home Win, 1=Draw, 2=Away Win
                if match.home_score > match.away_score:
                    y_data.append(0)
                elif match.home_score == match.away_score:
                    y_data.append(1)
                else:
                    y_data.append(2)
            except Exception as e:
                logger.warning(f"Feature generation failed for match {match.id}: {e}")
                continue

        return self._to_matrix(X_data), np.array(y_data)

    def _to_matrix(self, feature_dicts: list[dict]) -> np.ndarray:
        """
        Convert list of feature dictionaries to numpy matrix.
        """
        df = pd.DataFrame(feature_dicts)
        return df.values
```

---

## Model Training

### XGBoost Configuration

```python
XGBOOST_CONFIG = {
    # Base parameters
    'objective': 'multi:softprob',
    'num_class': 3,
    'eval_metric': 'mlogloss',

    # Tree parameters
    'max_depth': 6,
    'min_child_weight': 1,
    'gamma': 0.1,

    # Learning parameters
    'learning_rate': 0.05,
    'n_estimators': 500,

    # Regularization
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,

    # Sampling
    'subsample': 0.8,
    'colsample_bytree': 0.8,

    # Other
    'random_state': 42,
    'n_jobs': -1,
    'early_stopping_rounds': 50,
}
```

### Hyperparameter Tuning

Using Optuna for hyperparameter optimization.

```python
import optuna
from sklearn.model_selection import TimeSeriesSplit

def objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 0.0, 0.5),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),
    }

    # Time-based cross-validation
    tscv = TimeSeriesSplit(n_splits=5)
    scores = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = xgb.XGBClassifier(**params, objective='multi:softprob', num_class=3)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

        y_pred_proba = model.predict_proba(X_val)
        score = log_loss(y_val, y_pred_proba)
        scores.append(score)

    return np.mean(scores)

# Run optimization
study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=100)

best_params = study.best_params
```

### Training Pipeline

```python
class ModelTrainer:
    """
    Handles model training, evaluation, and persistence.
    """

    def __init__(self, config: dict = None):
        self.config = config or XGBOOST_CONFIG
        self.feature_generator = FeatureGenerator()
        self.scaler = StandardScaler()
        self.model = None

    def train(
        self,
        start_date: date,
        end_date: date,
        leagues: list[int] = None,
        test_size: float = 0.2
    ) -> dict:
        """
        Train model on historical data.
        """
        # Generate features
        X, y = self.feature_generator.generate_training_matrix(
            start_date, end_date, leagues
        )

        # Time-based split (last 20% for testing)
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        self.model = xgb.XGBClassifier(**self.config)
        self.model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=True
        )

        # Calibrate probabilities
        self.calibrator = CalibratedClassifierCV(
            self.model, method='isotonic', cv='prefit'
        )
        self.calibrator.fit(X_test_scaled, y_test)

        # Evaluate
        metrics = self.evaluate(X_test_scaled, y_test)

        # Save model
        version = self.save_model()

        return {
            'version': version,
            'metrics': metrics,
            'feature_importance': self.get_feature_importance()
        }

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Calculate evaluation metrics.
        """
        y_pred = self.model.predict(X)
        y_pred_proba = self.calibrator.predict_proba(X)

        return {
            'accuracy': accuracy_score(y, y_pred),
            'log_loss': log_loss(y, y_pred_proba),
            'brier_score': self._brier_score(y, y_pred_proba),
            'confusion_matrix': confusion_matrix(y, y_pred).tolist(),
            'classification_report': classification_report(y, y_pred, output_dict=True),
        }

    def _brier_score(self, y_true: np.ndarray, y_proba: np.ndarray) -> float:
        """
        Calculate multi-class Brier score.
        """
        y_onehot = np.zeros((len(y_true), 3))
        y_onehot[np.arange(len(y_true)), y_true] = 1
        return np.mean(np.sum((y_proba - y_onehot) ** 2, axis=1))

    def get_feature_importance(self) -> dict:
        """
        Get feature importance scores.
        """
        importance = self.model.feature_importances_
        feature_names = self.feature_generator.get_feature_names()
        return dict(sorted(
            zip(feature_names, importance),
            key=lambda x: x[1],
            reverse=True
        ))

    def save_model(self) -> str:
        """
        Save model to artifacts directory.
        """
        version = datetime.now().strftime('%Y%m%d_%H%M%S')

        artifact_dir = Path(f'ml/artifacts/{version}')
        artifact_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, artifact_dir / 'model.joblib')
        joblib.dump(self.scaler, artifact_dir / 'scaler.joblib')
        joblib.dump(self.calibrator, artifact_dir / 'calibrator.joblib')

        # Save metadata
        metadata = {
            'version': version,
            'created_at': datetime.now().isoformat(),
            'config': self.config,
            'feature_names': self.feature_generator.get_feature_names(),
        }
        with open(artifact_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)

        return version
```

---

## Model Inference

### Predictor Class

```python
class MatchPredictor:
    """
    Generates predictions for upcoming matches.
    """

    def __init__(self, model_version: str = 'latest'):
        self.model_version = model_version
        self._load_model()
        self.feature_generator = FeatureGenerator()

    def _load_model(self):
        """
        Load model artifacts from disk.
        """
        if self.model_version == 'latest':
            artifact_dir = self._get_latest_model_dir()
        else:
            artifact_dir = Path(f'ml/artifacts/{self.model_version}')

        self.model = joblib.load(artifact_dir / 'model.joblib')
        self.scaler = joblib.load(artifact_dir / 'scaler.joblib')
        self.calibrator = joblib.load(artifact_dir / 'calibrator.joblib')

        with open(artifact_dir / 'metadata.json') as f:
            self.metadata = json.load(f)

    def predict(self, match: Match) -> dict:
        """
        Generate prediction for a single match.
        """
        # Generate features
        features = self.feature_generator.generate_features(match)
        X = np.array([list(features.values())])

        # Scale
        X_scaled = self.scaler.transform(X)

        # Predict probabilities
        proba = self.calibrator.predict_proba(X_scaled)[0]

        # Calculate confidence
        confidence = self._calculate_confidence(proba)

        # Determine recommended outcome
        outcomes = ['HOME', 'DRAW', 'AWAY']
        recommended = outcomes[np.argmax(proba)]

        # Get key factors
        key_factors = self._explain_prediction(features, match)

        return {
            'match_id': match.id,
            'home_win_probability': round(float(proba[0]), 4),
            'draw_probability': round(float(proba[1]), 4),
            'away_win_probability': round(float(proba[2]), 4),
            'confidence_score': round(confidence, 4),
            'recommended_outcome': recommended,
            'prediction_strength': self._get_strength(confidence),
            'key_factors': key_factors,
            'model_version': self.model_version,
        }

    def predict_batch(self, matches: list[Match]) -> list[dict]:
        """
        Generate predictions for multiple matches.
        """
        return [self.predict(match) for match in matches]

    def _calculate_confidence(self, proba: np.ndarray) -> float:
        """
        Calculate confidence score based on probability distribution.

        Higher confidence when:
        - One outcome has high probability
        - Distribution is skewed (not uniform)
        """
        max_prob = np.max(proba)
        entropy = -np.sum(proba * np.log(proba + 1e-10))
        max_entropy = -np.log(1/3)  # Maximum entropy for 3 classes

        # Combine max probability and low entropy
        confidence = 0.5 * max_prob + 0.5 * (1 - entropy / max_entropy)

        return confidence

    def _get_strength(self, confidence: float) -> str:
        """
        Categorize prediction strength.
        """
        if confidence >= 0.7:
            return 'STRONG'
        elif confidence >= 0.55:
            return 'MODERATE'
        else:
            return 'WEAK'

    def _explain_prediction(self, features: dict, match: Match) -> list[str]:
        """
        Generate human-readable explanation factors.
        """
        factors = []

        # Form factors
        home_form = features.get('home_points_last_5', 0)
        away_form = features.get('away_points_last_5', 0)

        if home_form >= 12:
            factors.append(f"{match.home_team.name} excellent form (W{features.get('home_wins_last_5', 0)})")
        if away_form <= 5:
            factors.append(f"{match.away_team.name} poor away form")

        # H2H factors
        h2h_home_wins = features.get('h2h_home_team_wins', 0)
        h2h_total = features.get('h2h_total_matches', 0)
        if h2h_total >= 5 and h2h_home_wins / h2h_total > 0.5:
            factors.append(f"H2H favors {match.home_team.name}")

        # Position factors
        pos_diff = features.get('position_difference', 0)
        if abs(pos_diff) >= 10:
            higher = match.home_team.name if pos_diff < 0 else match.away_team.name
            factors.append(f"{higher} significantly higher in table")

        # Injuries
        home_injuries = features.get('home_team_injuries', 0)
        away_injuries = features.get('away_team_injuries', 0)
        if home_injuries >= 3:
            factors.append(f"{match.home_team.name} has {home_injuries} injuries")
        if away_injuries >= 3:
            factors.append(f"{match.away_team.name} has {away_injuries} injuries")

        return factors[:5]  # Return top 5 factors
```

---

## Model Evaluation Framework

### Metrics Tracked

```python
EVALUATION_METRICS = {
    'accuracy': 'Overall prediction accuracy',
    'log_loss': 'Logarithmic loss (lower is better)',
    'brier_score': 'Brier score for probability calibration',

    # By outcome
    'home_accuracy': 'Accuracy for home win predictions',
    'draw_accuracy': 'Accuracy for draw predictions',
    'away_accuracy': 'Accuracy for away win predictions',

    # ROI metrics
    'roi_flat_stake': 'ROI with flat unit stakes',
    'roi_kelly': 'ROI with Kelly criterion stakes',

    # Calibration
    'calibration_error': 'Expected calibration error',
}
```

### Continuous Evaluation

```python
def evaluate_model_performance(
    model_version: str,
    evaluation_period_days: int = 30
) -> dict:
    """
    Evaluate model performance over recent predictions.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=evaluation_period_days)

    # Get predictions with actual results
    predictions = Prediction.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        match__status='finished',
        model_version=model_version
    ).select_related('match')

    if not predictions:
        return None

    y_true = []
    y_pred = []
    y_proba = []

    for pred in predictions:
        match = pred.match

        # Actual outcome
        if match.home_score > match.away_score:
            actual = 0
        elif match.home_score == match.away_score:
            actual = 1
        else:
            actual = 2
        y_true.append(actual)

        # Predicted outcome
        proba = [pred.home_win_probability, pred.draw_probability, pred.away_win_probability]
        y_pred.append(np.argmax(proba))
        y_proba.append(proba)

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    y_proba = np.array(y_proba)

    return {
        'total_predictions': len(predictions),
        'accuracy': accuracy_score(y_true, y_pred),
        'log_loss': log_loss(y_true, y_proba),
        'brier_score': brier_score_multiclass(y_true, y_proba),
        'home_accuracy': calculate_outcome_accuracy(y_true, y_pred, 0),
        'draw_accuracy': calculate_outcome_accuracy(y_true, y_pred, 1),
        'away_accuracy': calculate_outcome_accuracy(y_true, y_pred, 2),
    }
```

---

## Celery Tasks

### Daily Training Task

```python
from celery import shared_task

@shared_task
def retrain_model():
    """
    Daily model retraining task.
    """
    logger.info("Starting model retraining...")

    trainer = ModelTrainer()

    # Train on last 3 seasons
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=365 * 3)

    result = trainer.train(
        start_date=start_date,
        end_date=end_date,
        test_size=0.2
    )

    # Log metrics
    logger.info(f"Model {result['version']} trained - Accuracy: {result['metrics']['accuracy']:.4f}")

    # Store metrics in database
    ModelMetrics.objects.create(
        model_version=result['version'],
        evaluation_date=date.today(),
        **result['metrics']
    )

    return result['version']
```

### Prediction Generation Task

```python
@shared_task
def generate_predictions():
    """
    Generate predictions for upcoming matches.
    """
    predictor = MatchPredictor(model_version='latest')

    # Get upcoming matches (next 7 days)
    upcoming = Match.objects.filter(
        match_date__gte=date.today(),
        match_date__lte=date.today() + timedelta(days=7),
        status='scheduled'
    ).exclude(
        predictions__isnull=False  # Skip already predicted
    )

    predictions_created = 0

    for match in upcoming:
        try:
            pred_data = predictor.predict(match)

            Prediction.objects.create(
                match=match,
                home_win_probability=pred_data['home_win_probability'],
                draw_probability=pred_data['draw_probability'],
                away_win_probability=pred_data['away_win_probability'],
                confidence_score=pred_data['confidence_score'],
                recommended_outcome=pred_data['recommended_outcome'],
                model_version=pred_data['model_version'],
                key_factors=pred_data['key_factors'],
            )
            predictions_created += 1

        except Exception as e:
            logger.error(f"Failed to predict match {match.id}: {e}")

    logger.info(f"Generated {predictions_created} predictions")
    return predictions_created
```

---

## Model Registry

### Version Management

```python
class ModelRegistry:
    """
    Manages model versions and deployment.
    """

    def __init__(self, artifacts_dir: str = 'ml/artifacts'):
        self.artifacts_dir = Path(artifacts_dir)

    def list_versions(self) -> list[dict]:
        """
        List all available model versions.
        """
        versions = []
        for path in sorted(self.artifacts_dir.iterdir(), reverse=True):
            if path.is_dir():
                metadata_path = path / 'metadata.json'
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    versions.append(metadata)
        return versions

    def get_latest_version(self) -> str:
        """
        Get the most recent model version.
        """
        versions = self.list_versions()
        return versions[0]['version'] if versions else None

    def promote_to_production(self, version: str):
        """
        Mark a model version as production.
        """
        prod_link = self.artifacts_dir / 'production'
        if prod_link.exists():
            prod_link.unlink()
        prod_link.symlink_to(version)

    def rollback(self, version: str):
        """
        Rollback to a previous model version.
        """
        self.promote_to_production(version)
```

---

## Performance Benchmarks

### Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Overall Accuracy | >65% | TBD |
| Home Win Accuracy | >70% | TBD |
| Draw Accuracy | >35% | TBD |
| Away Win Accuracy | >60% | TBD |
| Log Loss | <0.95 | TBD |
| Brier Score | <0.20 | TBD |

### Baseline Comparisons

| Model | Accuracy | Log Loss |
|-------|----------|----------|
| Always Home | ~46% | 1.20 |
| Random | ~33% | 1.10 |
| Betting Odds | ~52% | 0.98 |
| **Bet_Hope v1** | Target >55% | <0.95 |
