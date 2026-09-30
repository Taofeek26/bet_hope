"""
Bet_Hope - Production Settings
"""
from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

DEBUG = False

# CORS / CSRF — the frontend now lives on Vercel (a different origin), so
# these must be set explicitly via env; base.py's localhost default would
# silently lock out the real frontend if left unset here.
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if origin.strip()
]
# e.g. CORS_ALLOWED_ORIGIN_REGEXES=^https://bet-hope-.*\.vercel\.app$
# to allow Vercel's per-branch preview deployment URLs.
CORS_ALLOWED_ORIGIN_REGEXES = [
    regex.strip() for regex in os.getenv('CORS_ALLOWED_ORIGIN_REGEXES', '').split(',') if regex.strip()
]
# CSRF_TRUSTED_ORIGINS supports Django's own "https://*.vercel.app" wildcard
# syntax (no regex here) — reuse CORS_ALLOWED_ORIGINS plus an optional extra
# wildcard var for preview domains.
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS + [
    origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS_EXTRA', '').split(',') if origin.strip()
]

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# SSL settings - disabled until SSL certificate is configured
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'false').lower() == 'true'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'false').lower() == 'true'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'false').lower() == 'true'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'false').lower() == 'true'

# Sentry Error Tracking
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
    )

# base.py sets the 'apps' logger to DEBUG, which is useful locally but
# fills CloudWatch (billed per GB ingested) in production. (COST-06)
LOGGING['loggers']['apps']['level'] = os.getenv('APPS_LOG_LEVEL', 'INFO')

# Logging — skip the file handler entirely on Lambda: /app is read-only
# there (only /tmp is writable), and CloudWatch Logs already captures
# stdout/stderr from every invocation, so a log file adds nothing.
if not os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    LOGGING['handlers']['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': '/app/logs/django.log',
        'maxBytes': 1024 * 1024 * 10,  # 10 MB
        'backupCount': 5,
        'formatter': 'verbose',
    }
    LOGGING['root']['handlers'] = ['console', 'file']

# No standalone Redis/ElastiCache in the Lambda architecture (no NAT-free
# way to justify its cost here) — cache falls back to per-instance memory
# (a correctness no-op, not a functionality requirement) and any .delay()
# calls run synchronously in-process instead of publishing to a broker
# that doesn't exist. Scheduled jobs (train/predict/sync) run as direct
# EventBridge-triggered Lambda invocations instead of Celery beat — see
# infrastructure/template.yaml.
if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

    # Rate-limit identity. The API is edge-optimized, so X-Forwarded-For
    # arrives as "<client>, <CloudFront edge IP>". With NUM_PROXIES unset,
    # DRF keys throttles on that whole string, and the edge IP changes
    # between requests, so limits never accumulated (found in the Phase 0
    # live test). 2 = take the second-to-last address: the real client as
    # seen by CloudFront. Anything a caller prepends is ignored, so it
    # can't be spoofed. With a single-entry header (regional API) DRF
    # falls back to that entry.
    REST_FRAMEWORK['NUM_PROXIES'] = int(os.getenv('DRF_NUM_PROXIES', '2'))

    # Everything under BASE_DIR (/var/task) is read-only at runtime — only
    # /tmp is writable. These are used as scratch/cache dirs (re-downloaded
    # or regenerated each cold start, not meant to persist — anything that
    # needs to persist already goes to RDS or S3).
    from pathlib import Path
    _TMP = Path('/tmp')
    MEDIA_ROOT = _TMP / 'media'
    DATA_DIR = _TMP / 'data'
    RAW_DATA_DIR = DATA_DIR / 'raw'
    PROCESSED_DATA_DIR = DATA_DIR / 'processed'
    ML_ARTIFACTS_DIR = _TMP / 'ml' / 'artifacts'
    for _dir in (MEDIA_ROOT, RAW_DATA_DIR, PROCESSED_DATA_DIR, ML_ARTIFACTS_DIR):
        _dir.mkdir(parents=True, exist_ok=True)

# Name of the sibling Lambda function (ManageFunction in template.yaml) that
# runs long management commands. WebFunction has a 29s API Gateway timeout,
# far too short for train_model/sync_real_data — the admin task-runner
# invokes ManageFunction asynchronously instead and tracks progress via the
# TaskRun model rather than blocking the request.
MANAGE_FUNCTION_NAME = os.getenv('MANAGE_FUNCTION_NAME', '')
