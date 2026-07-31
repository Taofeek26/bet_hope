"""
Management command to clean up duplicate matches in the database.
Must be run BEFORE applying the unique constraint migration.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.matches.models import Match
from apps.predictions.models import Prediction


class Command(BaseCommand):
    help = 'Clean up duplicate matches (same teams, date, season)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write('Finding duplicate matches...')

        # Find duplicates: same (season, home_team, away_team, match_date)
        duplicates = Match.objects.values(
            'season', 'home_team', 'away_team', 'match_date'
        ).annotate(
            count=Count('id')
        ).filter(
            count__gt=1
        )

        total_duplicates = duplicates.count()
        self.stdout.write(f'Found {total_duplicates} sets of duplicate matches')

        if total_duplicates == 0:
            self.stdout.write(self.style.SUCCESS('No duplicates found!'))
            return

        deleted_count = 0
        kept_count = 0

        for dup in duplicates:
            # Get all matches for this duplicate set
            matches = Match.objects.filter(
                season_id=dup['season'],
                home_team_id=dup['home_team'],
                away_team_id=dup['away_team'],
                match_date=dup['match_date']
            ).order_by('-updated_at', '-id')  # Keep most recently updated

            match_list = list(matches)

            if len(match_list) <= 1:
                continue

            # Keep the first one (most recently updated or has more data)
            keeper = match_list[0]
            to_delete = match_list[1:]

            # Prefer match with scores if available
            for m in match_list:
                if m.home_score is not None and keeper.home_score is None:
                    # Swap - this one has more data
                    to_delete = [x for x in match_list if x.id != m.id]
                    keeper = m
                    break

            self.stdout.write(
                f'  Duplicate: {keeper.home_team} vs {keeper.away_team} '
                f'on {keeper.match_date} ({len(to_delete)} duplicates)'
            )

            for match in to_delete:
                # Check for related predictions
                prediction_count = Prediction.objects.filter(match=match).count()

                if prediction_count > 0:
                    # Move predictions to keeper match
                    if not dry_run:
                        Prediction.objects.filter(match=match).update(match=keeper)
                    self.stdout.write(
                        f'    Moving {prediction_count} predictions from match {match.id} to {keeper.id}'
                    )

                if dry_run:
                    self.stdout.write(f'    Would delete match {match.id}')
                else:
                    match.delete()
                    self.stdout.write(f'    Deleted match {match.id}')

                deleted_count += 1

            kept_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\nDry run complete. Would delete {deleted_count} duplicate matches, '
                f'keeping {kept_count} unique matches.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nCleanup complete. Deleted {deleted_count} duplicate matches, '
                f'kept {kept_count} unique matches.'
            ))
