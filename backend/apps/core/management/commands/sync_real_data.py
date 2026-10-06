"""
Sync real match data from Football-Data.co.uk

Data sources:
- Football-Data.co.uk: Historical match results + upcoming fixtures (20 leagues, 30+ years)
"""
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync real historical match data from Football-Data.co.uk'

    def add_arguments(self, parser):
        parser.add_argument(
            '--leagues',
            nargs='+',
            default=None,  # Will use all 20 leagues if None
            help='League codes to sync (default: all 20 leagues)',
        )
        parser.add_argument(
            '--seasons',
            nargs='+',
            default=None,  # Will use all seasons if None
            help='Season codes to sync (default: all available seasons)',
        )
        parser.add_argument(
            '--recent-only',
            action='store_true',
            help='Only sync last 5 seasons (faster)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing match data before syncing',
        )
        parser.add_argument(
            '--fixtures',
            action='store_true',
            help='Also sync upcoming fixtures from Football-Data.co.uk',
        )
        parser.add_argument(
            '--fixtures-only',
            action='store_true',
            help='Only sync upcoming fixtures (skip historical data)',
        )
        parser.add_argument(
            '--current-season',
            action='store_true',
            help='Re-download only the current season CSV for every league (results, '
                 'shots, odds), then fixtures. Fits in one Lambda run; scheduled twice a week.',
        )

    def handle(self, *args, **options):
        from apps.data_ingestion.providers.football_data import FootballDataProvider
        from apps.matches.models import Match, MatchStatistics, MatchOdds
        from apps.predictions.models import Prediction
        from apps.leagues.models import League, Season
        from apps.teams.models import Team, TeamSeasonStats

        sync_fixtures = options.get('fixtures', False)
        fixtures_only = options.get('fixtures_only', False)
        recent_only = options.get('recent_only', False)
        current_only = options.get('current_season', False)
        if current_only:
            sync_fixtures = True

        # Get leagues and seasons from provider if not specified
        from apps.data_ingestion.providers.football_data import FootballDataProvider
        from apps.core.seasons import current_season_code
        provider = FootballDataProvider()

        leagues = options.get('leagues') or list(provider.LEAGUES.keys())
        if current_only:
            seasons = [current_season_code()]
        elif options.get('seasons'):
            seasons = options['seasons']
        elif recent_only:
            seasons = provider.SEASONS[:5]  # Last 5 seasons
        else:
            seasons = provider.SEASONS  # All available seasons

        self.stdout.write(f'Syncing {len(leagues)} leagues: {leagues}')
        self.stdout.write(f'Syncing {len(seasons)} seasons: {seasons[:5]}... (showing first 5)')
        if sync_fixtures or fixtures_only:
            self.stdout.write('Will also sync upcoming fixtures')

        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Prediction.objects.all().delete()
            MatchOdds.objects.all().delete()
            MatchStatistics.objects.all().delete()
            Match.objects.all().delete()
            TeamSeasonStats.objects.all().delete()
            Team.objects.all().delete()
            Season.objects.all().delete()
            League.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing data'))

        total_created = 0
        total_updated = 0

        # Sync historical data from Football-Data.co.uk (unless fixtures-only)
        if not fixtures_only:
            for league_code in leagues:
                for season in seasons:
                    self.stdout.write(f'Syncing {league_code}/{season}...')

                    try:
                        df = provider.download_csv(league_code, season, use_cache=True)

                        if df is not None and not df.empty:
                            created, updated = provider.sync_to_database(league_code, season, df)
                            total_created += created
                            total_updated += updated
                            self.stdout.write(
                                self.style.SUCCESS(f'  {league_code}/{season}: {created} created, {updated} updated')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'  {league_code}/{season}: No data available')
                            )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  {league_code}/{season}: Error - {e}')
                        )

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Historical data sync complete!'))
            self.stdout.write(f'  Total created: {total_created}')
            self.stdout.write(f'  Total updated: {total_updated}')

        # Sync upcoming fixtures. Football-Data.org is used here (not
        # API-Football) because API-Football's free tier rejects the
        # current season outright ("Free plans do not have access to this
        # season, try from 2022 to 2024") — it can only ever backfill
        # already-finished seasons, never real upcoming fixtures.
        if sync_fixtures or fixtures_only:
            # Football-Data.co.uk's fixture list first (Phase 2): it covers
            # all 20 leagues and carries pre-match odds, the input the model
            # is trained on and upcoming matches never had (ML-01).
            self.stdout.write('')
            self.stdout.write('Syncing upcoming fixtures + odds from Football-Data.co.uk...')
            try:
                fx_created, fx_updated = provider.sync_fixtures()
                self.stdout.write(self.style.SUCCESS(
                    f'Fixtures (co.uk): {fx_created} created, {fx_updated} updated'))
                total_created += fx_created
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Fixtures (co.uk) failed: {e}'))

            self.stdout.write('Syncing upcoming fixtures from Football-Data.org...')
            from apps.data_ingestion.providers.football_data_org import FootballDataOrgProvider

            if FootballDataOrgProvider.is_configured():
                org_provider = FootballDataOrgProvider()
                fixtures_created, fixtures_updated = org_provider.sync_fixtures_to_database(days=14)
                self.stdout.write(
                    self.style.SUCCESS(f'Fixtures: {fixtures_created} created, {fixtures_updated} updated')
                )
                total_created += fixtures_created

                # Pull final scores for matches that have since kicked off.
                # The window reaches back to the oldest match still marked
                # "scheduled" after its date (DATA-04): a fixed 7 days lost
                # results for good whenever the job missed a week.
                days_back = self._stale_window_days(org_provider)
                self.stdout.write(f'Syncing results from Football-Data.org (last {days_back} days)...')
                results_created, results_updated = org_provider.sync_results_to_database(days=days_back)
                self.stdout.write(
                    self.style.SUCCESS(f'Results: {results_created} created, {results_updated} updated')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('FOOTBALL_DATA_ORG_KEY not configured. Skipping fixture sync.')
                )

        # Generate predictions for upcoming matches using the real trained
        # model (falls back to a labeled statistical estimate on its own if
        # no model is active — see generate_predictions.py). This used to
        # be a local random-number generator mislabeled as 'xgboost'
        # output; that silently filled the database with fake predictions
        # on every scheduled run.
        self.stdout.write('')
        self.stdout.write('Generating predictions for matches without results...')
        from django.core.management import call_command
        call_command('generate_predictions', upcoming=True, days=14)

        # Mark predictions correct/incorrect against whatever results the
        # step above just pulled in. Nothing did this on any schedule
        # before — results could sync in fine and predictions would still
        # show as permanently unverified.
        self.stdout.write('')
        self.stdout.write('Validating predictions against results...')
        call_command('generate_predictions', validate=True)

        # Each club's division = where it plays now (promotion/relegation).
        # One Team spans divisions since Phase 2, so this is recomputed
        # after new matches arrive instead of being fixed at creation.
        from apps.teams.models import Team
        from apps.teams.merge import update_current_league
        moved = 0
        for team in Team.objects.select_related('league'):
            before = team.league_id
            update_current_league(team)
            moved += team.league_id != before
        self.stdout.write(f'Clubs whose current division changed: {moved}')

    @staticmethod
    def _stale_window_days(org_provider, minimum=7, maximum=60):
        """Days back to the oldest past match still not finished, in football-data.org leagues."""
        from datetime import date
        from apps.matches.models import Match

        oldest = (Match.objects.filter(
                      match_date__lt=date.today(),
                      match_date__gte=date.today() - timedelta(days=maximum),
                      status__in=[Match.Status.SCHEDULED, Match.Status.LIVE, Match.Status.HALFTIME],
                      season__league__code__in=list(org_provider.LEAGUES),
                  ).order_by('match_date').values_list('match_date', flat=True).first())
        if not oldest:
            return minimum
        return max(minimum, min(maximum, (date.today() - oldest).days + 1))
