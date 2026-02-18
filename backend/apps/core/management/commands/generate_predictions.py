"""
Generate predictions using trained ML model

This command:
1. Uses the trained XGBoost model to generate real predictions
2. Validates predictions against actual results for finished matches
3. Updates prediction accuracy statistics
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate predictions using trained ML model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--upcoming',
            action='store_true',
            help='Generate predictions for upcoming matches only',
        )
        parser.add_argument(
            '--historical',
            action='store_true',
            help='Regenerate predictions for historical matches (for validation)',
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate existing predictions against actual results',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing predictions before generating new ones',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look ahead for upcoming matches (default: 30)',
        )
        parser.add_argument(
            '--seasons',
            nargs='+',
            default=None,
            help='Season codes for historical prediction generation',
        )

    def handle(self, *args, **options):
        from apps.predictions.models import Prediction, ModelVersion
        from apps.matches.models import Match
        from apps.ml_pipeline.inference.predictor import MatchPredictor

        upcoming = options.get('upcoming', False)
        historical = options.get('historical', False)
        validate = options.get('validate', False)
        clear = options.get('clear', False)
        days = options.get('days', 30)
        seasons = options.get('seasons')

        # Check for trained model
        active_model = ModelVersion.get_active_version()
        if not active_model:
            self.stdout.write(self.style.WARNING(
                'No active ML model found. Run "python manage.py train_model" first.'
            ))
            self.stdout.write('Falling back to simplified predictions...')
            self._generate_simple_predictions(upcoming, historical, seasons, days, clear)
            if validate:
                self._validate_predictions()
            return

        self.stdout.write(f'Using ML model: {active_model.version} (Accuracy: {active_model.accuracy})')

        if clear:
            self.stdout.write('Clearing existing predictions...')
            Prediction.objects.all().delete()

        # Initialize predictor
        predictor = MatchPredictor()
        if not predictor.load_model():
            self.stdout.write(self.style.ERROR('Failed to load ML model'))
            return

        if upcoming or (not historical and not validate):
            self._generate_upcoming_predictions(predictor, days)

        if historical:
            self._generate_historical_predictions(predictor, seasons)

        if validate:
            self._validate_predictions()

    def _generate_upcoming_predictions(self, predictor, days):
        """Generate predictions for upcoming matches using ML model."""
        from apps.matches.models import Match
        from apps.predictions.models import Prediction

        today = timezone.now().date()
        end_date = today + timedelta(days=days)

        matches = Match.objects.filter(
            match_date__gte=today,
            match_date__lte=end_date,
            status=Match.Status.SCHEDULED,
        ).select_related('home_team', 'away_team', 'season')

        self.stdout.write(f'Generating predictions for {matches.count()} upcoming matches...')

        created = 0
        updated = 0
        errors = 0

        for match in matches:
            try:
                prediction_data = predictor.predict_match(
                    home_team_id=match.home_team_id,
                    away_team_id=match.away_team_id,
                    match_date=match.match_date,
                    season_code=match.season.code,
                )

                if 'error' in prediction_data:
                    errors += 1
                    continue

                obj, was_created = Prediction.objects.update_or_create(
                    match=match,
                    defaults={
                        'model_version': predictor.model_version or 'current',
                        'home_win_probability': Decimal(str(prediction_data.get('home_win_prob', 0.33))),
                        'draw_probability': Decimal(str(prediction_data.get('draw_prob', 0.33))),
                        'away_win_probability': Decimal(str(prediction_data.get('away_win_prob', 0.33))),
                        'predicted_home_score': Decimal(str(prediction_data.get('predicted_total_goals', 2.5) * 0.55)),
                        'predicted_away_score': Decimal(str(prediction_data.get('predicted_total_goals', 2.5) * 0.45)),
                        'confidence_score': Decimal(str(prediction_data.get('confidence', 0.4))),
                        'model_type': 'xgboost',
                        'key_factors': prediction_data.get('value_bets', []),
                    }
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                logger.error(f"Error predicting match {match.id}: {e}")
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f'Upcoming predictions: {created} created, {updated} updated, {errors} errors'
        ))

    def _generate_historical_predictions(self, predictor, seasons):
        """Generate predictions for historical matches."""
        from apps.matches.models import Match
        from apps.predictions.models import Prediction

        query = Match.objects.filter(
            status=Match.Status.FINISHED
        ).select_related('home_team', 'away_team', 'season')

        if seasons:
            query = query.filter(season__code__in=seasons)
        else:
            # Default to current season
            query = query.filter(season__code='2526')

        # Only matches without predictions
        query = query.exclude(predictions__isnull=False)

        self.stdout.write(f'Generating predictions for {query.count()} historical matches...')

        created = 0
        errors = 0

        for match in query:
            try:
                prediction_data = predictor.predict_match(
                    home_team_id=match.home_team_id,
                    away_team_id=match.away_team_id,
                    match_date=match.match_date,
                    season_code=match.season.code,
                )

                if 'error' in prediction_data:
                    errors += 1
                    continue

                Prediction.objects.create(
                    match=match,
                    model_version=predictor.model_version or 'current',
                    home_win_probability=Decimal(str(prediction_data.get('home_win_prob', 0.33))),
                    draw_probability=Decimal(str(prediction_data.get('draw_prob', 0.33))),
                    away_win_probability=Decimal(str(prediction_data.get('away_win_prob', 0.33))),
                    predicted_home_score=Decimal(str(prediction_data.get('predicted_total_goals', 2.5) * 0.55)),
                    predicted_away_score=Decimal(str(prediction_data.get('predicted_total_goals', 2.5) * 0.45)),
                    confidence_score=Decimal(str(prediction_data.get('confidence', 0.4))),
                    model_type='xgboost',
                    key_factors=prediction_data.get('value_bets', []),
                )
                created += 1

            except Exception as e:
                logger.error(f"Error predicting match {match.id}: {e}")
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f'Historical predictions: {created} created, {errors} errors'
        ))

    def _generate_simple_predictions(self, upcoming, historical, seasons, days, clear):
        """Generate simplified predictions without ML model (fallback)."""
        from apps.matches.models import Match
        from apps.predictions.models import Prediction
        from decimal import Decimal

        if clear:
            Prediction.objects.all().delete()

        # Get matches to predict
        today = timezone.now().date()

        if upcoming:
            query = Match.objects.filter(
                match_date__gte=today,
                match_date__lte=today + timedelta(days=days),
            )
        elif historical:
            query = Match.objects.filter(status=Match.Status.FINISHED)
            if seasons:
                query = query.filter(season__code__in=seasons)
        else:
            query = Match.objects.all()

        # Exclude matches with predictions
        query = query.exclude(predictions__isnull=False)
        query = query.select_related('home_team', 'away_team', 'season')

        self.stdout.write(f'Generating simple predictions for {query.count()} matches...')

        created = 0
        for match in query:
            # Use historical stats to estimate probabilities
            home_prob, draw_prob, away_prob = self._estimate_probabilities(match)

            confidence = max(home_prob, draw_prob, away_prob)

            try:
                Prediction.objects.create(
                    match=match,
                    model_version='simple_v1',
                    home_win_probability=Decimal(str(home_prob)),
                    draw_probability=Decimal(str(draw_prob)),
                    away_win_probability=Decimal(str(away_prob)),
                    predicted_home_score=Decimal('1.50'),
                    predicted_away_score=Decimal('1.20'),
                    confidence_score=Decimal(str(confidence)),
                    model_type='statistical',
                    key_factors=[
                        {'factor': 'Home advantage', 'impact': 'positive'},
                        {'factor': 'Historical average', 'impact': 'neutral'},
                    ],
                )
                created += 1
            except Exception as e:
                logger.error(f"Error creating prediction: {e}")

        self.stdout.write(self.style.SUCCESS(f'Simple predictions: {created} created'))

    def _estimate_probabilities(self, match):
        """Estimate probabilities based on historical league averages."""
        from apps.matches.models import Match

        # Get league-specific historical data
        league_matches = Match.objects.filter(
            season__league=match.season.league,
            status=Match.Status.FINISHED,
        ).exclude(home_score__isnull=True)

        total = league_matches.count()
        if total < 50:
            # Default Premier League-like distribution
            return 0.45, 0.27, 0.28

        home_wins = league_matches.filter(home_score__gt=models.F('away_score')).count()
        draws = league_matches.filter(home_score=models.F('away_score')).count()
        away_wins = total - home_wins - draws

        home_prob = round(home_wins / total, 4)
        draw_prob = round(draws / total, 4)
        away_prob = round(away_wins / total, 4)

        # Normalize
        total_prob = home_prob + draw_prob + away_prob
        home_prob /= total_prob
        draw_prob /= total_prob
        away_prob /= total_prob

        return home_prob, draw_prob, away_prob

    def _validate_predictions(self):
        """Validate predictions against actual match results."""
        from apps.matches.models import Match
        from apps.predictions.models import Prediction
        from django.db.models import F

        self.stdout.write('Validating predictions against actual results...')

        # Get predictions for finished matches that haven't been validated
        predictions = Prediction.objects.filter(
            match__status=Match.Status.FINISHED,
            is_correct__isnull=True,
        ).select_related('match')

        validated = 0
        correct = 0

        for pred in predictions:
            match = pred.match
            if match.home_score is None or match.away_score is None:
                continue

            # Determine actual outcome
            if match.home_score > match.away_score:
                actual = 'HOME'
            elif match.home_score < match.away_score:
                actual = 'AWAY'
            else:
                actual = 'DRAW'

            pred.actual_outcome = actual
            pred.is_correct = (pred.recommended_outcome == actual)
            pred.save(update_fields=['actual_outcome', 'is_correct', 'updated_at'])

            validated += 1
            if pred.is_correct:
                correct += 1

        accuracy = (correct / validated * 100) if validated > 0 else 0

        self.stdout.write(self.style.SUCCESS(
            f'Validated {validated} predictions: {correct} correct ({accuracy:.1f}% accuracy)'
        ))

        # Show breakdown by confidence level
        self._show_accuracy_breakdown()

    def _show_accuracy_breakdown(self):
        """Show accuracy breakdown by confidence level."""
        from apps.predictions.models import Prediction
        from django.db.models import Count, Q

        stats = Prediction.objects.filter(
            is_correct__isnull=False
        ).values('prediction_strength').annotate(
            total=Count('id'),
            correct=Count('id', filter=Q(is_correct=True))
        )

        self.stdout.write('\nAccuracy by confidence level:')
        for stat in stats:
            strength = stat['prediction_strength']
            total = stat['total']
            correct = stat['correct']
            accuracy = (correct / total * 100) if total > 0 else 0
            self.stdout.write(f'  {strength}: {correct}/{total} ({accuracy:.1f}%)')


# Import models for F expression
from django.db import models
