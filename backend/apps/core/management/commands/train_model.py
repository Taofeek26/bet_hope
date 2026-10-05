"""
Train ML prediction models using historical match data.
"""
import json
import logging
import os
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Train ML prediction models using historical match data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seasons',
            nargs='+',
            default=None,  # None = current season + the 4 before it (apps.core.seasons)
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
        parser.add_argument(
            '--engine',
            choices=['v2', 'v1'],
            default='v2',
            help='v2 (default, Phase 3): point-in-time features, market correction, '
                 'promotion check. v1: the original pipeline.',
        )
        parser.add_argument(
            '--force-promote',
            action='store_true',
            help='v2: make the new model active even if it does not beat the current one',
        )

    def handle_v2(self, options):
        from datetime import datetime
        from django.utils import timezone
        from apps.ml_pipeline.v2.features import build_features, labels, load_matches
        from apps.ml_pipeline.v2.model import ModelV2, load_version, metrics, model_dir
        from apps.predictions.models import ModelVersion

        version = options.get('model_version') or 'v2_' + datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        df = load_matches()
        X = build_features(df)
        self.stdout.write(f'Built features for {len(df)} matches')
        model = ModelV2.train(df, X)
        meta = model.meta
        t, b = meta['test'], (meta['baselines'] or {}).get('bookmaker')
        self.stdout.write(f"Windows: {meta['windows']}  samples: {meta['samples']}")
        self.stdout.write(f"Test (unseen): accuracy {t['accuracy']:.4f}  log loss {t['log_loss']:.4f}  rps {t['rps']:.4f}")
        if b:
            self.stdout.write(f"Bookmaker on the same matches: accuracy {b['accuracy']:.4f}  log loss {b['log_loss']:.4f}")
        for row in meta['calibration']:
            self.stdout.write(f"  confidence {row['band']}: n={row['n']}  predicted {row['predicted']:.3f}  actual {row['actual']:.3f}")

        # Promotion check (ML-04): beat the active model on the SAME test window
        active = ModelVersion.get_active_version()
        promote, reason = True, 'no active model'
        if active and not options.get('force_promote'):
            if active.model_type == 'v2':
                try:
                    old = load_version(active.version)
                    y = labels(df)[0]
                    idx = model._test_index
                    old_p = old.predict(X.loc[idx])[['p_home', 'p_draw', 'p_away']].values
                    old_ll = metrics(old_p, y.loc[idx].values)['log_loss']
                    promote = t['log_loss'] <= old_ll + 1e-4
                    reason = f"new {t['log_loss']:.4f} vs active {active.version} {old_ll:.4f} on the same window"
                except Exception as e:
                    promote, reason = True, f'active model could not be scored ({e}); replacing it'
            else:
                old_ll = float(active.log_loss) if active.log_loss is not None else 99
                promote = t['log_loss'] < old_ll
                reason = f"new {t['log_loss']:.4f} vs v1 {active.version} self-reported {old_ll:.4f}"
        elif options.get('force_promote'):
            reason = '--force-promote'
        meta['promotion'] = {'promoted': promote, 'reason': reason}

        d = model_dir(version)
        model.save(d)
        location = str(d)
        if os.getenv('S3_MODEL_BUCKET'):
            from apps.ml_pipeline.storage import S3ModelStorage
            location = S3ModelStorage().upload_artifacts(str(d), version)

        if promote:
            ModelVersion.objects.filter(status=ModelVersion.Status.ACTIVE).update(status=ModelVersion.Status.ARCHIVED)
        ModelVersion.objects.create(
            version=version,
            status=ModelVersion.Status.ACTIVE if promote else ModelVersion.Status.ARCHIVED,
            model_type='v2', model_path=location, trained_at=timezone.now(),
            training_samples=meta['samples']['train'],
            accuracy=round(t['accuracy'], 4), log_loss=round(t['log_loss'], 6), brier_score=round(t['brier'], 6),
            feature_names=meta['features'], hyperparameters=meta['best_iterations'],
            notes=json.dumps({k: meta[k] for k in ('windows', 'samples', 'test', 'baselines', 'promotion', 'over25')}),
        )
        self.stdout.write(self.style.SUCCESS(
            f"Saved {version} ({'ACTIVE' if promote else 'archived, not promoted'}): {reason}"))

    def handle(self, *args, **options):
        if options.get('engine', 'v2') == 'v2':
            return self.handle_v2(options)
        from apps.ml_pipeline.features.feature_extractor import FeatureExtractor
        from apps.ml_pipeline.training.trainer import ModelTrainer
        from apps.matches.models import Match

        from apps.core.seasons import recent_season_codes
        seasons = options['seasons'] or recent_season_codes(5)
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
