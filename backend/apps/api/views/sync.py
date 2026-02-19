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
        Get status of all scheduled tasks and their last run times.

        Returns:
            List of scheduled tasks with last run info
        """
        from django_celery_results.models import TaskResult
        from config.celery import app

        # Define task groups with friendly names
        task_groups = {
            'Data Sync': [
                ('daily-data-sync', 'Daily Data Sync', 'Daily at 4:00 AM UTC'),
                ('sync-fixtures-api', 'Fixtures Sync', 'Every 6 hours'),
                ('sync-results-api', 'Results Sync', 'Every 3 hours'),
                ('update-match-results', 'Match Results Update', 'Every 3 hours'),
                ('sync-live-scores-weekend', 'Live Scores (Weekend)', 'Every 15 min (Sat-Sun)'),
                ('sync-live-scores-weekday', 'Live Scores (Weekday)', 'Every 15 min (evenings)'),
            ],
            'Predictions': [
                ('generate-predictions', 'Generate Predictions', 'Every 6 hours'),
                ('validate-predictions', 'Validate Predictions', 'Daily at 6:00 AM UTC'),
            ],
            'ML & Analytics': [
                ('daily-model-training', 'Model Retraining', 'Daily at 5:00 AM UTC'),
                ('calculate-metrics', 'Calculate Metrics', 'Daily at 7:00 AM UTC'),
            ],
            'Documents': [
                ('daily-document-refresh', 'Document Refresh', 'Daily at 4:30 AM UTC'),
                ('daily-scrape-docs', 'Scrape Documentation', 'Daily at 4:15 AM UTC'),
                ('daily-update-strategies', 'Update Strategies', 'Daily at 4:20 AM UTC'),
                ('daily-embed-documents', 'Embed Documents', 'Daily at 4:45 AM UTC'),
                ('morning-football-news', 'Football News (AM)', 'Daily at 6:00 AM UTC'),
                ('evening-football-news', 'Football News (PM)', 'Daily at 6:00 PM UTC'),
                ('daily-cleanup-old-news', 'Cleanup Old News', 'Daily at 5:30 AM UTC'),
            ],
            'Maintenance': [
                ('weekly-historical-sync', 'Historical Sync', 'Weekly on Mondays'),
                ('cleanup-old-data', 'Cleanup Old Data', 'Weekly on Sundays'),
                ('weekly-cleanup-embeddings', 'Cleanup Embeddings', 'Weekly on Sundays'),
            ],
        }

        # Get the beat schedule from Celery config
        beat_schedule = app.conf.beat_schedule

        # Get recent task results for each task type
        now = timezone.now()
        results = []

        for group_name, tasks in task_groups.items():
            group_tasks = []
            for task_key, display_name, schedule in tasks:
                task_info = beat_schedule.get(task_key, {})
                task_name = task_info.get('task', f'tasks.{task_key}')

                # Get last successful run for this task
                last_result = TaskResult.objects.filter(
                    task_name=task_name,
                    status='SUCCESS'
                ).order_by('-date_done').first()

                # Get last run regardless of status
                last_any_result = TaskResult.objects.filter(
                    task_name=task_name
                ).order_by('-date_done').first()

                # Calculate time since last run
                last_run = None
                time_ago = None
                last_status = None

                if last_result:
                    last_run = last_result.date_done.isoformat()
                    delta = now - last_result.date_done
                    if delta.days > 0:
                        time_ago = f"{delta.days}d ago"
                    elif delta.seconds >= 3600:
                        time_ago = f"{delta.seconds // 3600}h ago"
                    elif delta.seconds >= 60:
                        time_ago = f"{delta.seconds // 60}m ago"
                    else:
                        time_ago = "just now"

                if last_any_result:
                    last_status = last_any_result.status.lower()

                # Determine health status
                # Tasks that run frequently should have recent runs
                health = 'unknown'
                if last_result:
                    delta = now - last_result.date_done
                    if 'every 15 min' in schedule.lower():
                        health = 'healthy' if delta < timedelta(minutes=30) else 'stale'
                    elif 'every 3 hours' in schedule.lower():
                        health = 'healthy' if delta < timedelta(hours=4) else 'stale'
                    elif 'every 6 hours' in schedule.lower():
                        health = 'healthy' if delta < timedelta(hours=8) else 'stale'
                    elif 'daily' in schedule.lower():
                        health = 'healthy' if delta < timedelta(hours=26) else 'stale'
                    elif 'weekly' in schedule.lower():
                        health = 'healthy' if delta < timedelta(days=8) else 'stale'
                    else:
                        health = 'healthy' if delta < timedelta(days=1) else 'stale'

                group_tasks.append({
                    'key': task_key,
                    'name': display_name,
                    'schedule': schedule,
                    'last_run': last_run,
                    'time_ago': time_ago,
                    'last_status': last_status,
                    'health': health,
                })

            results.append({
                'group': group_name,
                'tasks': group_tasks,
            })

        # Calculate overall health
        all_tasks = []
        for group in results:
            all_tasks.extend(group['tasks'])

        healthy_count = sum(1 for t in all_tasks if t['health'] == 'healthy')
        stale_count = sum(1 for t in all_tasks if t['health'] == 'stale')
        unknown_count = sum(1 for t in all_tasks if t['health'] == 'unknown')

        if stale_count > 2:
            overall_health = 'warning'
        elif stale_count > 0:
            overall_health = 'partial'
        elif unknown_count == len(all_tasks):
            overall_health = 'unknown'
        else:
            overall_health = 'healthy'

        return Response({
            'overall_health': overall_health,
            'summary': {
                'healthy': healthy_count,
                'stale': stale_count,
                'unknown': unknown_count,
                'total': len(all_tasks),
            },
            'last_checked': now.isoformat(),
            'groups': results,
        })
