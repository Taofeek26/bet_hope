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

    # Seasons to download, newest first: computed from today's date back to
    # 1993-94, where Football-Data.co.uk starts (Phase 2). The hard-coded
    # list stopped at 2025-26, so the current season was never imported.
    @property
    def SEASONS(self) -> List[str]:
        from apps.core.seasons import all_season_codes
        return all_season_codes()

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

            # Parse CSV from the raw bytes. response.text guessed Latin-1
            # (the server sends no charset), which turned UTF-8 names into
            # "PreuÃen MÃ¼nster". Older seasons are Latin-1, so fall back.
            df = pd.read_csv(
                StringIO(self._decode(response.content)),
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

    @staticmethod
    def _decode(raw: bytes) -> str:
        """CSV bytes -> text: UTF-8 (with or without BOM), else Latin-1."""
        try:
            return raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            return raw.decode('latin-1')

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
        df: pd.DataFrame,
        resolver=None,
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

        from apps.core.seasons import season_name as _season_name
        db_season, _ = Season.objects.get_or_create(
            league=league,
            code=season,
            defaults={'name': _season_name(season)}
        )

        # One Team per club per country, found through TeamAlias (Phase 2):
        # the old get_or_create(fd_name, league) made a new Team every time a
        # club changed division, splitting its history.
        from apps.teams.identity import TeamResolver
        resolver = resolver or TeamResolver(source='football-data.co.uk')
        team_cache = {}

        def get_or_create_team(name: str) -> Team:
            if name not in team_cache:
                team_cache[name] = resolver.resolve(name, league)
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

                    # Create unique identifier for reference
                    # Ids, not names: names made this exceed the 50-char column and the
                    # row silently failed to import (e.g. "Preußen Münster", Phase 2).
                    match_id = f"{league_code}_{season}_{match_date}_{home_team.pk}_{away_team.pk}"

                    # Kickoff (UK local time in these files), when the season file has it
                    from apps.matches.timeutil import local_to_utc
                    kickoff = self._parse_time(row.get('Time'))
                    kickoff_fields = {
                        'kickoff_time': kickoff,
                        'kickoff_at': local_to_utc(match_date, kickoff, 'Europe/London'),
                    } if kickoff else {}

                    # Get or create match using natural key (prevents duplicates)
                    match, match_created = Match.objects.update_or_create(
                        season=db_season,
                        home_team=home_team,
                        away_team=away_team,
                        match_date=match_date,
                        defaults={
                            **kickoff_fields,
                            'home_score': self._safe_int(row.get('FTHG')),
                            'away_score': self._safe_int(row.get('FTAG')),
                            'home_halftime_score': self._safe_int(row.get('HTHG')),
                            'away_halftime_score': self._safe_int(row.get('HTAG')),
                            'status': Match.Status.FINISHED if not pd.isna(row.get('FTHG')) else Match.Status.SCHEDULED,
                            'fd_match_id': match_id,  # Store for reference
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
                    home_odds = self._first_decimal(row, 'AvgH', 'BbAvH', 'PSH', 'B365H')
                    if home_odds:
                        MatchOdds.objects.update_or_create(
                            match=match,
                            defaults={
                                'home_odds': home_odds,
                                'draw_odds': self._first_decimal(row, 'AvgD', 'BbAvD', 'PSD', 'B365D'),
                                'away_odds': self._first_decimal(row, 'AvgA', 'BbAvA', 'PSA', 'B365A'),
                                'over_25_odds': self._first_decimal(row, 'Avg>2.5', 'BbAv>2.5', 'P>2.5', 'B365>2.5'),
                                'under_25_odds': self._first_decimal(row, 'Avg<2.5', 'BbAv<2.5', 'P<2.5', 'B365<2.5'),
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

        from apps.core.seasons import season_code_for, season_name
        from apps.teams.identity import TeamResolver
        from apps.matches.timeutil import local_to_utc

        df = self.download_fixtures()
        if df is None or df.empty:
            return 0, 0

        created = updated = with_odds = 0
        resolver = TeamResolver(source='football-data.co.uk')

        for _, row in df.iterrows():
            div = row.get('Div', '')
            if not div or div not in self.LEAGUES:
                continue
            home_name, away_name = row.get('HomeTeam'), row.get('AwayTeam')
            match_date = row.get('Date')
            if pd.isna(home_name) or pd.isna(away_name) or pd.isna(match_date):
                continue
            match_date = pd.Timestamp(match_date).date()
            try:
                # One savepoint per row: a bad row can't abort the rest.
                with transaction.atomic():
                    info = self.LEAGUES[div]
                    league, _ = League.objects.get_or_create(
                        code=div, defaults={'name': info['name'], 'country': info['country'], 'tier': info['tier']},
                    )
                    # Season from the match's own date, not today's (a fixture
                    # list read in July can include August fixtures).
                    code = season_code_for(match_date, league.season_start_month)
                    db_season, _ = Season.objects.get_or_create(
                        league=league, code=code, defaults={'name': season_name(code)},
                    )
                    home_team = resolver.resolve(str(home_name), league)
                    away_team = resolver.resolve(str(away_name), league)

                    kickoff_time = self._parse_time(row.get('Time'))
                    match, was_created = Match.objects.get_or_create(
                        season=db_season, home_team=home_team, away_team=away_team, match_date=match_date,
                        defaults={
                            'status': Match.Status.SCHEDULED,
                            'fd_match_id': f"{div}_{code}_{match_date}_{home_team.pk}_{away_team.pk}",
                        },
                    )
                    # Football-Data.co.uk times are UK local time.
                    if kickoff_time and match.status == Match.Status.SCHEDULED:
                        match.kickoff_time = kickoff_time
                        match.kickoff_at = local_to_utc(match_date, kickoff_time, 'Europe/London')
                        match.save(update_fields=['kickoff_time', 'kickoff_at', 'updated_at'])
                    created += was_created
                    updated += not was_created

                    # Pre-match market odds: the input the model was trained
                    # on and upcoming fixtures never had before (ML-01).
                    home_odds = self._first_decimal(row, 'AvgH', 'BbAvH', 'PSH', 'B365H')
                    if home_odds and match.status == Match.Status.SCHEDULED:
                        MatchOdds.objects.update_or_create(
                            match=match,
                            defaults={
                                'home_odds': home_odds,
                                'draw_odds': self._first_decimal(row, 'AvgD', 'BbAvD', 'PSD', 'B365D'),
                                'away_odds': self._first_decimal(row, 'AvgA', 'BbAvA', 'PSA', 'B365A'),
                                'over_25_odds': self._first_decimal(row, 'Avg>2.5', 'BbAv>2.5', 'P>2.5', 'B365>2.5'),
                                'under_25_odds': self._first_decimal(row, 'Avg<2.5', 'BbAv<2.5', 'P<2.5', 'B365<2.5'),
                                'bookmaker': 'Average',
                            },
                        )
                        with_odds += 1
            except Exception as e:
                logger.error(f"Error processing fixture {div} {home_name} v {away_name}: {e}")

        if resolver.created:
            logger.warning(f"New teams created from fixtures: {resolver.created}")
        logger.info(f"Fixtures synced: {created} created, {updated} updated, {with_odds} with odds")
        return created, updated

    def _first_decimal(self, row, *columns) -> Optional[Decimal]:
        """First of `columns` holding a usable number (NaN is skipped, unlike `a or b`)."""
        for col in columns:
            value = self._safe_decimal(row.get(col))
            if value:
                return value
        return None

    @staticmethod
    def _parse_time(value):
        """'15:00' / '20:45' -> time, else None."""
        if value is None or pd.isna(value):
            return None
        try:
            return datetime.strptime(str(value).strip()[:5], '%H:%M').time()
        except ValueError:
            return None
