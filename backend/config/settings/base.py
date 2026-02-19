"""
Bet_Hope - Base Django Settings
"""
import os
from pathlib import Path
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'django_celery_beat',
    'django_celery_results',
]

LOCAL_APPS = [
    'apps.core',
    'apps.leagues',
    'apps.teams',
    'apps.players',
    'apps.matches',
    'apps.predictions',
    'apps.data_ingestion',
    'apps.analytics',
    'apps.ml_pipeline',
    'apps.documents',
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database - Support both DATABASE_URL and individual settings
import dj_database_url

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'bet_hope'),
            'USER': os.getenv('DB_USER', 'bet_hope'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'bet_hope_password'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# =============================================================================
# BET_HOPE CUSTOM SETTINGS
# =============================================================================

# Data directories
DATA_DIR = BASE_DIR / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'

# ML Model settings
ML_ARTIFACTS_DIR = BASE_DIR / 'ml' / 'artifacts'
ML_MODEL_VERSION = os.getenv('ML_MODEL_VERSION', 'latest')

# Supported Leagues Configuration (20 leagues)
SUPPORTED_LEAGUES = {
    # Tier 1 - Big 5 European Leagues
    'E0': {'name': 'Premier League', 'country': 'England', 'tier': 1, 'fd_code': 'E0'},
    'SP1': {'name': 'La Liga', 'country': 'Spain', 'tier': 1, 'fd_code': 'SP1'},
    'I1': {'name': 'Serie A', 'country': 'Italy', 'tier': 1, 'fd_code': 'I1'},
    'D1': {'name': 'Bundesliga', 'country': 'Germany', 'tier': 1, 'fd_code': 'D1'},
    'F1': {'name': 'Ligue 1', 'country': 'France', 'tier': 1, 'fd_code': 'F1'},

    # Tier 2 - Other Top Leagues
    'N1': {'name': 'Eredivisie', 'country': 'Netherlands', 'tier': 2, 'fd_code': 'N1'},
    'P1': {'name': 'Primeira Liga', 'country': 'Portugal', 'tier': 2, 'fd_code': 'P1'},
    'B1': {'name': 'Pro League', 'country': 'Belgium', 'tier': 2, 'fd_code': 'B1'},
    'T1': {'name': 'Super Lig', 'country': 'Turkey', 'tier': 2, 'fd_code': 'T1'},
    'G1': {'name': 'Super League', 'country': 'Greece', 'tier': 2, 'fd_code': 'G1'},

    # Tier 3 - Second Divisions
    'E1': {'name': 'Championship', 'country': 'England', 'tier': 3, 'fd_code': 'E1'},
    'SP2': {'name': 'La Liga 2', 'country': 'Spain', 'tier': 3, 'fd_code': 'SP2'},
    'I2': {'name': 'Serie B', 'country': 'Italy', 'tier': 3, 'fd_code': 'I2'},
    'D2': {'name': '2. Bundesliga', 'country': 'Germany', 'tier': 3, 'fd_code': 'D2'},
    'F2': {'name': 'Ligue 2', 'country': 'France', 'tier': 3, 'fd_code': 'F2'},

    # Tier 4 - Other European Leagues
    'SC0': {'name': 'Premiership', 'country': 'Scotland', 'tier': 4, 'fd_code': 'SC0'},
    'E2': {'name': 'League One', 'country': 'England', 'tier': 4, 'fd_code': 'E2'},
    'E3': {'name': 'League Two', 'country': 'England', 'tier': 4, 'fd_code': 'E3'},

    # Additional Leagues
    'ARG': {'name': 'Primera Division', 'country': 'Argentina', 'tier': 2, 'fd_code': 'ARG'},
    'BRA': {'name': 'Serie A', 'country': 'Brazil', 'tier': 2, 'fd_code': 'BRA'},
}

# Football-Data.co.uk URLs (CSV historical data)
FOOTBALL_DATA_BASE_URL = 'https://www.football-data.co.uk'
FOOTBALL_DATA_CSV_URL = 'https://www.football-data.co.uk/mmz4281'

# Football-Data.org API (real-time fixtures and results)
# Get a free API key at: https://www.football-data.org/client/register
# Free tier: 10 requests/min, covers Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Championship, UCL
FOOTBALL_DATA_API_KEY = os.getenv('FOOTBALL_DATA_API_KEY', '')
FOOTBALL_DATA_API_URL = 'https://api.football-data.org/v4'

# Historical data range (10 years)
HISTORICAL_SEASONS = [
    '2425', '2324', '2223', '2122', '2021',
    '1920', '1819', '1718', '1617', '1516',
]

# Season mappings for display
SEASON_DISPLAY = {
    '2425': '2024-25',
    '2324': '2023-24',
    '2223': '2022-23',
    '2122': '2021-22',
    '2021': '2020-21',
    '1920': '2019-20',
    '1819': '2018-19',
    '1718': '2017-18',
    '1617': '2016-17',
    '1516': '2015-16',
}

# ML Training Configuration
ML_CONFIG = {
    'min_matches_for_training': 500,
    'test_size': 0.2,
    'random_state': 42,
    'feature_selection_threshold': 0.01,
    'xgboost': {
        'n_estimators': 500,
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'objective': 'multi:softprob',
        'num_class': 3,
        'eval_metric': 'mlogloss',
        'early_stopping_rounds': 50,
    },
}

# Prediction Configuration
PREDICTION_CONFIG = {
    'confidence_thresholds': {
        'high': 0.70,
        'medium': 0.55,
        'low': 0.0,
    },
    'cache_ttl_minutes': 60,
}

# =============================================================================
# AI PROVIDER SETTINGS
# =============================================================================

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Google (Gemini)
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')

# Default AI provider
DEFAULT_AI_PROVIDER = os.getenv('DEFAULT_AI_PROVIDER', 'openai')

# RAG Configuration
RAG_CONFIG = {
    'chunk_size': 1000,
    'chunk_overlap': 200,
    'embedding_model': 'text-embedding-3-small',
    'top_k_retrieval': 5,
    'min_similarity_score': 0.5,
}
