"""
API-Football Provider (api-football.com)

REST API provider for real-time fixtures and results.
Free tier: 100 requests/day, covers all major leagues.

Requires API key - get one free at: https://dashboard.api-football.com/register

Free tier includes all endpoints:
- Fixtures, results, livescores
- Standings, teams, players
- All major leagues worldwide
"""
import logging
import time
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple

import requests
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


class FootballDataAPIProvider:
    """
    Provider for API-Football REST API.
    Provides real-time fixtures and results.

    Register for free at: https://dashboard.api-football.com/register
    """

    BASE_URL = "https://v3.football.api-sports.io"

    # League IDs mapping (API-Football uses numeric IDs)
    # Map our league codes to API-Football league IDs
    LEAGUES = {
        'E0': {'id': 39, 'name': 'Premier League', 'country': 'England', 'tier': 1},
        'SP1': {'id': 140, 'name': 'La Liga', 'country': 'Spain', 'tier': 1},
        'I1': {'id': 135, 'name': 'Serie A', 'country': 'Italy', 'tier': 1},
        'D1': {'id': 78, 'name': 'Bundesliga', 'country': 'Germany', 'tier': 1},
        'F1': {'id': 61, 'name': 'Ligue 1', 'country': 'France', 'tier': 1},
        'E1': {'id': 40, 'name': 'Championship', 'country': 'England', 'tier': 3},
        'N1': {'id': 88, 'name': 'Eredivisie', 'country': 'Netherlands', 'tier': 2},
        'P1': {'id': 94, 'name': 'Primeira Liga', 'country': 'Portugal', 'tier': 2},
        'B1': {'id': 144, 'name': 'Pro League', 'country': 'Belgium', 'tier': 2},
        'T1': {'id': 203, 'name': 'Super Lig', 'country': 'Turkey', 'tier': 2},
        'SC0': {'id': 179, 'name': 'Premiership', 'country': 'Scotland', 'tier': 4},
        'G1': {'id': 197, 'name': 'Super League', 'country': 'Greece', 'tier': 2},
        'CL': {'id': 2, 'name': 'Champions League', 'country': 'Europe', 'tier': 1},
        'EL': {'id': 3, 'name': 'Europa League', 'country': 'Europe', 'tier': 1},
    }

    # Reverse mapping: API league ID to our code
    ID_TO_CODE = {info['id']: code for code, info in LEAGUES.items()}

    # Status mapping from API to our model
    STATUS_MAPPING = {
        'TBD': 'scheduled',
        'NS': 'scheduled',      # Not Started
        '1H': 'live',           # First Half
        'HT': 'halftime',       # Halftime
        '2H': 'live',           # Second Half
        'ET': 'live',           # Extra Time
        'P': 'live',            # Penalties
        'FT': 'finished',       # Full Time
        'AET': 'finished',      # After Extra Time
        'PEN': 'finished',      # After Penalties
        'BT': 'live',           # Break Time
        'SUSP': 'postponed',    # Suspended
        'INT': 'postponed',     # Interrupted
        'PST': 'postponed',     # Postponed
        'CANC': 'cancelled',    # Cancelled
        'ABD': 'cancelled',     # Abandoned
        'AWD': 'finished',      # Awarded
        'WO': 'finished',       # Walkover
        'LIVE': 'live',
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the API provider.

        Args:
            api_key: API-Football API key. If not provided, uses settings.
        """
        self.api_key = api_key or getattr(settings, 'API_FOOTBALL_KEY', None)
        if not self.api_key:
            logger.warning("No API_FOOTBALL_KEY configured. API calls will fail.")

        self.session = requests.Session()
        self.session.headers.update({
            'x-apisports-key': self.api_key or '',
        })

        # Rate limiting: 100 requests per day for free tier
        # Be conservative - space out requests
        self.last_request_time = 0
        self.min_request_interval = 1  # 1 second between requests

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
            endpoint: API endpoint (e.g., '/fixtures')
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
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if data.get('errors'):
                errors = data['errors']
                if isinstance(errors, dict):
                    for key, msg in errors.items():
                        logger.error(f"API error: {key}: {msg}")
                else:
                    logger.error(f"API error: {errors}")
                return None

            return data

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning("Rate limit exceeded. Daily limit reached.")
                return None
            elif response.status_code == 403:
                logger.error("API key invalid")
            else:
                logger.error(f"HTTP error: {e}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def get_status(self) -> Optional[Dict]:
        """
        Get API account status and remaining requests.

        Returns:
            Account status info
        """
        data = self._request('/status')
        if data:
            return data.get('response', {})
        return None

    def get_leagues(self) -> Optional[List[Dict]]:
        """
        Get list of available leagues.

        Returns:
            List of league data
        """
        data = self._request('/leagues')
        if data:
            return data.get('response', [])
        return None

    def get_fixtures(
        self,
        league_id: Optional[int] = None,
        date_str: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        season: Optional[int] = None,
        status: Optional[str] = None,
        live: bool = False,
    ) -> Optional[List[Dict]]:
        """
        Get fixtures/matches.

        Args:
            league_id: League ID filter
            date_str: Specific date (YYYY-MM-DD)
            from_date: Start date filter (YYYY-MM-DD)
            to_date: End date filter (YYYY-MM-DD)
            season: Season year (e.g., 2025)
            status: Status filter (NS, LIVE, FT, etc.)
            live: If True, get only live matches

        Returns:
            List of fixture data
        """
        params = {}

        if live:
            params['live'] = 'all'
        else:
            if league_id:
                params['league'] = league_id
            if date_str:
                params['date'] = date_str
            if from_date:
                params['from'] = from_date
            if to_date:
                params['to'] = to_date
            if season:
                params['season'] = season
            if status:
                params['status'] = status

        data = self._request('/fixtures', params)
        if data:
            return data.get('response', [])
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

        # Get current season year
        season = today.year if today.month >= 7 else today.year - 1

        if league_code and league_code in self.LEAGUES:
            league_id = self.LEAGUES[league_code]['id']
            return self.get_fixtures(
                league_id=league_id,
                from_date=today.isoformat(),
                to_date=to_date.isoformat(),
                season=season
            )
        else:
            # Get fixtures for all supported leagues
            all_fixtures = []
            for code, info in self.LEAGUES.items():
                fixtures = self.get_fixtures(
                    league_id=info['id'],
                    from_date=today.isoformat(),
                    to_date=to_date.isoformat(),
                    season=season
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

        season = today.year if today.month >= 7 else today.year - 1

        if league_code and league_code in self.LEAGUES:
            league_id = self.LEAGUES[league_code]['id']
            return self.get_fixtures(
                league_id=league_id,
                from_date=from_date.isoformat(),
                to_date=today.isoformat(),
                season=season,
                status='FT-AET-PEN'  # Finished statuses
            )
        else:
            all_results = []
            for code, info in self.LEAGUES.items():
                results = self.get_fixtures(
                    league_id=info['id'],
                    from_date=from_date.isoformat(),
                    to_date=today.isoformat(),
                    season=season,
                    status='FT-AET-PEN'
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
        return self.get_fixtures(live=True)

    def get_standings(self, league_code: str, season: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Get current standings for a league.

        Args:
            league_code: Our league code
            season: Season year (default: current)

        Returns:
            Standings data
        """
        if league_code not in self.LEAGUES:
            return None

        league_id = self.LEAGUES[league_code]['id']

        if not season:
            today = date.today()
            season = today.year if today.month >= 7 else today.year - 1

        data = self._request('/standings', {
            'league': league_id,
            'season': season
        })

        if data:
            return data.get('response', [])
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
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match

        fixtures = self.get_upcoming_fixtures(league_code, days)
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
            for fixture in fixtures:
                try:
                    result = self._sync_fixture(fixture, current_season)
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
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match

        results = self.get_recent_results(league_code, days)
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
            for fixture in results:
                try:
                    result = self._sync_fixture(fixture, current_season)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                except Exception as e:
                    logger.error(f"Error syncing result: {e}")
                    continue

        logger.info(f"Results synced: {created} created, {updated} updated")
        return created, updated

    def _sync_fixture(self, fixture: Dict, season_code: str) -> Optional[str]:
        """
        Sync a single fixture to the database.

        Args:
            fixture: Fixture data from API
            season_code: Current season code

        Returns:
            'created', 'updated', or None
        """
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match

        # Get league info
        league_data = fixture.get('league', {})
        api_league_id = league_data.get('id')

        # Find our league code
        our_league_code = self.ID_TO_CODE.get(api_league_id)
        if not our_league_code:
            # League not in our supported list
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

        # Get teams with logos
        teams_data = fixture.get('teams', {})
        home_data = teams_data.get('home', {})
        away_data = teams_data.get('away', {})

        home_name = home_data.get('name', 'Unknown')
        away_name = away_data.get('name', 'Unknown')
        home_logo = home_data.get('logo', '')
        away_logo = away_data.get('logo', '')

        home_team, home_created = Team.objects.get_or_create(
            name=home_name,
            league=league,
            defaults={'fd_name': home_name, 'logo_url': home_logo}
        )
        # Update logo if not set
        if not home_created and not home_team.logo_url and home_logo:
            home_team.logo_url = home_logo
            home_team.save(update_fields=['logo_url'])

        away_team, away_created = Team.objects.get_or_create(
            name=away_name,
            league=league,
            defaults={'fd_name': away_name, 'logo_url': away_logo}
        )
        # Update logo if not set
        if not away_created and not away_team.logo_url and away_logo:
            away_team.logo_url = away_logo
            away_team.save(update_fields=['logo_url'])

        # Parse date and time
        fixture_info = fixture.get('fixture', {})
        timestamp = fixture_info.get('timestamp')

        if timestamp:
            match_dt = datetime.fromtimestamp(timestamp)
            match_date = match_dt.date()
            kickoff_time = match_dt.time()
        else:
            date_str = fixture_info.get('date', '')
            if date_str:
                match_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                match_date = match_dt.date()
                kickoff_time = match_dt.time()
            else:
                return None

        # Create API match ID for reference (not used as primary key)
        api_id = fixture_info.get('id')
        api_match_id = f"apifb_{api_id}" if api_id else ""

        # Get score if available
        goals = fixture.get('goals', {})
        score_data = fixture.get('score', {})

        home_score = goals.get('home')
        away_score = goals.get('away')

        # Halftime score
        halftime = score_data.get('halftime', {})
        home_ht = halftime.get('home')
        away_ht = halftime.get('away')

        # Map status
        status_data = fixture_info.get('status', {})
        api_status = status_data.get('short', 'NS')
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

        # Get matchweek/round
        round_str = league_data.get('round', '')
        matchweek = None
        if round_str:
            # Extract number from strings like "Regular Season - 15"
            import re
            match = re.search(r'\d+', round_str)
            if match:
                matchweek = int(match.group())

        # Create or update match using natural key (prevents duplicates)
        match, match_created = Match.objects.update_or_create(
            season=db_season,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            defaults={
                'kickoff_time': kickoff_time,
                'matchweek': matchweek,
                'home_score': home_score,
                'away_score': away_score,
                'home_halftime_score': home_ht,
                'away_halftime_score': away_ht,
                'status': status,
                'fd_match_id': api_match_id,  # Store API ID for reference
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

        for fixture in live_matches:
            try:
                fixture_info = fixture.get('fixture', {})
                teams_data = fixture.get('teams', {})
                goals = fixture.get('goals', {})

                # Get match date
                date_str = fixture_info.get('date')
                if date_str:
                    match_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    match_date = match_dt.date()
                else:
                    match_date = date.today()

                # Get team names
                home_name = teams_data.get('home', {}).get('name', '')
                away_name = teams_data.get('away', {}).get('name', '')

                # Try to find match by teams and date (more reliable than fd_match_id)
                from apps.teams.models import Team
                home_team = Team.objects.filter(name__icontains=home_name.split()[0]).first()
                away_team = Team.objects.filter(name__icontains=away_name.split()[0]).first()

                if home_team and away_team:
                    rows = Match.objects.filter(
                        home_team=home_team,
                        away_team=away_team,
                        match_date=match_date
                    ).update(
                        home_score=goals.get('home'),
                        away_score=goals.get('away'),
                        status=Match.Status.LIVE,
                    )
                else:
                    # Fallback to fd_match_id
                    api_id = fixture_info.get('id')
                    rows = Match.objects.filter(fd_match_id=f"apifb_{api_id}").update(
                        home_score=goals.get('home'),
                        away_score=goals.get('away'),
                        status=Match.Status.LIVE,
                    )

                if rows > 0:
                    updated += 1

            except Exception as e:
                logger.error(f"Error updating live match: {e}")
                continue

        logger.info(f"Updated {updated} live matches")
        return updated

    def get_teams(self, league_id: int, season: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Get teams for a league.

        Args:
            league_id: API-Football league ID
            season: Season year (default: current)

        Returns:
            List of team data with logos
        """
        if not season:
            today = date.today()
            season = today.year if today.month >= 7 else today.year - 1

        data = self._request('/teams', {
            'league': league_id,
            'season': season
        })

        if data:
            return data.get('response', [])
        return None

    def sync_teams_with_logos(self, league_code: Optional[str] = None) -> Tuple[int, int]:
        """
        Sync teams with their logos from API-Football.

        Args:
            league_code: Optional league code to filter

        Returns:
            Tuple of (created, updated)
        """
        from apps.leagues.models import League
        from apps.teams.models import Team

        today = date.today()
        season = today.year if today.month >= 7 else today.year - 1

        created = 0
        updated = 0

        leagues_to_sync = {}
        if league_code and league_code in self.LEAGUES:
            leagues_to_sync[league_code] = self.LEAGUES[league_code]
        else:
            leagues_to_sync = self.LEAGUES

        for code, info in leagues_to_sync.items():
            try:
                teams = self.get_teams(info['id'], season)
                if not teams:
                    continue

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
                    team_info = team_data.get('team', {})
                    team_name = team_info.get('name', 'Unknown')
                    team_logo = team_info.get('logo', '')
                    team_code = team_info.get('code', '')
                    team_founded = team_info.get('founded')

                    venue = team_data.get('venue', {})
                    stadium = venue.get('name', '')
                    stadium_capacity = venue.get('capacity')
                    city = venue.get('city', '')

                    team, team_created = Team.objects.update_or_create(
                        name=team_name,
                        league=league,
                        defaults={
                            'fd_name': team_name,
                            'logo_url': team_logo,
                            'code': team_code or '',
                            'founded': team_founded,
                            'stadium': stadium,
                            'stadium_capacity': stadium_capacity,
                            'city': city,
                        }
                    )

                    if team_created:
                        created += 1
                    else:
                        updated += 1

                logger.info(f"Synced teams for {code}: {created} created, {updated} updated")

            except Exception as e:
                logger.error(f"Error syncing teams for {code}: {e}")
                continue

        logger.info(f"Total teams synced: {created} created, {updated} updated")
        return created, updated

    @classmethod
    def is_configured(cls) -> bool:
        """Check if the API is properly configured."""
        return bool(getattr(settings, 'API_FOOTBALL_KEY', None))

    @classmethod
    def get_available_leagues(cls) -> Dict[str, Dict]:
        """Get list of supported leagues."""
        return cls.LEAGUES.copy()

    # Alias for backward compatibility
    COMPETITIONS = LEAGUES

    @classmethod
    def get_available_competitions(cls) -> Dict[str, Dict]:
        """Get list of supported competitions (alias for get_available_leagues)."""
        return cls.get_available_leagues()
