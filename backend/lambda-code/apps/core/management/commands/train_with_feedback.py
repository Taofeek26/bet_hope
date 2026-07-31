"""
Train ML models with feedback-driven learning.

This command trains models using prediction outcomes to improve accuracy.
It weights samples based on:
- Time decay (recent matches more important)
- Prediction errors (wrong predictions weighted higher for learning)
"""
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Train ML models with feedback from past prediction outcomes'

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
            '--no-feedback',
            action='store_true',
            help='Disable prediction feedback weighting',
        )
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze prediction errors, do not retrain',
        )
        parser.add_argument(
            '--model-version',
            type=str,
            default=None,
            help='Model version string',
        )

    def handle(self, *args, **options):
        from apps.ml_pipeline.feedback import FeedbackTrainer
        from apps.ml_pipeline.training.trainer import ModelTrainer
        from apps.matches.models import Match

        seasons = options['seasons']
        leagues = options['leagues']
        tune = options['tune']
        version = options.get('model_version')
        use_feedback = not options['no_feedback']
        analyze_only = options['analyze_only']

        # Initialize feedback trainer
        feedback_trainer = FeedbackTrainer()

        # Analyze prediction errors first
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=== Prediction Error Analysis ==='))
        analysis = feedback_trainer.analyze_prediction_errors(days=30)

        if analysis['status'] == 'success':
            self.stdout.write(f"Period: Last {analysis['period_days']} days")
            self.stdout.write(f"Total predictions: {analysis['total_predictions']}")
            self.stdout.write(f"Correct: {analysis['correct_predictions']}")
            self.stdout.write(f"Overall accuracy: {analysis['overall_accuracy']:.1%}")

            self.stdout.write('')
            self.stdout.write('By Outcome:')
            for outcome, stats in analysis['by_outcome'].items():
                self.stdout.write(f"  {outcome}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1%})")

            self.stdout.write('')
            self.stdout.write('By Confidence:')
            for level, stats in analysis['by_confidence'].items():
                self.stdout.write(f"  {level}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1%})")

            self.stdout.write('')
            self.stdout.write('Recommendations:')
            for rec in analysis['recommendations']:
                self.stdout.write(f"  - {rec}")
        else:
            self.stdout.write(self.style.WARNING('No prediction data available for analysis'))

        if analyze_only:
            return

        # Build weighted training data
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=== Building Training Dataset ==='))
        self.stdout.write(f'Seasons: {seasons}')
        if leagues:
            self.stdout.write(f'Leagues: {leagues}')
        self.stdout.write(f'Using prediction feedback: {use_feedback}')

        X, y_result, y_goals, weights = feedback_trainer.build_weighted_training_data(
            season_codes=seasons,
            league_codes=leagues,
            include_prediction_feedback=use_feedback
        )

        self.stdout.write(self.style.SUCCESS(f'Built dataset: {len(X)} samples, {len(X.columns)} features'))
        self.stdout.write(f'Sample weight range: {weights.min():.3f} - {weights.max():.3f}')

        # Check data quality
        if len(X) < 100:
            self.stdout.write(self.style.ERROR('Not enough data for training (need at least 100 matches)'))
            return

        # Train models with feedback weights
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=== Training Models ==='))

        trainer = ModelTrainer()

        # Train result model with sample weights
        self.stdout.write('Training match result model (with feedback weights)...')
        result_metrics = trainer.train_result_model(
            X, y_result,
            sample_weights=weights if use_feedback else None,
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
            'used_feedback_learning': use_feedback,
            'training_type': 'feedback_weighted' if use_feedback else 'standard',
        }
        save_path = trainer.save_models(version=version, metadata=metadata)
        self.stdout.write(self.style.SUCCESS(f'Models saved to: {save_path}'))

        # Feature importance
        self.stdout.write('')
        self.stdout.write('Top 10 important features:')
        importance = trainer.get_feature_importance()
        for _, row in importance.head(10).iterrows():
            self.stdout.write(f'  {row["feature"]}: {row["importance"]:.4f}')

        # Show hard negatives for review
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=== Top 5 Hard Negatives (for review) ==='))
        hard_negatives = feedback_trainer.get_hard_negatives(limit=5)
        for neg in hard_negatives:
            self.stdout.write(
                f"  {neg['home_team']} vs {neg['away_team']} ({neg['date']}): "
                f"Predicted {neg['predicted']} ({neg['confidence']:.0%}) -> Actual {neg['actual']}"
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Feedback-driven training complete!'))
