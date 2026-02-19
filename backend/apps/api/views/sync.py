"""
Data Sync API Views

Endpoints for triggering data sync operations and checking status.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from django.conf import settings

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
