"""
Bet_Hope URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


def health_check(request):
    """Health check that also proves the database answers (503 if not)."""
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        # Don't echo the driver error: it can contain the database hostname.
        return JsonResponse(
            {'status': 'unhealthy', 'service': 'bet-hope-api', 'database': 'unreachable'},
            status=503,
        )
    return JsonResponse({'status': 'healthy', 'service': 'bet-hope-api', 'database': 'ok'})


# API URL patterns
api_v1_patterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include('apps.api.urls')),
]

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/v1/', include((api_v1_patterns, 'api'), namespace='api-v1')),
    # Also serve API at /api/ for frontend compatibility
    path('api/', include(api_v1_patterns)),
]

# Debug toolbar URLs
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
