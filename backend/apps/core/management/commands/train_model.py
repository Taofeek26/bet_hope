"""
Train ML prediction models using historical match data.
"""
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Train ML prediction models using historical match data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seasons',
            nargs='+',
            default=['2526', '2425', '2324', '2223', '2122'],
            help='Season codes to use for training',
        )
        parser.add_argument(
            '--leagues',
            nargs='+',
            default=None,
            help='League codes to include (default: all)',
        )
        parser.add_argument(
            '--tune',
            action='store_true',
            help='Perform hyperparameter tuning (slower)',
        )
        parser.add_argument(
            '--model-version',
            type=str,
            default=None,
            help='Model version string',
        )

    def handle(self, *args, **options):
        from apps.ml_pipeline.features.feature_extractor import FeatureExtractor
        from apps.ml_pipeline.training.trainer import ModelTrainer
        from apps.matches.models import Match

        seasons = options['seasons']
        leagues = options['leagues']
        tune = options['tune']
        version = options.get('model_version')

        self.stdout.write(f'Training with seasons: {seasons}')
        if leagues:
            self.stdout.write(f'Filtering to leagues: {leagues}')

        # Check available data
        match_count = Match.objects.filter(
            season__code__in=seasons,
            status=Match.Status.FINISHED
        ).count()
        self.stdout.write(f'Found {match_count} finished matches for training')

        if match_count < 100:
            self.stdout.write(self.style.ERROR('Not enough data for training (need at least 100 matches)'))
            return

        # Build training dataset
        self.stdout.write('')
        self.stdout.write('Building training dataset...')
        extractor = FeatureExtractor(use_cache=True)

        X, y_result, y_goals = extractor.build_training_data(
            season_codes=seasons,
            league_codes=leagues,
            use_disk_cache=True
        )

        self.stdout.write(self.style.SUCCESS(f'Built dataset: {len(X)} samples, {len(X.columns)} features'))

        # Train models
        self.stdout.write('')
        self.stdout.write('Training match result model...')
        trainer = ModelTrainer()

        result_metrics = trainer.train_result_model(
            X, y_result,
            tune_hyperparams=tune
        )
        self.stdout.write(f'  Accuracy: {result_metrics["accuracy"]:.3f}')
        self.stdout.write(f'  Log Loss: {result_metrics["log_loss"]:.3f}')

        # Train goals model
        self.stdout.write('')
        self.stdout.write('Training goals prediction model...')
        goals_metrics = trainer.train_goals_model(X, y_goals)
        self.stdout.write(f'  RMSE: {goals_metrics["rmse"]:.3f}')
        self.stdout.write(f'  MAE: {goals_metrics["mae"]:.3f}')

        # Train over 2.5 model
        self.stdout.write('')
        self.stdout.write('Training Over 2.5 goals model...')
        over25_metrics = trainer.train_over25_model(X, y_goals)
        self.stdout.write(f'  Accuracy: {over25_metrics["accuracy"]:.3f}')

        # Save models
        self.stdout.write('')
        self.stdout.write('Saving models...')
        metadata = {
            'seasons': seasons,
            'leagues': leagues,
            'n_samples': len(X),
            'accuracy': result_metrics['accuracy'],
            'log_loss': result_metrics['log_loss'],
        }
        save_path = trainer.save_models(version=version, metadata=metadata)
        self.stdout.write(self.style.SUCCESS(f'Models saved to: {save_path}'))

        # Feature importance
        self.stdout.write('')
        self.stdout.write('Top 10 important features:')
        importance = trainer.get_feature_importance()
        for _, row in importance.head(10).iterrows():
            self.stdout.write(f'  {row["feature"]}: {row["importance"]:.4f}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Training complete!'))
