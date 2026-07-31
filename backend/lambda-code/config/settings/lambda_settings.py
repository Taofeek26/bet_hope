"""
Lambda-specific Django settings — minimal, env-driven, no debug toolbar.
Imports from base but overrides for Lambda environment.
"""
from .base import *

# Lambda runs in production mode
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'

# Allow all hosts (Lambda behind API Gateway)
ALLOWED_HOSTS = ['*']

# Database — from DATABASE_URL env var (points to EC2 PostgreSQL)
import dj_database_url
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.config(default=DATABASE_URL)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'bet_hope'),
            'USER': os.getenv('DB_USER', 'bet_hope'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# Redis — from REDIS_URL env var
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# ML artifacts — stored in /tmp for Lambda ephemeral, backed by S3
ML_ARTIFACTS_DIR = os.getenv('ML_ARTIFACTS_DIR', '/tmp/ml/artifacts')

# S3 model bucket
S3_MODEL_BUCKET = os.getenv('S3_MODEL_BUCKET', '')

# Celery — broker URL (tasks still use Celery for compatibility)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)

# Remove debug toolbar (not available in Lambda)
if 'debug_toolbar' in INSTALLED_APPS:
    INSTALLED_APPS = [a for a in INSTALLED_APPS if a != 'debug_toolbar']

# Logging — stdout only (CloudWatch picks it up)
LOGGING['handlers'] = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'simple',
    }
}
LOGGING['root'] = {'handlers': ['console'], 'level': 'INFO'}