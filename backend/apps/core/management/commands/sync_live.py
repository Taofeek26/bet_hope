"""
Live scores (Phase 6) for the competitions football-data.org's free tier
covers (Premier League, Championship, LaLiga, Serie A, Bundesliga, Ligue 1,
Eredivisie, Primeira Liga, Champions League).

Runs every 5 minutes during match hours (EventBridge LiveScoresSchedule).
It returns at once, without calling the API, unless a covered match kicked
off in the last 2.5 hours, starts within 10 minutes, or is still marked live.
One API request per run (all of today's matches), well inside the 10/minute limit.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

COVERED = ['E0', 'E1', 'SP1', 'I1', 'D1', 'F1', 'N1', 'P1', 'CL']


class Command(BaseCommand):
    help = 'Update live scores for covered competitions (cheap no-op outside match windows)'

    def handle(self, *args, **options):
        from apps.matches.models import Match
        now = timezone.now()
        # Once an hour (the first run after :00), fill the scores of matches
        # that ended without one from ESPN (Phase 8), then settle what they
        # finish: the daily validation would otherwise wait until 04:15.
        if now.minute < 5:
            self._espn_results()
        active = Match.objects.filter(season__league__code__in=COVERED).filter(
            Q(status__in=[Match.Status.LIVE, Match.Status.HALFTIME])
            | Q(status=Match.Status.SCHEDULED, kickoff_at__gte=now - timedelta(minutes=150),
                kickoff_at__lte=now + timedelta(minutes=10)))
        if not active.exists():
            self.stdout.write('No covered match in play: nothing to do')
            return

        from apps.data_ingestion.providers.football_data_org import FootballDataOrgProvider
        from apps.teams.identity import TeamResolver
        provider = FootballDataOrgProvider()
        data = provider._request('/matches', {'dateFrom': (now - timedelta(days=1)).date().isoformat(),
                                              'dateTo': now.date().isoformat()})
        matches = (data or {}).get('matches', [])
        resolver = TeamResolver(source='football-data.org')
        live = finished = 0
        for m in matches:
            if m.get('status') not in ('IN_PLAY', 'PAUSED', 'FINISHED'):
                continue
            try:
                provider._sync_match(m, resolver)
            except Exception as e:
                self.stdout.write(f"  skip {m.get('id')}: {e}")
                continue
            live += m['status'] in ('IN_PLAY', 'PAUSED')
            finished += m['status'] == 'FINISHED'
        self.stdout.write(f'Live scores: {live} in play, {finished} finished today ({len(matches)} from the API)')

    def _espn_results(self):
        try:
            from apps.data_ingestion.providers.espn import sync_stale_results
            res = sync_stale_results(days_back=14, stdout=self.stdout)
            if res['finished'] or res['postponed'] or res['cancelled']:
                from django.core.management import call_command
                call_command('generate_predictions', validate=True)
        except Exception as e:  # never let the results check stop live scores
            self.stdout.write(f'ESPN results failed: {e}')
