"""
Train ML model from exported data (for GitHub Actions training).
"""
import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Train ML model from exported JSON data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            type=str,
            required=True,
            help='Input JSON file with training data',
        )
        parser.add_argument(
            '--model-version',
            type=str,
            default=None,
            help='Model version (default: timestamp)',
        )

    def handle(self, *args, **options):
        import numpy as np
        import pandas as pd
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from xgboost import XGBClassifier, XGBRegressor
        import joblib

        input_path = options['input']
        version = options['model_version'] or datetime.now().strftime('%Y%m%d_%H%M%S')

        self.stdout.write(f'Loading training data from {input_path}...')

        # Load exported data
        with open(input_path, 'r') as f:
            data = json.load(f)

        matches = data['matches']
        self.stdout.write(f'Loaded {len(matches)} matches')

        # Convert to DataFrame
        df = pd.DataFrame(matches)

        # Feature engineering
        self.stdout.write('Engineering features...')
        features = self._engineer_features(df)

        # Prepare targets
        # Result: 0 = Away, 1 = Draw, 2 = Home
        df['result'] = df.apply(
            lambda x: 2 if x['home_score'] > x['away_score']
            else (1 if x['home_score'] == x['away_score'] else 0),
            axis=1
        )
        df['total_goals'] = df['home_score'] + df['away_score']
        df['over_25'] = (df['total_goals'] > 2.5).astype(int)

        # Filter valid rows
        valid_mask = features.notna().all(axis=1)
        X = features[valid_mask].values
        y_result = df.loc[valid_mask, 'result'].values
        y_goals = df.loc[valid_mask, 'total_goals'].values
        y_over25 = df.loc[valid_mask, 'over_25'].values

        self.stdout.write(f'Training on {len(X)} samples with {X.shape[1]} features')

        # Split data
        X_train, X_test, y_train_result, y_test_result = train_test_split(
            X, y_result, test_size=0.2, random_state=42
        )
        _, _, y_train_goals, y_test_goals = train_test_split(
            X, y_goals, test_size=0.2, random_state=42
        )
        _, _, y_train_over25, y_test_over25 = train_test_split(
            X, y_over25, test_size=0.2, random_state=42
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train models
        self.stdout.write('Training result prediction model...')
        result_model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
        )
        result_model.fit(X_train_scaled, y_train_result)
        result_accuracy = result_model.score(X_test_scaled, y_test_result)
        self.stdout.write(f'  Result accuracy: {result_accuracy:.4f}')

        self.stdout.write('Training goals prediction model...')
        goals_model = XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
        )
        goals_model.fit(X_train_scaled, y_train_goals)

        self.stdout.write('Training over 2.5 goals model...')
        over25_model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
        )
        over25_model.fit(X_train_scaled, y_train_over25)
        over25_accuracy = over25_model.score(X_test_scaled, y_test_over25)
        self.stdout.write(f'  Over 2.5 accuracy: {over25_accuracy:.4f}')

        # Save models
        model_dir = os.path.join(settings.BASE_DIR, 'models', version)
        os.makedirs(model_dir, exist_ok=True)

        joblib.dump(scaler, os.path.join(model_dir, 'scaler.pkl'))
        joblib.dump(result_model, os.path.join(model_dir, 'result_model.pkl'))
        joblib.dump(goals_model, os.path.join(model_dir, 'goals_model.pkl'))
        joblib.dump(over25_model, os.path.join(model_dir, 'over25_model.pkl'))

        # Save metadata
        metadata = {
            'version': version,
            'trained_at': datetime.now().isoformat(),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'features': list(features.columns),
            'metrics': {
                'result_accuracy': float(result_accuracy),
                'over25_accuracy': float(over25_accuracy),
            }
        }

        with open(os.path.join(model_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)

        # Save features list
        with open(os.path.join(model_dir, 'features.json'), 'w') as f:
            json.dump(list(features.columns), f, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f'Model v{version} trained successfully!\n'
            f'  - Result accuracy: {result_accuracy:.4f}\n'
            f'  - Over 2.5 accuracy: {over25_accuracy:.4f}\n'
            f'  - Saved to: {model_dir}'
        ))

    def _engineer_features(self, df):
        """Engineer features from match data."""
        features = pd.DataFrame()

        # Parse home_stats and away_stats from dict columns
        for prefix, stats_col in [('home', 'home_stats'), ('away', 'away_stats')]:
            if stats_col in df.columns:
                # Extract nested dict values
                for stat in ['wins', 'draws', 'losses', 'goals_for', 'goals_against']:
                    features[f'{prefix}_{stat}'] = df[stats_col].apply(
                        lambda x: x.get(stat, 0) if isinstance(x, dict) else 0
                    )

                # Calculate derived features
                played = features[f'{prefix}_wins'] + features[f'{prefix}_draws'] + features[f'{prefix}_losses']
                played = played.replace(0, 1)  # Avoid division by zero

                features[f'{prefix}_ppg'] = (
                    features[f'{prefix}_wins'] * 3 + features[f'{prefix}_draws']
                ) / played

                features[f'{prefix}_goals_per_game'] = features[f'{prefix}_goals_for'] / played
                features[f'{prefix}_conceded_per_game'] = features[f'{prefix}_goals_against'] / played
                features[f'{prefix}_goal_diff'] = features[f'{prefix}_goals_for'] - features[f'{prefix}_goals_against']

        # Add odds features if available
        if 'odds' in df.columns:
            features['odds_home'] = df['odds'].apply(
                lambda x: x.get('home', 2.5) if isinstance(x, dict) and x.get('home') else 2.5
            )
            features['odds_draw'] = df['odds'].apply(
                lambda x: x.get('draw', 3.5) if isinstance(x, dict) and x.get('draw') else 3.5
            )
            features['odds_away'] = df['odds'].apply(
                lambda x: x.get('away', 3.0) if isinstance(x, dict) and x.get('away') else 3.0
            )

            # Implied probabilities
            features['implied_home'] = 1 / features['odds_home']
            features['implied_draw'] = 1 / features['odds_draw']
            features['implied_away'] = 1 / features['odds_away']

        # Fill NaN with defaults
        features = features.fillna(0)

        return features
