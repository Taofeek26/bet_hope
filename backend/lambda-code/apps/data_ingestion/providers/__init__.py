# Data Providers
from .football_data import FootballDataProvider
from .football_data_api import FootballDataAPIProvider
from .football_data_org import FootballDataOrgProvider
from .understat import UnderstatProvider

__all__ = [
    'FootballDataProvider',
    'FootballDataAPIProvider',
    'FootballDataOrgProvider',
    'UnderstatProvider',
    'get_fixtures_provider',
]


def get_fixtures_provider():
    """
    Get the best available fixtures/results provider.

    Priority:
    1. Football-Data.org (free, reliable)
    2. API-Football (if configured)

    Returns:
        Provider instance or None if none configured
    """
    from django.conf import settings

    # Prefer Football-Data.org (more generous free tier)
    if getattr(settings, 'FOOTBALL_DATA_ORG_KEY', None):
        return FootballDataOrgProvider()

    # Fallback to API-Football
    if getattr(settings, 'API_FOOTBALL_KEY', None):
        return FootballDataAPIProvider()

    return None
