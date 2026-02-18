"""
Bet_Hope - Development Settings
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Use PostgreSQL with pgvector for development
# DATABASE_URL takes precedence (used in Docker), otherwise use localhost (local dev)
import dj_database_url

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Docker environment - use DATABASE_URL
    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL)
    }
else:
    # Local development - connect to Docker PostgreSQL on localhost
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'bet_hope',
            'USER': 'bet_hope',
            'PASSWORD': 'bet_hope_password',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# Django Debug Toolbar (optional)
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass

# CORS - Allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Celery - Use eager mode for development (optional)
# CELERY_TASK_ALWAYS_EAGER = True

# Logging - More verbose in development
LOGGING['loggers']['apps']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'

# Cache - Use local memory in development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable throttling in development
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}
