"""
Football-Data.org Provider

REST API provider for fixtures and results.
Free tier: 10 requests/minute, covers all major European leagues.

Get free API key at: https://www.football-data.org/client/register

Supported competitions (free tier):
- Premier League (PL)
- La Liga (PD)
- Serie A (SA)
- Bundesliga (BL1)
- Ligue 1 (FL1)
- Championship (ELC)
- Eredivisie (DED)
- Primeira Liga (PPL)
- Champions League (CL)
- Europa League (EL)
"""
import logging
import time
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple

import requests
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


class FootballDataOrgProvider:
    """
    Provider for Football-Data.org REST API.
    Provides fixtures and results for major European leagues.

    Register for free at: https://www.football-data.org/client/register
    """

    BASE_URL = "https://api.football-data.org/v4"

    # League code mapping (Football-Data.org codes to our codes)
    # Our code -> Football-Data.org code
    LEAGUES = {
        'E0': {'fd_code': 'PL', 'name': 'Premier League', 'country': 'England', 'tier': 1},
        'SP1': {'fd_code': 'PD', 'name': 'La Liga', 'country': 'Spain', 'tier': 1},
        'I1': {'fd_code': 'SA', 'name': 'Serie A', 'country': 'Italy', 'tier': 1},
        'D1': {'fd_code': 'BL1', 'name': 'Bundesliga', 'country': 'Germany', 'tier': 1},
        'F1': {'fd_code': 'FL1', 'name': 'Ligue 1', 'country': 'France', 'tier': 1},
        'E1': {'fd_code': 'ELC', 'name': 'Championship', 'country': 'England', 'tier': 3},
        'N1': {'fd_code': 'DED', 'name': 'Eredivisie', 'country': 'Netherlands', 'tier': 2},
        'P1': {'fd_code': 'PPL', 'name': 'Primeira Liga', 'country': 'Portugal', 'tier': 2},
        'CL': {'fd_code': 'CL', 'name': 'Champions League', 'country': 'Europe', 'tier': 1},
        'EL': {'fd_code': 'EL', 'name': 'Europa League', 'country': 'Europe', 'tier': 1},
    }

    # Reverse mapping: Football-Data.org code to our code
    FD_CODE_TO_OUR_CODE = {info['fd_code']: code for code, info in LEAGUES.items()}

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
        self.api_key = api_key or getattr(settings, 'FOOTBALL_DATA_ORG_KEY', None)
        if not self.api_key:
            logger.warning("No FOOTBALL_DATA_ORG_KEY configured. API calls will fail.")

        self.session = requests.Session()
        self.session.headers.update({
            'X-Auth-Token': self.api_key or '',
        })

        # Rate limiting: 10 requests per minute for free tier
        self.last_request_time = 0
        self.min_request_interval = 6  # 6 seconds between requests = 10/min

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
            endpoint: API endpoint (e.g., '/matches')
            params: Query parameters

        Returns:
            JSON response or None on error
        """
        if not self.api_key:
            logger.error("No API key configured")
            return None

        self._rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        logger.info(f"API request: {url} params={params}")

        try:
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 429:
                logger.warning("Rate limit exceeded. Waiting 60 seconds...")
                time.sleep(60)
                return self._request(endpoint, params)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                logger.error("API key invalid or access denied")
            elif response.status_code == 404:
                logger.warning(f"Resource not found: {endpoint}")
            else:
                logger.error(f"HTTP error: {e}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def get_status(self) -> Optional[Dict]:
        """
        Get API account status.

        Returns:
            Account status info
        """
        # Football-Data.org doesn't have a dedicated status endpoint
        # Test with a simple request
        data = self._request('/competitions/PL')
        if data:
            return {'status': 'ok', 'message': 'API is working'}
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
        competition_code: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        matchday: Optional[int] = None,
    ) -> Optional[List[Dict]]:
        """
        Get matches/fixtures.

        Args:
            competition_code: Football-Data.org competition code (e.g., 'PL')
            date_from: Start date filter (YYYY-MM-DD)
            date_to: End date filter (YYYY-MM-DD)
            status: Status filter (SCHEDULED, FINISHED, etc.)
            matchday: Matchday filter

        Returns:
            List of match data
        """
        params = {}

        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        if status:
            params['status'] = status
        if matchday:
            params['matchday'] = matchday

        if competition_code:
            endpoint = f'/competitions/{competition_code}/matches'
        else:
            endpoint = '/matches'

        data = self._request(endpoint, params)
        if data:
            return data.get('matches', [])
        return None

    def get_upcoming_fixtures(
        self,
        league_code: Optional[str] = None,
        days: int = 14
    ) -> Optional[List[Dict]]:
        """
        Get upcoming fixtures.

        Args:
            league_code: Our league code (e.g., 'E0')
            days: Number of days ahead to fetch

        Returns:
            List of upcoming fixture data
        """
        today = date.today()
        to_date = today + timedelta(days=days)

        if league_code and league_code in self.LEAGUES:
            fd_code = self.LEAGUES[league_code]['fd_code']
            return self.get_matches(
                competition_code=fd_code,
                date_from=today.isoformat(),
                date_to=to_date.isoformat(),
                status='SCHEDULED,TIMED'
            )
        else:
            # Get fixtures for all supported leagues
            all_fixtures = []
            for code, info in self.LEAGUES.items():
                fixtures = self.get_matches(
                    competition_code=info['fd_code'],
                    date_from=today.isoformat(),
                    date_to=to_date.isoformat(),
                    status='SCHEDULED,TIMED'
                )
                if fixtures:
                    all_fixtures.extend(fixtures)
            return all_fixtures

    def get_recent_results(
        self,
        league_code: Optional[str] = None,
        days: int = 7
    ) -> Optional[List[Dict]]:
        """
        Get recent match results.

        Args:
            league_code: Our league code (e.g., 'E0')
            days: Number of days back to fetch

        Returns:
            List of finished match data
        """
        today = date.today()
        from_date = today - timedelta(days=days)

        if league_code and league_code in self.LEAGUES:
            fd_code = self.LEAGUES[league_code]['fd_code']
            return self.get_matches(
                competition_code=fd_code,
                date_from=from_date.isoformat(),
                date_to=today.isoformat(),
                status='FINISHED'
            )
        else:
            all_results = []
            for code, info in self.LEAGUES.items():
                results = self.get_matches(
                    competition_code=info['fd_code'],
                    date_from=from_date.isoformat(),
                    date_to=today.isoformat(),
                    status='FINISHED'
                )
                if results:
                    all_results.extend(results)
            return all_results

    def get_standings(self, league_code: str) -> Optional[List[Dict]]:
        """
        Get current standings for a league.

        Args:
            league_code: Our league code

        Returns:
            Standings data
        """
        if league_code not in self.LEAGUES:
            return None

        fd_code = self.LEAGUES[league_code]['fd_code']
        data = self._request(f'/competitions/{fd_code}/standings')

        if data:
            return data.get('standings', [])
        return None

    def sync_fixtures_to_database(
        self,
        league_code: Optional[str] = None,
        days: int = 14
    ) -> Tuple[int, int]:
        """
        Sync upcoming fixtures to database.

        Args:
            league_code: Optional league filter
            days: Days ahead to sync

        Returns:
            Tuple of (created, updated)
        """
        fixtures = self.get_upcoming_fixtures(league_code, days)
        if not fixtures:
            logger.info("No fixtures to sync")
            return 0, 0

        return self._sync_matches_to_db(fixtures)

    def sync_results_to_database(
        self,
        league_code: Optional[str] = None,
        days: int = 7
    ) -> Tuple[int, int]:
        """
        Sync recent results to database.

        Args:
            league_code: Optional league filter
            days: Days back to sync

        Returns:
            Tuple of (created, updated)
        """
        results = self.get_recent_results(league_code, days)
        if not results:
            logger.info("No results to sync")
            return 0, 0

        return self._sync_matches_to_db(results)

    def _sync_matches_to_db(self, matches: List[Dict]) -> Tuple[int, int]:
        """
        Sync matches to database.

        Args:
            matches: List of match data from API

        Returns:
            Tuple of (created, updated)
        """
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match

        created = 0
        updated = 0

        # Get current season code
        today = date.today()
        if today.month >= 8:
            current_season = f"{str(today.year)[2:]}{str(today.year + 1)[2:]}"
        else:
            current_season = f"{str(today.year - 1)[2:]}{str(today.year)[2:]}"

        with transaction.atomic():
            for match_data in matches:
                try:
                    result = self._sync_match(match_data, current_season)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                except Exception as e:
                    logger.error(f"Error syncing match: {e}")
                    continue

        logger.info(f"Matches synced: {created} created, {updated} updated")
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
        fd_code = competition.get('code')

        # Find our league code
        our_league_code = self.FD_CODE_TO_OUR_CODE.get(fd_code)
        if not our_league_code:
            return None

        league_info = self.LEAGUES[our_league_code]

        # Get or create league
        league, _ = League.objects.get_or_create(
            code=our_league_code,
            defaults={
                'name': league_info['name'],
                'country': league_info['country'],
                'tier': league_info['tier'],
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
        home_team_data = match_data.get('homeTeam', {})
        away_team_data = match_data.get('awayTeam', {})

        home_name = home_team_data.get('name', 'Unknown')
        away_name = away_team_data.get('name', 'Unknown')
        home_crest = home_team_data.get('crest', '')
        away_crest = away_team_data.get('crest', '')

        home_team = self._find_or_create_team(home_name, league, home_crest)
        away_team = self._find_or_create_team(away_name, league, away_crest)

        # Parse date and time
        utc_date = match_data.get('utcDate', '')
        if utc_date:
            match_dt = datetime.fromisoformat(utc_date.replace('Z', '+00:00'))
            match_date = match_dt.date()
            kickoff_time = match_dt.time()
        else:
            return None

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

        # Get matchweek
        matchday = match_data.get('matchday')

        # API match ID for reference
        api_id = match_data.get('id')
        api_match_id = f"fdorg_{api_id}" if api_id else ""

        # Create or update match
        match, match_created = Match.objects.update_or_create(
            season=db_season,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            defaults={
                'kickoff_time': kickoff_time,
                'matchweek': matchday,
                'home_score': home_score,
                'away_score': away_score,
                'home_halftime_score': home_ht,
                'away_halftime_score': away_ht,
                'status': status,
                'fd_match_id': api_match_id,
            }
        )

        return 'created' if match_created else 'updated'

    def _normalize_team_name(self, name: str) -> str:
        """
        Normalize team name for matching.
        """
        import unicodedata
        import re

        if not name:
            return ''

        # Remove accents
        normalized = unicodedata.normalize('NFKD', name)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))

        # Lowercase
        normalized = normalized.lower().strip()

        # Common abbreviations
        abbreviations = {
            ' fc': '',
            ' cf': '',
            ' sc': '',
            ' ac': '',
            ' afc': '',
            ' utd': ' united',
            ' united': ' united',
            ' city': ' city',
            ' town': ' town',
        }

        for abbrev, full in abbreviations.items():
            normalized = normalized.replace(abbrev, full)

        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _find_or_create_team(self, api_name: str, league, logo_url: str = ''):
        """
        Find existing team or create new one.
        """
        from apps.teams.models import Team

        # 1. Try exact match by name
        team = Team.objects.filter(name=api_name, league=league).first()
        if team:
            if logo_url and not team.logo_url:
                team.logo_url = logo_url
                team.save(update_fields=['logo_url'])
            return team

        # 2. Try exact match by fd_name
        team = Team.objects.filter(fd_name=api_name, league=league).first()
        if team:
            team.name = api_name
            if logo_url and not team.logo_url:
                team.logo_url = logo_url
            team.save(update_fields=['name', 'logo_url'])
            return team

        # 3. Try normalized name matching
        normalized_api = self._normalize_team_name(api_name)

        for existing_team in Team.objects.filter(league=league):
            if self._normalize_team_name(existing_team.name) == normalized_api:
                if logo_url and not existing_team.logo_url:
                    existing_team.logo_url = logo_url
                    existing_team.save(update_fields=['logo_url'])
                return existing_team

            if existing_team.fd_name and self._normalize_team_name(existing_team.fd_name) == normalized_api:
                existing_team.name = api_name
                if logo_url and not existing_team.logo_url:
                    existing_team.logo_url = logo_url
                existing_team.save(update_fields=['name', 'logo_url'])
                return existing_team

        # 4. Create new team
        team = Team.objects.create(
            name=api_name,
            fd_name=api_name,
            league=league,
            logo_url=logo_url,
        )
        logger.info(f"Created new team: {api_name} in {league.name}")
        return team

    def sync_teams_with_logos(self, league_code: Optional[str] = None) -> Tuple[int, int]:
        """
        Sync teams with their logos.

        Args:
            league_code: Optional league code to filter

        Returns:
            Tuple of (created, updated)
        """
        from apps.leagues.models import League
        from apps.teams.models import Team

        created = 0
        updated = 0

        leagues_to_sync = {}
        if league_code and league_code in self.LEAGUES:
            leagues_to_sync[league_code] = self.LEAGUES[league_code]
        else:
            leagues_to_sync = self.LEAGUES

        for code, info in leagues_to_sync.items():
            try:
                fd_code = info['fd_code']
                data = self._request(f'/competitions/{fd_code}/teams')

                if not data:
                    continue

                teams = data.get('teams', [])

                # Get or create league
                league, _ = League.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': info['name'],
                        'country': info['country'],
                        'tier': info['tier'],
                    }
                )

                for team_data in teams:
                    team_name = team_data.get('name', 'Unknown')
                    team_crest = team_data.get('crest', '')
                    team_tla = team_data.get('tla', '')
                    team_founded = team_data.get('founded')
                    team_venue = team_data.get('venue', '')

                    existing_team = self._find_or_create_team(team_name, league, team_crest)

                    team_updated = False
                    if team_tla and not existing_team.code:
                        existing_team.code = team_tla
                        team_updated = True
                    if team_founded and not existing_team.founded:
                        existing_team.founded = team_founded
                        team_updated = True
                    if team_venue and not existing_team.stadium:
                        existing_team.stadium = team_venue
                        team_updated = True

                    if team_updated:
                        existing_team.save()
                        updated += 1
                    else:
                        created += 1

                logger.info(f"Synced teams for {code}")

            except Exception as e:
                logger.error(f"Error syncing teams for {code}: {e}")
                continue

        return created, updated

    @classmethod
    def is_configured(cls) -> bool:
        """Check if the API is properly configured."""
        return bool(getattr(settings, 'FOOTBALL_DATA_ORG_KEY', None))

    @classmethod
    def get_available_leagues(cls) -> Dict[str, Dict]:
        """Get list of supported leagues."""
        return cls.LEAGUES.copy()

    # Backward compatibility
    COMPETITIONS = LEAGUES

    @classmethod
    def get_available_competitions(cls) -> Dict[str, Dict]:
        """Get list of supported competitions."""
        return cls.get_available_leagues()
