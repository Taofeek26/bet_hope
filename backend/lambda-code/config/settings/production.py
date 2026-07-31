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

# Logging
LOGGING['handlers']['file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': '/app/logs/django.log',
    'maxBytes': 1024 * 1024 * 10,  # 10 MB
    'backupCount': 5,
    'formatter': 'verbose',
}
LOGGING['root']['handlers'] = ['console', 'file']
