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
    - Get available competitions
    """

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def api_status(self, request):
        """
        Check Football-Data.org API status and configuration.

        Returns:
            API configuration status and available competitions
        """
        if not settings.FOOTBALL_DATA_API_KEY:
            return Response({
                'status': 'not_configured',
                'message': 'FOOTBALL_DATA_API_KEY environment variable not set',
                'help': 'Get a free API key at https://www.football-data.org/client/register'
            })

        try:
            provider = FootballDataAPIProvider()
            competitions = provider.get_competitions()

            if competitions:
                return Response({
                    'status': 'ok',
                    'competitions_available': len(competitions),
                    'free_tier_competitions': list(FootballDataAPIProvider.COMPETITIONS.keys()),
                    'competitions': [
                        {
                            'code': c['code'],
                            'name': c['name'],
                            'country': c.get('area', {}).get('name', 'Unknown')
                        }
                        for c in competitions[:20]  # Limit to first 20
                    ]
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Could not fetch competitions from API'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_fixtures(self, request):
        """
        Trigger fixture sync from Football-Data.org API.

        Query params:
            days: Number of days ahead to sync (default: 14)
            competition: Optional competition code to filter

        Returns:
            Task status and results
        """
        from tasks import sync_fixtures_api

        days = int(request.query_params.get('days', 14))
        competition = request.query_params.get('competition')

        # Check if API is configured
        if not settings.FOOTBALL_DATA_API_KEY:
            return Response({
                'status': 'error',
                'message': 'FOOTBALL_DATA_API_KEY not configured'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Trigger async task
            task = sync_fixtures_api.delay(days=days)

            return Response({
                'status': 'started',
                'task_id': task.id,
                'message': f'Fixture sync started for next {days} days',
                'competition': competition or 'all'
            })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_results(self, request):
        """
        Trigger results sync from Football-Data.org API.

        Query params:
            days: Number of days back to sync (default: 3)
            competition: Optional competition code to filter

        Returns:
            Task status and results
        """
        from tasks import sync_results_api

        days = int(request.query_params.get('days', 3))
        competition = request.query_params.get('competition')

        if not settings.FOOTBALL_DATA_API_KEY:
            return Response({
                'status': 'error',
                'message': 'FOOTBALL_DATA_API_KEY not configured'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = sync_results_api.delay(days=days)

            return Response({
                'status': 'started',
                'task_id': task.id,
                'message': f'Results sync started for last {days} days',
                'competition': competition or 'all'
            })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def sync_live(self, request):
        """
        Trigger live scores sync from Football-Data.org API.

        Returns:
            Task status and results
        """
        from tasks import sync_live_scores

        if not settings.FOOTBALL_DATA_API_KEY:
            return Response({
                'status': 'error',
                'message': 'FOOTBALL_DATA_API_KEY not configured'
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
    def competitions(self, request):
        """
        Get list of supported competitions from free tier.

        Returns:
            List of supported competitions with details
        """
        competitions = FootballDataAPIProvider.get_available_competitions()

        return Response({
            'count': len(competitions),
            'competitions': [
                {
                    'api_code': code,
                    'name': info['name'],
                    'country': info['country'],
                    'our_code': info['code'],
                    'tier': info['tier']
                }
                for code, info in competitions.items()
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

        if not settings.FOOTBALL_DATA_API_KEY:
            return Response({
                'status': 'error',
                'message': 'FOOTBALL_DATA_API_KEY not configured'
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
