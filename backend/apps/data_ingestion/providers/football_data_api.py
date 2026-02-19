"""
Football-Data.org API Provider

REST API provider for real-time fixtures and results.
Free tier: 10 requests/minute, covers top European leagues.

Requires API key - get one free at: https://www.football-data.org/client/register

Free tier competitions:
- Premier League (PL)
- La Liga (PD)
- Serie A (SA)
- Bundesliga (BL1)
- Ligue 1 (FL1)
- Championship (ELC)
- Champions League (CL)
- Eredivisie (DED)
- Primeira Liga (PPL)
- European Championship (EC)
- World Cup (WC)
"""
import logging
import time
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class FootballDataAPIProvider:
    """
    Provider for Football-Data.org REST API.
    Provides real-time fixtures and results.
    """

    BASE_URL = "https://api.football-data.org/v4"

    # Competition codes mapping
    # These are the free tier competitions
    COMPETITIONS = {
        'PL': {'name': 'Premier League', 'country': 'England', 'code': 'E0', 'tier': 1},
        'PD': {'name': 'La Liga', 'country': 'Spain', 'code': 'SP1', 'tier': 1},
        'SA': {'name': 'Serie A', 'country': 'Italy', 'code': 'I1', 'tier': 1},
        'BL1': {'name': 'Bundesliga', 'country': 'Germany', 'code': 'D1', 'tier': 1},
        'FL1': {'name': 'Ligue 1', 'country': 'France', 'code': 'F1', 'tier': 1},
        'ELC': {'name': 'Championship', 'country': 'England', 'code': 'E1', 'tier': 3},
        'DED': {'name': 'Eredivisie', 'country': 'Netherlands', 'code': 'N1', 'tier': 2},
        'PPL': {'name': 'Primeira Liga', 'country': 'Portugal', 'code': 'P1', 'tier': 2},
        'CL': {'name': 'Champions League', 'country': 'Europe', 'code': 'CL', 'tier': 1},
    }

    # Mapping from our league codes to API competition codes
    LEAGUE_TO_COMPETITION = {
        'E0': 'PL',   # Premier League
        'SP1': 'PD',  # La Liga
        'I1': 'SA',   # Serie A
        'D1': 'BL1',  # Bundesliga
        'F1': 'FL1',  # Ligue 1
        'E1': 'ELC',  # Championship
        'N1': 'DED',  # Eredivisie
        'P1': 'PPL',  # Primeira Liga
        'CL': 'CL',   # Champions League
    }

    # Status mapping from API to our model
    STATUS_MAPPING = {
        'SCHEDULED': 'scheduled',
        'TIMED': 'scheduled',
        'IN_PLAY': 'live',
        'PAUSED': 'halftime',
        'FINISHED': 'finished',
        'SUSPENDED': 'postponed',
        'POSTPONED': 'postponed',
        'CANCELLED': 'cancelled',
        'AWARDED': 'finished',
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the API provider.

        Args:
            api_key: Football-Data.org API key. If not provided, uses settings.
        """
        self.api_key = api_key or getattr(settings, 'FOOTBALL_DATA_API_KEY', None)
        if not self.api_key:
            logger.warning("No FOOTBALL_DATA_API_KEY configured. API calls will fail.")

        self.session = requests.Session()
        self.session.headers.update({
            'X-Auth-Token': self.api_key or '',
        })

        # Rate limiting: 10 requests per minute for free tier
        self.last_request_time = 0
        self.min_request_interval = 6  # seconds between requests (10 req/min)

    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make an API request with rate limiting.

        Args:
            endpoint: API endpoint (e.g., '/competitions/PL/matches')
            params: Query parameters

        Returns:
            JSON response or None on error
        """
        if not self.api_key:
            logger.error("No API key configured")
            return None

        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        logger.info(f"API request: {url}")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning("Rate limit exceeded. Waiting 60 seconds...")
                time.sleep(60)
                return self._request(endpoint, params)
            elif response.status_code == 403:
                logger.error("API key invalid or subscription required for this resource")
            else:
                logger.error(f"HTTP error: {e}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def get_competitions(self) -> Optional[List[Dict]]:
        """
        Get list of available competitions.

        Returns:
            List of competition data
        """
        data = self._request('/competitions')
        if data:
            return data.get('competitions', [])
        return None

    def get_matches(
        self,
        competition: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[str] = None,
        matchday: Optional[int] = None,
    ) -> Optional[List[Dict]]:
        """
        Get matches for a competition.

        Args:
            competition: Competition code (e.g., 'PL')
            date_from: Start date filter
            date_to: End date filter
            status: Status filter (SCHEDULED, LIVE, FINISHED, etc.)
            matchday: Matchday number filter

        Returns:
            List of match data
        """
        params = {}
        if date_from:
            params['dateFrom'] = date_from.isoformat()
        if date_to:
            params['dateTo'] = date_to.isoformat()
        if status:
            params['status'] = status
        if matchday:
            params['matchday'] = matchday

        data = self._request(f'/competitions/{competition}/matches', params)
        if data:
            return data.get('matches', [])
        return None

    def get_upcoming_fixtures(
        self,
        competition: Optional[str] = None,
        days: int = 14
    ) -> Optional[List[Dict]]:
        """
        Get upcoming fixtures.

        Args:
            competition: Optional competition filter
            days: Number of days ahead to fetch

        Returns:
            List of upcoming match data
        """
        today = date.today()
        date_to = today + timedelta(days=days)

        if competition:
            return self.get_matches(
                competition,
                date_from=today,
                date_to=date_to,
                status='SCHEDULED'
            )
        else:
            # Get fixtures across all free competitions
            all_fixtures = []
            for comp_code in self.COMPETITIONS.keys():
                fixtures = self.get_matches(
                    comp_code,
                    date_from=today,
                    date_to=date_to,
                    status='SCHEDULED'
                )
                if fixtures:
                    all_fixtures.extend(fixtures)
            return all_fixtures

    def get_recent_results(
        self,
        competition: Optional[str] = None,
        days: int = 7
    ) -> Optional[List[Dict]]:
        """
        Get recent match results.

        Args:
            competition: Optional competition filter
            days: Number of days back to fetch

        Returns:
            List of finished match data
        """
        today = date.today()
        date_from = today - timedelta(days=days)

        if competition:
            return self.get_matches(
                competition,
                date_from=date_from,
                date_to=today,
                status='FINISHED'
            )
        else:
            all_results = []
            for comp_code in self.COMPETITIONS.keys():
                results = self.get_matches(
                    comp_code,
                    date_from=date_from,
                    date_to=today,
                    status='FINISHED'
                )
                if results:
                    all_results.extend(results)
            return all_results

    def get_live_matches(self) -> Optional[List[Dict]]:
        """
        Get currently live matches.

        Returns:
            List of live match data
        """
        data = self._request('/matches', {'status': 'IN_PLAY'})
        if data:
            return data.get('matches', [])
        return None

    def get_standings(self, competition: str) -> Optional[List[Dict]]:
        """
        Get current standings for a competition.

        Args:
            competition: Competition code

        Returns:
            List of standing tables
        """
        data = self._request(f'/competitions/{competition}/standings')
        if data:
            return data.get('standings', [])
        return None

    def sync_fixtures_to_database(
        self,
        competition: Optional[str] = None,
        days: int = 14
    ) -> Tuple[int, int]:
        """
        Sync upcoming fixtures to database.

        Args:
            competition: Optional competition filter
            days: Days ahead to sync

        Returns:
            Tuple of (created, updated)
        """
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match

        fixtures = self.get_upcoming_fixtures(competition, days)
        if not fixtures:
            logger.info("No fixtures to sync")
            return 0, 0

        created = 0
        updated = 0

        # Get current season code
        today = date.today()
        if today.month >= 8:
            current_season = f"{str(today.year)[2:]}{str(today.year + 1)[2:]}"
        else:
            current_season = f"{str(today.year - 1)[2:]}{str(today.year)[2:]}"

        with transaction.atomic():
            for match_data in fixtures:
                try:
                    result = self._sync_match(match_data, current_season)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                except Exception as e:
                    logger.error(f"Error syncing fixture: {e}")
                    continue

        logger.info(f"Fixtures synced: {created} created, {updated} updated")
        return created, updated

    def sync_results_to_database(
        self,
        competition: Optional[str] = None,
        days: int = 7
    ) -> Tuple[int, int]:
        """
        Sync recent results to database.

        Args:
            competition: Optional competition filter
            days: Days back to sync

        Returns:
            Tuple of (created, updated)
        """
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match

        results = self.get_recent_results(competition, days)
        if not results:
            logger.info("No results to sync")
            return 0, 0

        created = 0
        updated = 0

        today = date.today()
        if today.month >= 8:
            current_season = f"{str(today.year)[2:]}{str(today.year + 1)[2:]}"
        else:
            current_season = f"{str(today.year - 1)[2:]}{str(today.year)[2:]}"

        with transaction.atomic():
            for match_data in results:
                try:
                    result = self._sync_match(match_data, current_season)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                except Exception as e:
                    logger.error(f"Error syncing result: {e}")
                    continue

        logger.info(f"Results synced: {created} created, {updated} updated")
        return created, updated

    def _sync_match(self, match_data: Dict, season_code: str) -> Optional[str]:
        """
        Sync a single match to the database.

        Args:
            match_data: Match data from API
            season_code: Current season code

        Returns:
            'created', 'updated', or None
        """
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match

        # Get competition info
        competition = match_data.get('competition', {})
        comp_code = competition.get('code', '')

        if comp_code not in self.COMPETITIONS:
            return None

        comp_info = self.COMPETITIONS[comp_code]
        our_league_code = comp_info.get('code', comp_code)

        # Get or create league
        league, _ = League.objects.get_or_create(
            code=our_league_code,
            defaults={
                'name': comp_info['name'],
                'country': comp_info['country'],
                'tier': comp_info['tier'],
            }
        )

        # Get or create season
        season_name = f"20{season_code[:2]}-{season_code[2:]}"
        db_season, _ = Season.objects.get_or_create(
            league=league,
            code=season_code,
            defaults={'name': season_name}
        )

        # Get teams
        home_data = match_data.get('homeTeam', {})
        away_data = match_data.get('awayTeam', {})

        home_name = home_data.get('shortName') or home_data.get('name', 'Unknown')
        away_name = away_data.get('shortName') or away_data.get('name', 'Unknown')

        home_team, _ = Team.objects.get_or_create(
            name=home_name,
            league=league,
            defaults={'fd_name': home_name}
        )

        away_team, _ = Team.objects.get_or_create(
            name=away_name,
            league=league,
            defaults={'fd_name': away_name}
        )

        # Parse date and time
        utc_date = match_data.get('utcDate', '')
        if utc_date:
            match_dt = datetime.fromisoformat(utc_date.replace('Z', '+00:00'))
            match_date = match_dt.date()
            kickoff_time = match_dt.time()
        else:
            return None

        # Create unique ID
        api_id = match_data.get('id')
        match_id = f"api_{api_id}" if api_id else f"{our_league_code}_{season_code}_{match_date}_{home_name}_{away_name}"

        # Get score if available
        score = match_data.get('score', {})
        full_time = score.get('fullTime', {})
        half_time = score.get('halfTime', {})

        home_score = full_time.get('home')
        away_score = full_time.get('away')
        home_ht = half_time.get('home')
        away_ht = half_time.get('away')

        # Map status
        api_status = match_data.get('status', 'SCHEDULED')
        our_status = self.STATUS_MAPPING.get(api_status, 'scheduled')

        # Determine match status
        if our_status == 'finished' and home_score is not None:
            status = Match.Status.FINISHED
        elif our_status == 'live':
            status = Match.Status.LIVE
        elif our_status == 'halftime':
            status = Match.Status.HALFTIME
        elif our_status == 'postponed':
            status = Match.Status.POSTPONED
        elif our_status == 'cancelled':
            status = Match.Status.CANCELLED
        else:
            status = Match.Status.SCHEDULED

        # Create or update match
        match, match_created = Match.objects.update_or_create(
            fd_match_id=match_id,
            defaults={
                'season': db_season,
                'home_team': home_team,
                'away_team': away_team,
                'match_date': match_date,
                'kickoff_time': kickoff_time,
                'matchweek': match_data.get('matchday'),
                'home_score': home_score,
                'away_score': away_score,
                'home_halftime_score': home_ht,
                'away_halftime_score': away_ht,
                'status': status,
            }
        )

        return 'created' if match_created else 'updated'

    def sync_live_matches(self) -> int:
        """
        Update live match scores in database.

        Returns:
            Number of matches updated
        """
        from apps.matches.models import Match

        live_matches = self.get_live_matches()
        if not live_matches:
            return 0

        updated = 0

        for match_data in live_matches:
            try:
                api_id = match_data.get('id')
                match_id = f"api_{api_id}"

                score = match_data.get('score', {})
                full_time = score.get('fullTime', {})

                Match.objects.filter(fd_match_id=match_id).update(
                    home_score=full_time.get('home'),
                    away_score=full_time.get('away'),
                    status=Match.Status.LIVE,
                )
                updated += 1

            except Exception as e:
                logger.error(f"Error updating live match: {e}")
                continue

        logger.info(f"Updated {updated} live matches")
        return updated

    @classmethod
    def is_configured(cls) -> bool:
        """Check if the API is properly configured."""
        return bool(getattr(settings, 'FOOTBALL_DATA_API_KEY', None))

    @classmethod
    def get_available_competitions(cls) -> Dict[str, Dict]:
        """Get list of competitions available in free tier."""
        return cls.COMPETITIONS.copy()
