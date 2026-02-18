"""
Football-Data.co.uk CSV Provider

Downloads and parses free CSV data from football-data.co.uk
Covers 20+ leagues with 10+ years of historical data.
No API key required - completely free!

Data includes:
- Match results (home/away scores)
- Match statistics (shots, corners, fouls, cards)
- Betting odds (can be used for implied probabilities)

CSV URL format: https://www.football-data.co.uk/mmz4281/{season}/{league}.csv
Example: https://www.football-data.co.uk/mmz4281/2324/E0.csv
"""
import logging
import pandas as pd
import requests
from io import StringIO, BytesIO
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class FootballDataProvider:
    """
    Provider for Football-Data.co.uk CSV data.
    """

    BASE_URL = "https://www.football-data.co.uk/mmz4281"
    FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"

    # League codes mapping - 20 leagues supported by Football-Data.co.uk
    LEAGUES = {
        # Top 5 European Leagues (Tier 1)
        'E0': {'name': 'Premier League', 'country': 'England', 'tier': 1},
        'SP1': {'name': 'La Liga', 'country': 'Spain', 'tier': 1},
        'I1': {'name': 'Serie A', 'country': 'Italy', 'tier': 1},
        'D1': {'name': 'Bundesliga', 'country': 'Germany', 'tier': 1},
        'F1': {'name': 'Ligue 1', 'country': 'France', 'tier': 1},

        # Other Major European Leagues (Tier 2)
        'N1': {'name': 'Eredivisie', 'country': 'Netherlands', 'tier': 2},
        'B1': {'name': 'Pro League', 'country': 'Belgium', 'tier': 2},
        'P1': {'name': 'Primeira Liga', 'country': 'Portugal', 'tier': 2},
        'T1': {'name': 'Super Lig', 'country': 'Turkey', 'tier': 2},
        'G1': {'name': 'Super League', 'country': 'Greece', 'tier': 2},
        'SC0': {'name': 'Scottish Premiership', 'country': 'Scotland', 'tier': 2},

        # Second Division Leagues (Tier 3)
        'E1': {'name': 'Championship', 'country': 'England', 'tier': 3},
        'SP2': {'name': 'La Liga 2', 'country': 'Spain', 'tier': 3},
        'I2': {'name': 'Serie B', 'country': 'Italy', 'tier': 3},
        'D2': {'name': '2. Bundesliga', 'country': 'Germany', 'tier': 3},
        'F2': {'name': 'Ligue 2', 'country': 'France', 'tier': 3},

        # Additional Leagues (Tier 4)
        'E2': {'name': 'League One', 'country': 'England', 'tier': 4},
        'E3': {'name': 'League Two', 'country': 'England', 'tier': 4},
        'SC1': {'name': 'Scottish Championship', 'country': 'Scotland', 'tier': 4},
        'SC2': {'name': 'Scottish League One', 'country': 'Scotland', 'tier': 4},
    }

    # Column mappings from CSV to our model fields
    COLUMN_MAPPING = {
        # Core match data
        'Date': 'match_date',
        'Time': 'kickoff_time',
        'HomeTeam': 'home_team',
        'AwayTeam': 'away_team',
        'FTHG': 'home_score',  # Full Time Home Goals
        'FTAG': 'away_score',  # Full Time Away Goals
        'FTR': 'outcome',      # Full Time Result (H/D/A)
        'HTHG': 'home_halftime_score',
        'HTAG': 'away_halftime_score',

        # Match statistics
        'HS': 'shots_home',
        'AS': 'shots_away',
        'HST': 'shots_on_target_home',
        'AST': 'shots_on_target_away',
        'HC': 'corners_home',
        'AC': 'corners_away',
        'HF': 'fouls_home',
        'AF': 'fouls_away',
        'HY': 'yellow_cards_home',
        'AY': 'yellow_cards_away',
        'HR': 'red_cards_home',
        'AR': 'red_cards_away',

        # Betting odds (average)
        'AvgH': 'home_odds',
        'AvgD': 'draw_odds',
        'AvgA': 'away_odds',
        'Avg>2.5': 'over_25_odds',
        'Avg<2.5': 'under_25_odds',

        # Alternative odds columns (some seasons use different names)
        'BbAvH': 'home_odds',
        'BbAvD': 'draw_odds',
        'BbAvA': 'away_odds',
        'BbAv>2.5': 'over_25_odds',
        'BbAv<2.5': 'under_25_odds',

        # Pinnacle odds (if available, often most accurate)
        'PSH': 'pinnacle_home',
        'PSD': 'pinnacle_draw',
        'PSA': 'pinnacle_away',
    }

    # Seasons to download - Football-Data.co.uk has data from 1993+
    # Format: YYZZ where 20YY-20ZZ or 19YY-19ZZ for pre-2000
    SEASONS = [
        # Current + Recent (2020s)
        '2526', '2425', '2324', '2223', '2122', '2021',
        # 2010s
        '1920', '1819', '1718', '1617', '1516',
        '1415', '1314', '1213', '1112', '1011',
        # 2000s
        '0910', '0809', '0708', '0607', '0506',
        '0405', '0304', '0203', '0102', '0001',
        # 1990s (where available)
        '9900', '9899', '9798', '9697', '9596', '9495', '9394',
    ]

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the provider.

        Args:
            cache_dir: Directory to cache downloaded CSV files
        """
        self.cache_dir = cache_dir or Path(settings.RAW_DATA_DIR) / 'football_data'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_csv_url(self, league_code: str, season: str) -> str:
        """
        Get the URL for a league's CSV file.

        Args:
            league_code: League code (e.g., 'E0' for Premier League)
            season: Season code (e.g., '2324' for 2023-24)

        Returns:
            Full URL to the CSV file
        """
        return f"{self.BASE_URL}/{season}/{league_code}.csv"

    def download_csv(
        self,
        league_code: str,
        season: str,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Download and parse CSV data for a league/season.

        Args:
            league_code: League code
            season: Season code
            use_cache: Whether to use cached files

        Returns:
            DataFrame with match data or None if failed
        """
        cache_file = self.cache_dir / f"{league_code}_{season}.csv"

        # Check cache first
        if use_cache and cache_file.exists():
            logger.info(f"Loading from cache: {cache_file}")
            try:
                df = pd.read_csv(cache_file, encoding='utf-8', on_bad_lines='skip')
                return self._clean_dataframe(df)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}, downloading fresh...")

        # Download from web
        url = self.get_csv_url(league_code, season)
        logger.info(f"Downloading: {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse CSV
            df = pd.read_csv(
                StringIO(response.text),
                encoding='utf-8',
                on_bad_lines='skip'
            )

            # Save to cache
            df.to_csv(cache_file, index=False)
            logger.info(f"Saved to cache: {cache_file}")

            return self._clean_dataframe(df)

        except requests.exceptions.RequestException as e:
            logger.error(f"Download failed for {league_code}/{season}: {e}")
            return None
        except Exception as e:
            logger.error(f"Parse failed for {league_code}/{season}: {e}")
            return None

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize the DataFrame.
        """
        if df is None or df.empty:
            return df

        # Remove empty rows
        df = df.dropna(how='all')

        # Strip whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]

        # Parse date column
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')

        return df

    def download_all_leagues(
        self,
        seasons: Optional[List[str]] = None,
        leagues: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Download data for all leagues and seasons.

        Args:
            seasons: List of seasons to download (default: all)
            leagues: List of league codes to download (default: all)

        Returns:
            Nested dict: {league_code: {season: DataFrame}}
        """
        seasons = seasons or self.SEASONS
        leagues = leagues or list(self.LEAGUES.keys())

        all_data = {}
        total = len(leagues) * len(seasons)
        downloaded = 0

        for league_code in leagues:
            all_data[league_code] = {}

            for season in seasons:
                df = self.download_csv(league_code, season)
                if df is not None and not df.empty:
                    all_data[league_code][season] = df
                    downloaded += 1
                    logger.info(f"Progress: {downloaded}/{total}")

        return all_data

    def sync_to_database(
        self,
        league_code: str,
        season: str,
        df: pd.DataFrame
    ) -> Tuple[int, int]:
        """
        Sync DataFrame to database models.

        Args:
            league_code: League code
            season: Season code
            df: DataFrame with match data

        Returns:
            Tuple of (matches_created, matches_updated)
        """
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match, MatchStatistics, MatchOdds

        if df is None or df.empty:
            return 0, 0

        created = 0
        updated = 0

        # Get or create league
        league_info = self.LEAGUES.get(league_code, {})
        league, _ = League.objects.get_or_create(
            code=league_code,
            defaults={
                'name': league_info.get('name', league_code),
                'country': league_info.get('country', 'Unknown'),
                'tier': league_info.get('tier', 2),
            }
        )

        # Get or create season - handle both 19XX and 20XX years
        start_year = int(season[:2])
        end_year = int(season[2:])
        # Determine century: if start > 90, it's 1990s; otherwise 2000s
        if start_year > 90:
            season_name = f"19{season[:2]}-{season[2:]}"
        else:
            season_name = f"20{season[:2]}-{season[2:]}"

        db_season, _ = Season.objects.get_or_create(
            league=league,
            code=season,
            defaults={'name': season_name}
        )

        # Team cache
        team_cache = {}

        def get_or_create_team(name: str) -> Team:
            if name not in team_cache:
                team, _ = Team.objects.get_or_create(
                    fd_name=name,
                    league=league,
                    defaults={'name': name}
                )
                team_cache[name] = team
            return team_cache[name]

        # Process each match
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    # Skip rows without essential data
                    if pd.isna(row.get('HomeTeam')) or pd.isna(row.get('AwayTeam')):
                        continue

                    home_team = get_or_create_team(str(row['HomeTeam']))
                    away_team = get_or_create_team(str(row['AwayTeam']))

                    # Parse date
                    match_date = row.get('Date')
                    if pd.isna(match_date):
                        continue
                    if isinstance(match_date, str):
                        match_date = datetime.strptime(match_date, '%d/%m/%Y').date()
                    elif isinstance(match_date, pd.Timestamp):
                        match_date = match_date.date()

                    # Create unique identifier
                    match_id = f"{league_code}_{season}_{match_date}_{home_team.fd_name}_{away_team.fd_name}"

                    # Get or create match
                    match, match_created = Match.objects.update_or_create(
                        fd_match_id=match_id,
                        defaults={
                            'season': db_season,
                            'home_team': home_team,
                            'away_team': away_team,
                            'match_date': match_date,
                            'home_score': self._safe_int(row.get('FTHG')),
                            'away_score': self._safe_int(row.get('FTAG')),
                            'home_halftime_score': self._safe_int(row.get('HTHG')),
                            'away_halftime_score': self._safe_int(row.get('HTAG')),
                            'status': Match.Status.FINISHED if not pd.isna(row.get('FTHG')) else Match.Status.SCHEDULED,
                        }
                    )

                    if match_created:
                        created += 1
                    else:
                        updated += 1

                    # Create/update statistics if available
                    if not pd.isna(row.get('HS')):
                        MatchStatistics.objects.update_or_create(
                            match=match,
                            defaults={
                                'shots_home': self._safe_int(row.get('HS')),
                                'shots_away': self._safe_int(row.get('AS')),
                                'shots_on_target_home': self._safe_int(row.get('HST')),
                                'shots_on_target_away': self._safe_int(row.get('AST')),
                                'corners_home': self._safe_int(row.get('HC')),
                                'corners_away': self._safe_int(row.get('AC')),
                                'fouls_home': self._safe_int(row.get('HF')),
                                'fouls_away': self._safe_int(row.get('AF')),
                                'yellow_cards_home': self._safe_int(row.get('HY')),
                                'yellow_cards_away': self._safe_int(row.get('AY')),
                                'red_cards_home': self._safe_int(row.get('HR')),
                                'red_cards_away': self._safe_int(row.get('AR')),
                            }
                        )

                    # Create/update odds if available
                    home_odds = self._safe_decimal(row.get('AvgH') or row.get('BbAvH') or row.get('PSH'))
                    if home_odds:
                        MatchOdds.objects.update_or_create(
                            match=match,
                            defaults={
                                'home_odds': home_odds,
                                'draw_odds': self._safe_decimal(row.get('AvgD') or row.get('BbAvD') or row.get('PSD')),
                                'away_odds': self._safe_decimal(row.get('AvgA') or row.get('BbAvA') or row.get('PSA')),
                                'over_25_odds': self._safe_decimal(row.get('Avg>2.5') or row.get('BbAv>2.5')),
                                'under_25_odds': self._safe_decimal(row.get('Avg<2.5') or row.get('BbAv<2.5')),
                            }
                        )

                except Exception as e:
                    logger.error(f"Error processing row: {e}")
                    continue

        # Update season stats
        db_season.total_matches = Match.objects.filter(season=db_season).count()
        db_season.matches_played = Match.objects.filter(
            season=db_season,
            status=Match.Status.FINISHED
        ).count()
        db_season.save()

        logger.info(f"Synced {league_code}/{season}: {created} created, {updated} updated")
        return created, updated

    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int."""
        if pd.isna(value):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def _safe_decimal(self, value) -> Optional[Decimal]:
        """Safely convert to Decimal."""
        if pd.isna(value):
            return None
        try:
            return Decimal(str(value)).quantize(Decimal('0.001'))
        except (ValueError, TypeError):
            return None

    def sync_all(
        self,
        seasons: Optional[List[str]] = None,
        leagues: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Download and sync all data to database.

        Returns:
            Dict with sync statistics
        """
        seasons = seasons or self.SEASONS
        leagues = leagues or list(self.LEAGUES.keys())

        stats = {
            'total_created': 0,
            'total_updated': 0,
            'leagues_processed': 0,
            'seasons_processed': 0,
            'errors': 0,
        }

        for league_code in leagues:
            for season in seasons:
                try:
                    df = self.download_csv(league_code, season)
                    if df is not None and not df.empty:
                        created, updated = self.sync_to_database(league_code, season, df)
                        stats['total_created'] += created
                        stats['total_updated'] += updated
                        stats['seasons_processed'] += 1
                except Exception as e:
                    logger.error(f"Sync failed for {league_code}/{season}: {e}")
                    stats['errors'] += 1

            stats['leagues_processed'] += 1

        logger.info(f"Sync complete: {stats}")
        return stats

    def download_fixtures(self, use_cache: bool = False) -> Optional[pd.DataFrame]:
        """
        Download upcoming fixtures from Football-Data.co.uk.

        Returns:
            DataFrame with fixture data
        """
        cache_file = self.cache_dir / 'fixtures.csv'

        # Check cache (short TTL for fixtures - 1 hour)
        if use_cache and cache_file.exists():
            import time
            file_age = time.time() - cache_file.stat().st_mtime
            if file_age < 3600:  # 1 hour
                logger.info("Using cached fixtures")
                return pd.read_csv(cache_file)

        logger.info(f"Downloading fixtures from {self.FIXTURES_URL}")

        try:
            response = requests.get(
                self.FIXTURES_URL,
                timeout=30,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response.raise_for_status()

            # Use BytesIO with utf-8-sig to handle BOM
            df = pd.read_csv(BytesIO(response.content), encoding='utf-8-sig')

            if df is None or df.empty:
                logger.warning("Fixtures CSV is empty")
                return None

            # Cache the file
            df.to_csv(cache_file, index=False)
            logger.info(f"Downloaded {len(df)} fixtures")

            return self._clean_dataframe(df)

        except Exception as e:
            logger.error(f"Failed to download fixtures: {e}")
            return None

    def sync_fixtures(self) -> Tuple[int, int]:
        """
        Sync upcoming fixtures to database.

        Returns:
            Tuple of (created, updated)
        """
        from apps.leagues.models import League, Season
        from apps.teams.models import Team
        from apps.matches.models import Match, MatchOdds

        df = self.download_fixtures()
        if df is None or df.empty:
            return 0, 0

        created = 0
        updated = 0

        # Get current season code
        from datetime import date
        today = date.today()
        year = today.year
        month = today.month
        if month >= 8:
            current_season = f"{str(year)[2:]}{str(year + 1)[2:]}"
        else:
            current_season = f"{str(year - 1)[2:]}{str(year)[2:]}"

        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    # Get league code (Div column)
                    div = row.get('Div', '')
                    if not div or div not in self.LEAGUES:
                        continue

                    # Get or create league
                    league_info = self.LEAGUES.get(div, {})
                    league, _ = League.objects.get_or_create(
                        code=div,
                        defaults={
                            'name': league_info.get('name', div),
                            'country': league_info.get('country', 'Unknown'),
                            'tier': league_info.get('tier', 2),
                        }
                    )

                    # Get or create season
                    season_name = f"20{current_season[:2]}-{current_season[2:]}"
                    db_season, _ = Season.objects.get_or_create(
                        league=league,
                        code=current_season,
                        defaults={'name': season_name}
                    )

                    # Parse date and time
                    date_str = row.get('Date', '')
                    time_str = row.get('Time', '')

                    if not date_str:
                        continue

                    match_date = pd.to_datetime(date_str, dayfirst=True).date()

                    kickoff_time = None
                    if time_str and pd.notna(time_str):
                        try:
                            kickoff_time = pd.to_datetime(time_str).time()
                        except:
                            pass

                    # Get teams
                    home_name = row.get('HomeTeam', '')
                    away_name = row.get('AwayTeam', '')

                    if not home_name or not away_name:
                        continue

                    home_team, _ = Team.objects.get_or_create(
                        fd_name=home_name,
                        league=league,
                        defaults={'name': home_name}
                    )

                    away_team, _ = Team.objects.get_or_create(
                        fd_name=away_name,
                        league=league,
                        defaults={'name': away_name}
                    )

                    # Create unique ID
                    match_id = f"{div}_{current_season}_{match_date}_{home_name}_{away_name}"

                    # Create or update match
                    match, match_created = Match.objects.update_or_create(
                        fd_match_id=match_id,
                        defaults={
                            'season': db_season,
                            'home_team': home_team,
                            'away_team': away_team,
                            'match_date': match_date,
                            'kickoff_time': kickoff_time,
                            'status': Match.Status.SCHEDULED,
                        }
                    )

                    if match_created:
                        created += 1
                    else:
                        updated += 1

                    # Add odds if available
                    home_odds = self._safe_decimal(
                        row.get('AvgH') or row.get('BbAvH') or row.get('PSH') or row.get('B365H')
                    )
                    if home_odds:
                        MatchOdds.objects.update_or_create(
                            match=match,
                            defaults={
                                'home_odds': home_odds,
                                'draw_odds': self._safe_decimal(
                                    row.get('AvgD') or row.get('BbAvD') or row.get('PSD') or row.get('B365D')
                                ),
                                'away_odds': self._safe_decimal(
                                    row.get('AvgA') or row.get('BbAvA') or row.get('PSA') or row.get('B365A')
                                ),
                                'over_25_odds': self._safe_decimal(row.get('Avg>2.5') or row.get('BbAv>2.5')),
                                'under_25_odds': self._safe_decimal(row.get('Avg<2.5') or row.get('BbAv<2.5')),
                                'bookmaker': 'Average',
                            }
                        )

                except Exception as e:
                    logger.error(f"Error processing fixture: {e}")
                    continue

        logger.info(f"Fixtures synced: {created} created, {updated} updated")
        return created, updated
