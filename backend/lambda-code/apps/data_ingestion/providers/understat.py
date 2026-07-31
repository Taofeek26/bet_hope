"""
Understat Provider

Scrapes advanced statistics (xG, xGA, xPTS) from understat.com
Uses the understat Python library for data extraction.

Covers 6 major leagues:
- Premier League (England)
- La Liga (Spain)
- Serie A (Italy)
- Bundesliga (Germany)
- Ligue 1 (France)
- Russian Premier League (Russia)

Data includes:
- Expected Goals (xG)
- Expected Goals Against (xGA)
- Expected Points (xPTS)
- Shot data with xG per shot
- Player-level xG statistics
"""
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Try to import understat, handle if not installed
try:
    import understat
    import aiohttp
    UNDERSTAT_AVAILABLE = True
except ImportError:
    UNDERSTAT_AVAILABLE = False
    logger.warning("understat package not installed. Run: pip install understat aiohttp")


class UnderstatProvider:
    """
    Provider for Understat xG data.

    Uses async scraping to fetch expected goals data.
    """

    # League name mapping (understat uses full names)
    LEAGUES = {
        'EPL': {'name': 'Premier League', 'country': 'England', 'fd_code': 'E0'},
        'La_Liga': {'name': 'La Liga', 'country': 'Spain', 'fd_code': 'SP1'},
        'Serie_A': {'name': 'Serie A', 'country': 'Italy', 'fd_code': 'I1'},
        'Bundesliga': {'name': 'Bundesliga', 'country': 'Germany', 'fd_code': 'D1'},
        'Ligue_1': {'name': 'Ligue 1', 'country': 'France', 'fd_code': 'F1'},
        'RFPL': {'name': 'Russian Premier League', 'country': 'Russia', 'fd_code': None},
    }

    # Seasons available (understat has data from 2014-15)
    SEASONS = [
        2024, 2023, 2022, 2021, 2020,
        2019, 2018, 2017, 2016, 2015, 2014
    ]

    def __init__(self):
        """Initialize the provider."""
        if not UNDERSTAT_AVAILABLE:
            raise ImportError(
                "understat package required. Install with: pip install understat aiohttp"
            )

    async def _fetch_league_data(
        self,
        league: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Fetch league data for a season.

        Args:
            league: League name (e.g., 'EPL')
            season: Season year (e.g., 2023 for 2023-24)

        Returns:
            Dict with teams and matches data
        """
        async with aiohttp.ClientSession() as session:
            us = understat.Understat(session)

            try:
                # Fetch team statistics
                teams = await us.get_league_table(league, season)

                # Fetch match results with xG
                results = await us.get_league_results(league, season)

                # Fetch fixtures (upcoming matches)
                fixtures = await us.get_league_fixtures(league, season)

                return {
                    'teams': teams,
                    'results': results,
                    'fixtures': fixtures,
                    'season': season,
                    'league': league,
                }

            except Exception as e:
                logger.error(f"Error fetching {league}/{season}: {e}")
                return None

    def fetch_league_data(self, league: str, season: int) -> Dict[str, Any]:
        """
        Synchronous wrapper for fetching league data.

        Args:
            league: League name
            season: Season year

        Returns:
            Dict with league data
        """
        return asyncio.run(self._fetch_league_data(league, season))

    async def _fetch_team_data(
        self,
        team_name: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Fetch detailed team data including shot data.

        Args:
            team_name: Team name as used by understat
            season: Season year

        Returns:
            Dict with team shots and player data
        """
        async with aiohttp.ClientSession() as session:
            us = understat.Understat(session)

            try:
                # Get team shots data
                shots = await us.get_team_stats(team_name, season)

                # Get team players
                players = await us.get_team_players(team_name, season)

                return {
                    'shots': shots,
                    'players': players,
                    'team': team_name,
                    'season': season,
                }

            except Exception as e:
                logger.error(f"Error fetching team {team_name}/{season}: {e}")
                return None

    def fetch_team_data(self, team_name: str, season: int) -> Dict[str, Any]:
        """Synchronous wrapper for team data."""
        return asyncio.run(self._fetch_team_data(team_name, season))

    async def _fetch_player_data(self, player_id: int) -> Dict[str, Any]:
        """
        Fetch detailed player data.

        Args:
            player_id: Understat player ID

        Returns:
            Dict with player statistics
        """
        async with aiohttp.ClientSession() as session:
            us = understat.Understat(session)

            try:
                # Get player shots
                shots = await us.get_player_shots(player_id)

                # Get player match data
                matches = await us.get_player_matches(player_id)

                # Get grouped stats
                grouped = await us.get_player_grouped_stats(player_id)

                return {
                    'shots': shots,
                    'matches': matches,
                    'grouped_stats': grouped,
                    'player_id': player_id,
                }

            except Exception as e:
                logger.error(f"Error fetching player {player_id}: {e}")
                return None

    def fetch_player_data(self, player_id: int) -> Dict[str, Any]:
        """Synchronous wrapper for player data."""
        return asyncio.run(self._fetch_player_data(player_id))

    def sync_to_database(
        self,
        league: str,
        season: int,
        data: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Sync understat data to database.

        Args:
            league: League name
            season: Season year
            data: Data from fetch_league_data

        Returns:
            Dict with sync statistics
        """
        from apps.leagues.models import League as LeagueModel, Season
        from apps.teams.models import Team, TeamSeasonStats
        from apps.matches.models import Match

        if not data:
            return {'teams_updated': 0, 'matches_updated': 0}

        stats = {
            'teams_updated': 0,
            'matches_updated': 0,
        }

        league_info = self.LEAGUES.get(league)
        if not league_info:
            logger.error(f"Unknown league: {league}")
            return stats

        # Get league and season from database
        try:
            db_league = LeagueModel.objects.get(code=league_info.get('fd_code'))
        except LeagueModel.DoesNotExist:
            logger.warning(f"League {league} not in database, skipping xG sync")
            return stats

        season_code = f"{str(season)[-2:]}{str(season + 1)[-2:]}"
        try:
            db_season = Season.objects.get(league=db_league, code=season_code)
        except Season.DoesNotExist:
            logger.warning(f"Season {season_code} not in database, skipping xG sync")
            return stats

        # Update team xG statistics
        with transaction.atomic():
            for team_data in data.get('teams', []):
                try:
                    team_name = team_data.get('title', '')

                    # Try to find matching team
                    team = Team.objects.filter(
                        league=db_league,
                        name__icontains=team_name.split()[0]  # Match first word
                    ).first()

                    if not team:
                        continue

                    # Update or create season stats with xG
                    TeamSeasonStats.objects.update_or_create(
                        team=team,
                        season=db_season,
                        defaults={
                            'xg_for': self._safe_decimal(team_data.get('xG')),
                            'xg_against': self._safe_decimal(team_data.get('xGA')),
                            'xpts': self._safe_decimal(team_data.get('xpts')),
                            'npxg': self._safe_decimal(team_data.get('npxG')),
                            'npxg_against': self._safe_decimal(team_data.get('npxGA')),
                        }
                    )
                    stats['teams_updated'] += 1

                except Exception as e:
                    logger.error(f"Error updating team {team_data}: {e}")
                    continue

            # Update match xG values
            for match_data in data.get('results', []):
                try:
                    match_date = datetime.strptime(
                        match_data.get('datetime', '')[:10],
                        '%Y-%m-%d'
                    ).date()

                    home_team_name = match_data.get('h', {}).get('title', '')
                    away_team_name = match_data.get('a', {}).get('title', '')

                    # Find the match
                    match = Match.objects.filter(
                        season=db_season,
                        match_date=match_date,
                        home_team__name__icontains=home_team_name.split()[0],
                        away_team__name__icontains=away_team_name.split()[0],
                    ).first()

                    if match:
                        match.home_xg = self._safe_decimal(match_data.get('xG', {}).get('h'))
                        match.away_xg = self._safe_decimal(match_data.get('xG', {}).get('a'))
                        match.save(update_fields=['home_xg', 'away_xg'])
                        stats['matches_updated'] += 1

                except Exception as e:
                    logger.error(f"Error updating match {match_data}: {e}")
                    continue

        logger.info(f"Synced xG for {league}/{season}: {stats}")
        return stats

    def sync_all(
        self,
        seasons: Optional[List[int]] = None,
        leagues: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Sync all leagues and seasons.

        Args:
            seasons: List of seasons to sync
            leagues: List of leagues to sync

        Returns:
            Dict with total sync statistics
        """
        seasons = seasons or self.SEASONS[:5]  # Default to last 5 seasons
        leagues = leagues or ['EPL', 'La_Liga', 'Serie_A', 'Bundesliga', 'Ligue_1']

        total_stats = {
            'teams_updated': 0,
            'matches_updated': 0,
            'errors': 0,
        }

        for league in leagues:
            for season in seasons:
                try:
                    logger.info(f"Fetching xG data for {league}/{season}")
                    data = self.fetch_league_data(league, season)

                    if data:
                        stats = self.sync_to_database(league, season, data)
                        total_stats['teams_updated'] += stats['teams_updated']
                        total_stats['matches_updated'] += stats['matches_updated']

                except Exception as e:
                    logger.error(f"Error syncing {league}/{season}: {e}")
                    total_stats['errors'] += 1

        logger.info(f"xG sync complete: {total_stats}")
        return total_stats

    def _safe_decimal(self, value) -> Optional[Decimal]:
        """Safely convert to Decimal."""
        if value is None:
            return None
        try:
            return Decimal(str(value)).quantize(Decimal('0.001'))
        except (ValueError, TypeError):
            return None


class FBrefProvider:
    """
    Alternative provider using FBref data via soccerdata package.

    Provides additional statistics not available from other sources.
    Note: Requires soccerdata package: pip install soccerdata
    """

    LEAGUES = {
        'ENG-Premier League': {'country': 'England', 'fd_code': 'E0'},
        'ESP-La Liga': {'country': 'Spain', 'fd_code': 'SP1'},
        'ITA-Serie A': {'country': 'Italy', 'fd_code': 'I1'},
        'GER-Bundesliga': {'country': 'Germany', 'fd_code': 'D1'},
        'FRA-Ligue 1': {'country': 'France', 'fd_code': 'F1'},
    }

    def __init__(self):
        """Initialize the provider."""
        try:
            import soccerdata as sd
            self.sd = sd
        except ImportError:
            raise ImportError(
                "soccerdata package required. Install with: pip install soccerdata"
            )

    def fetch_season_stats(
        self,
        league: str,
        season: str
    ) -> Dict[str, Any]:
        """
        Fetch season statistics from FBref.

        Args:
            league: League name (e.g., 'ENG-Premier League')
            season: Season string (e.g., '2023-2024')

        Returns:
            Dict with various statistics DataFrames
        """
        try:
            fbref = self.sd.FBref(leagues=league, seasons=season)

            return {
                'schedule': fbref.read_schedule(),
                'standings': fbref.read_standings(),
                'team_season_stats': fbref.read_team_season_stats(),
                'player_season_stats': fbref.read_player_season_stats(),
            }

        except Exception as e:
            logger.error(f"Error fetching FBref data for {league}/{season}: {e}")
            return None

    def fetch_match_stats(
        self,
        league: str,
        season: str
    ) -> Dict[str, Any]:
        """
        Fetch detailed match statistics.

        Args:
            league: League name
            season: Season string

        Returns:
            Dict with match-level statistics
        """
        try:
            fbref = self.sd.FBref(leagues=league, seasons=season)

            return {
                'match_stats': fbref.read_team_match_stats(),
                'lineups': fbref.read_lineup(),
            }

        except Exception as e:
            logger.error(f"Error fetching FBref match stats: {e}")
            return None
