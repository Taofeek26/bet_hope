"""
Data Sync API Views

Endpoints for triggering data sync operations and checking status.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from apps.data_ingestion.providers import FootballDataAPIProvider


class DataSyncViewSet(viewsets.ViewSet):
    """
    ViewSet for managing data synchronization operations.

    Provides endpoints to:
    - Check API status
    - Trigger fixture sync
    - Trigger results sync
    - Get available leagues
    """

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def api_status(self, request):
        """
        Check API-Football status and configuration.

        Returns:
            API configuration status and account info
        """
        if not settings.API_FOOTBALL_KEY:
            return Response({
                'status': 'not_configured',
                'message': 'API_FOOTBALL_KEY environment variable not set',
                'help': 'Get a free API key at https://dashboard.api-football.com/register'
            })

        try:
            provider = FootballDataAPIProvider()
            account_status = provider.get_status()

            if account_status:
                return Response({
                    'status': 'ok',
                    'account': account_status,
                    'supported_leagues': list(FootballDataAPIProvider.LEAGUES.keys()),
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Could not fetch account status from API'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_fixtures(self, request):
        """
        Trigger fixture sync from API-Football.

        Query params:
            days: Number of days ahead to sync (default: 14)
            league: Optional league code to filter (e.g., 'E0' for Premier League)

        Returns:
            Task status and results
        """
        from tasks import sync_fixtures_api

        days = int(request.query_params.get('days', 14))
        league = request.query_params.get('league')

        if not settings.API_FOOTBALL_KEY:
            return Response({
                'status': 'error',
                'message': 'API_FOOTBALL_KEY not configured'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = sync_fixtures_api.delay(days=days)

            return Response({
                'status': 'started',
                'task_id': task.id,
                'message': f'Fixture sync started for next {days} days',
                'league': league or 'all'
            })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_results(self, request):
        """
        Trigger results sync from API-Football.

        Query params:
            days: Number of days back to sync (default: 3)
            league: Optional league code to filter

        Returns:
            Task status and results
        """
        from tasks import sync_results_api

        days = int(request.query_params.get('days', 3))
        league = request.query_params.get('league')

        if not settings.API_FOOTBALL_KEY:
            return Response({
                'status': 'error',
                'message': 'API_FOOTBALL_KEY not configured'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = sync_results_api.delay(days=days)

            return Response({
                'status': 'started',
                'task_id': task.id,
                'message': f'Results sync started for last {days} days',
                'league': league or 'all'
            })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_live(self, request):
        """
        Trigger live scores sync from API-Football.

        Returns:
            Task status and results
        """
        from tasks import sync_live_scores

        if not settings.API_FOOTBALL_KEY:
            return Response({
                'status': 'error',
                'message': 'API_FOOTBALL_KEY not configured'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = sync_live_scores.delay()

            return Response({
                'status': 'started',
                'task_id': task.id,
                'message': 'Live scores sync started'
            })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def leagues(self, request):
        """
        Get list of supported leagues.

        Returns:
            List of supported leagues with details
        """
        leagues = FootballDataAPIProvider.get_available_leagues()

        return Response({
            'count': len(leagues),
            'leagues': [
                {
                    'code': code,
                    'api_id': info['id'],
                    'name': info['name'],
                    'country': info['country'],
                    'tier': info['tier']
                }
                for code, info in leagues.items()
            ]
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_all(self, request):
        """
        Trigger full data sync - fixtures and results.

        Returns:
            Task status
        """
        from tasks import sync_fixtures_api, sync_results_api

        if not settings.API_FOOTBALL_KEY:
            return Response({
                'status': 'error',
                'message': 'API_FOOTBALL_KEY not configured'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            fixtures_task = sync_fixtures_api.delay(days=14)
            results_task = sync_results_api.delay(days=7)

            return Response({
                'status': 'started',
                'fixtures_task_id': fixtures_task.id,
                'results_task_id': results_task.id,
                'message': 'Full sync started (fixtures + results)'
            })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def task_status(self, request):
        """
        Health of the scheduled jobs, judged by the data they produce
        (Phase 4, API-08). The old version read Celery's TaskResult table,
        which nothing writes since the move to Lambda + EventBridge, so it
        always reported "never run" even when every job succeeded.
        """
        from django.db.models import Max
        from apps.matches.models import Match
        from apps.predictions.models import Prediction, ModelVersion

        now = timezone.now()
        today = now.date()

        def entry(key, name, schedule, last, max_age):
            if last is None:
                return {'key': key, 'name': name, 'schedule': schedule, 'last_run': None,
                        'time_ago': None, 'last_status': None, 'health': 'unknown'}
            delta = now - last
            if delta.days > 0:
                ago = f'{delta.days}d ago'
            elif delta.seconds >= 3600:
                ago = f'{delta.seconds // 3600}h ago'
            elif delta.seconds >= 60:
                ago = f'{delta.seconds // 60}m ago'
            else:
                ago = 'just now'
            return {'key': key, 'name': name, 'schedule': schedule, 'last_run': last.isoformat(),
                    'time_ago': ago, 'last_status': 'success',
                    'health': 'healthy' if delta <= max_age else 'stale'}

        near = Match.objects.filter(match_date__gte=today - timedelta(days=10),
                                    match_date__lte=today + timedelta(days=14))
        fixtures_last = near.aggregate(t=Max('updated_at'))['t']
        csv_last = (Match.objects.exclude(fd_match_id__startswith='fdorg_')
                    .filter(match_date__gte=today - timedelta(days=30))
                    .aggregate(t=Max('updated_at'))['t'])
        training_last = ModelVersion.objects.aggregate(t=Max('created_at'))['t']
        predictions_last = Prediction.objects.aggregate(t=Max('updated_at'))['t']

        groups = [
            {'group': 'Data', 'tasks': [
                entry('daily-sync', 'Fixtures, odds & recent results', 'Daily 04:15 UTC', fixtures_last, timedelta(hours=26)),
                entry('current-season', 'Current-season results (all 20 leagues)', 'Mon & Thu 03:30 UTC', csv_last, timedelta(days=4, hours=12)),
            ]},
            {'group': 'Model', 'tasks': [
                entry('training', 'Model training (promotion-checked)', 'Daily 05:00 UTC', training_last, timedelta(hours=26)),
                entry('predictions', 'Predictions for the next 14 days', 'Daily 04:15 & 05:15 UTC', predictions_last, timedelta(hours=26)),
            ]},
        ]
        tasks = [t for g in groups for t in g['tasks']]
        healthy = sum(t['health'] == 'healthy' for t in tasks)
        stale = sum(t['health'] == 'stale' for t in tasks)
        unknown = sum(t['health'] == 'unknown' for t in tasks)
        overall = ('healthy' if healthy == len(tasks) else 'unknown' if unknown == len(tasks)
                   else 'warning' if stale > 1 else 'partial')
        return Response({
            'overall_health': overall,
            'summary': {'healthy': healthy, 'stale': stale, 'unknown': unknown, 'total': len(tasks)},
            'last_checked': now.isoformat(),
            'groups': groups,
        })
