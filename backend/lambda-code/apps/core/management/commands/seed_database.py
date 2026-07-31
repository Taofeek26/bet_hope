"""
Seed database with initial football data.
"""
import random
from datetime import date, time, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.leagues.models import League, Season
from apps.teams.models import Team, TeamSeasonStats
from apps.matches.models import Match, MatchOdds
from apps.predictions.models import Prediction


LEAGUES_DATA = [
    {
        'name': 'Premier League',
        'country': 'England',
        'code': 'E0',
        'tier': 1,
        'priority': 1,
        'has_xg_data': True,
        'has_player_data': True,
        'teams': [
            'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton',
            'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Ipswich Town',
            'Leicester City', 'Liverpool', 'Manchester City', 'Manchester United',
            'Newcastle United', 'Nottingham Forest', 'Southampton', 'Tottenham',
            'West Ham United', 'Wolverhampton'
        ]
    },
    {
        'name': 'La Liga',
        'country': 'Spain',
        'code': 'SP1',
        'tier': 1,
        'priority': 2,
        'has_xg_data': True,
        'has_player_data': True,
        'teams': [
            'Alaves', 'Athletic Bilbao', 'Atletico Madrid', 'Barcelona', 'Celta Vigo',
            'Espanyol', 'Getafe', 'Girona', 'Las Palmas', 'Leganes',
            'Mallorca', 'Osasuna', 'Rayo Vallecano', 'Real Betis', 'Real Madrid',
            'Real Sociedad', 'Real Valladolid', 'Sevilla', 'Valencia', 'Villarreal'
        ]
    },
    {
        'name': 'Serie A',
        'country': 'Italy',
        'code': 'I1',
        'tier': 1,
        'priority': 3,
        'has_xg_data': True,
        'has_player_data': True,
        'teams': [
            'Atalanta', 'Bologna', 'Cagliari', 'Como', 'Empoli',
            'Fiorentina', 'Genoa', 'Inter Milan', 'Juventus', 'Lazio',
            'Lecce', 'AC Milan', 'Monza', 'Napoli', 'Parma',
            'Roma', 'Torino', 'Udinese', 'Venezia', 'Verona'
        ]
    },
    {
        'name': 'Bundesliga',
        'country': 'Germany',
        'code': 'D1',
        'tier': 1,
        'priority': 4,
        'has_xg_data': True,
        'has_player_data': True,
        'teams': [
            'Augsburg', 'Bayer Leverkusen', 'Bayern Munich', 'Bochum', 'Borussia Dortmund',
            'Borussia Monchengladbach', 'Eintracht Frankfurt', 'Freiburg', 'Heidenheim',
            'Hoffenheim', 'Holstein Kiel', 'Mainz', 'RB Leipzig', 'St. Pauli',
            'Stuttgart', 'Union Berlin', 'Werder Bremen', 'Wolfsburg'
        ]
    },
    {
        'name': 'Ligue 1',
        'country': 'France',
        'code': 'F1',
        'tier': 1,
        'priority': 5,
        'has_xg_data': True,
        'has_player_data': True,
        'teams': [
            'Angers', 'Auxerre', 'Brest', 'Le Havre', 'Lens',
            'Lille', 'Lyon', 'Marseille', 'Monaco', 'Montpellier',
            'Nantes', 'Nice', 'Paris Saint-Germain', 'Reims', 'Rennes',
            'Saint-Etienne', 'Strasbourg', 'Toulouse'
        ]
    },
    {
        'name': 'Eredivisie',
        'country': 'Netherlands',
        'code': 'N1',
        'tier': 2,
        'priority': 6,
        'has_xg_data': False,
        'has_player_data': False,
        'teams': [
            'Ajax', 'AZ Alkmaar', 'Feyenoord', 'PSV Eindhoven', 'FC Twente',
            'FC Utrecht', 'Sparta Rotterdam', 'Go Ahead Eagles', 'Heerenveen',
            'NEC Nijmegen', 'Groningen', 'Heracles', 'RKC Waalwijk', 'Fortuna Sittard',
            'PEC Zwolle', 'Almere City', 'NAC Breda', 'Willem II'
        ]
    },
    {
        'name': 'Primeira Liga',
        'country': 'Portugal',
        'code': 'P1',
        'tier': 2,
        'priority': 7,
        'has_xg_data': False,
        'has_player_data': False,
        'teams': [
            'Benfica', 'Porto', 'Sporting CP', 'Braga', 'Vitoria Guimaraes',
            'Rio Ave', 'Famalicao', 'Casa Pia', 'Arouca', 'Boavista',
            'Gil Vicente', 'Moreirense', 'Estoril', 'Farense', 'Estrela Amadora',
            'Santa Clara', 'Nacional', 'AVS'
        ]
    },
]


class Command(BaseCommand):
    help = 'Seed the database with initial football data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Prediction.objects.all().delete()
            MatchOdds.objects.all().delete()
            Match.objects.all().delete()
            TeamSeasonStats.objects.all().delete()
            Team.objects.all().delete()
            Season.objects.all().delete()
            League.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared'))

        self.stdout.write('Seeding database...')

        leagues = self._create_leagues()
        self.stdout.write(self.style.SUCCESS(f'Created {len(leagues)} leagues'))

        seasons = self._create_seasons(leagues)
        self.stdout.write(self.style.SUCCESS(f'Created {len(seasons)} seasons'))

        teams = self._create_teams(leagues)
        self.stdout.write(self.style.SUCCESS(f'Created {len(teams)} teams'))

        team_stats = self._create_team_stats(seasons, teams)
        self.stdout.write(self.style.SUCCESS(f'Created {len(team_stats)} team stats'))

        matches = self._create_matches(seasons)
        self.stdout.write(self.style.SUCCESS(f'Created {len(matches)} matches'))

        predictions = self._create_predictions(matches)
        self.stdout.write(self.style.SUCCESS(f'Created {len(predictions)} predictions'))

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    def _create_leagues(self):
        leagues = []
        for data in LEAGUES_DATA:
            league, created = League.objects.update_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'country': data['country'],
                    'tier': data['tier'],
                    'priority': data['priority'],
                    'has_xg_data': data['has_xg_data'],
                    'has_player_data': data['has_player_data'],
                    'is_active': True,
                }
            )
            leagues.append(league)
        return leagues

    def _create_seasons(self, leagues):
        seasons = []
        for league in leagues:
            season, created = Season.objects.update_or_create(
                league=league,
                code='2526',
                defaults={
                    'name': '2025-26',
                    'start_date': date(2025, 8, 9),
                    'end_date': date(2026, 5, 24),
                    'status': Season.Status.IN_PROGRESS,
                    'total_matches': 380 if len(LEAGUES_DATA[0]['teams']) == 20 else 306,
                }
            )
            seasons.append(season)
        return seasons

    def _create_teams(self, leagues):
        teams = []
        for league_data in LEAGUES_DATA:
            league = League.objects.get(code=league_data['code'])
            for team_name in league_data['teams']:
                team, created = Team.objects.update_or_create(
                    name=team_name,
                    league=league,
                    defaults={
                        'short_name': team_name[:3].upper(),
                        'code': team_name[:3].upper(),
                        'fd_name': team_name,
                        'is_active': True,
                    }
                )
                teams.append(team)
        return teams

    def _create_team_stats(self, seasons, teams):
        stats = []
        for season in seasons:
            league_teams = [t for t in teams if t.league_id == season.league_id]
            for i, team in enumerate(league_teams, 1):
                matches_played = random.randint(20, 25)
                wins = random.randint(5, 15)
                draws = random.randint(3, 8)
                losses = matches_played - wins - draws
                goals_for = random.randint(25, 65)
                goals_against = random.randint(20, 55)
                points = wins * 3 + draws

                stat, created = TeamSeasonStats.objects.update_or_create(
                    team=team,
                    season=season,
                    defaults={
                        'matches_played': matches_played,
                        'wins': wins,
                        'draws': draws,
                        'losses': losses,
                        'goals_for': goals_for,
                        'goals_against': goals_against,
                        'points': points,
                        'league_position': i,
                        'form': ''.join(random.choices(['W', 'D', 'L'], k=5)),
                        'home_played': matches_played // 2,
                        'home_wins': wins // 2,
                        'home_draws': draws // 2,
                        'home_losses': losses // 2,
                        'home_goals_for': goals_for // 2,
                        'home_goals_against': goals_against // 2,
                        'away_played': matches_played - matches_played // 2,
                        'away_wins': wins - wins // 2,
                        'away_draws': draws - draws // 2,
                        'away_losses': losses - losses // 2,
                        'away_goals_for': goals_for - goals_for // 2,
                        'away_goals_against': goals_against - goals_against // 2,
                        'clean_sheets': random.randint(3, 12),
                        'failed_to_score': random.randint(2, 8),
                    }
                )
                stats.append(stat)
        return stats

    def _create_matches(self, seasons):
        all_matches = []
        today = date.today()

        for season in seasons:
            teams = list(Team.objects.filter(league=season.league))

            # Create past matches (finished)
            for matchweek in range(1, 21):
                match_date = today - timedelta(days=(21 - matchweek) * 7)

                random.shuffle(teams)
                for i in range(0, len(teams) - 1, 2):
                    if i + 1 >= len(teams):
                        break
                    home_team = teams[i]
                    away_team = teams[i + 1]

                    home_score = random.choices([0, 1, 2, 3, 4], weights=[15, 30, 30, 15, 10])[0]
                    away_score = random.choices([0, 1, 2, 3], weights=[25, 35, 25, 15])[0]

                    match, created = Match.objects.update_or_create(
                        season=season,
                        home_team=home_team,
                        away_team=away_team,
                        match_date=match_date,
                        defaults={
                            'matchweek': matchweek,
                            'kickoff_time': time(15, 0),
                            'status': Match.Status.FINISHED,
                            'home_score': home_score,
                            'away_score': away_score,
                            'home_halftime_score': min(home_score, random.randint(0, home_score)),
                            'away_halftime_score': min(away_score, random.randint(0, away_score)),
                        }
                    )

                    # Create odds for the match
                    self._create_match_odds(match)
                    all_matches.append(match)

            # Create upcoming matches (scheduled) - start from today
            for matchweek in range(21, 26):
                match_date = today + timedelta(days=(matchweek - 21))

                random.shuffle(teams)
                for i in range(0, len(teams) - 1, 2):
                    if i + 1 >= len(teams):
                        break
                    home_team = teams[i]
                    away_team = teams[i + 1]

                    match, created = Match.objects.update_or_create(
                        season=season,
                        home_team=home_team,
                        away_team=away_team,
                        match_date=match_date,
                        defaults={
                            'matchweek': matchweek,
                            'kickoff_time': time(15, 0),
                            'status': Match.Status.SCHEDULED,
                        }
                    )

                    self._create_match_odds(match)
                    all_matches.append(match)

        return all_matches

    def _create_match_odds(self, match):
        # Generate realistic odds
        home_base = random.uniform(1.5, 4.0)
        draw_base = random.uniform(3.0, 4.0)
        away_base = random.uniform(1.8, 5.0)

        MatchOdds.objects.update_or_create(
            match=match,
            defaults={
                'home_odds': Decimal(str(round(home_base, 2))),
                'draw_odds': Decimal(str(round(draw_base, 2))),
                'away_odds': Decimal(str(round(away_base, 2))),
                'over_25_odds': Decimal(str(round(random.uniform(1.7, 2.2), 2))),
                'under_25_odds': Decimal(str(round(random.uniform(1.6, 2.1), 2))),
                'btts_yes_odds': Decimal(str(round(random.uniform(1.6, 2.0), 2))),
                'btts_no_odds': Decimal(str(round(random.uniform(1.7, 2.1), 2))),
                'bookmaker': 'Average',
            }
        )

    def _create_predictions(self, matches):
        predictions = []
        # Create predictions for all matches (both finished and scheduled)
        # This allows analytics to work with finished match data

        for match in matches:
            # Generate realistic probabilities with some high-confidence picks
            # About 30% of predictions should have high confidence (> 0.55)
            is_high_conf = random.random() < 0.3

            if is_high_conf:
                # High confidence prediction - one outcome dominates
                dominant = random.uniform(0.55, 0.75)
                remaining = 1 - dominant
                second = remaining * random.uniform(0.4, 0.6)
                third = remaining - second

                outcomes = [dominant, second, third]
                random.shuffle(outcomes)
                home_prob, draw_prob, away_prob = outcomes
            else:
                # Normal prediction
                home_prob = round(random.uniform(0.25, 0.50), 5)
                away_prob = round(random.uniform(0.20, 0.45), 5)
                draw_prob = round(1 - home_prob - away_prob, 5)

                # Ensure draw_prob is positive
                if draw_prob < 0.15:
                    draw_prob = 0.20
                    total = home_prob + away_prob + draw_prob
                    home_prob = round(home_prob / total, 5)
                    away_prob = round(away_prob / total, 5)
                    draw_prob = round(1 - home_prob - away_prob, 5)

            confidence = max(home_prob, draw_prob, away_prob)

            prediction, created = Prediction.objects.update_or_create(
                match=match,
                model_version='v1.0.0',
                defaults={
                    'home_win_probability': Decimal(str(home_prob)),
                    'draw_probability': Decimal(str(draw_prob)),
                    'away_win_probability': Decimal(str(away_prob)),
                    'predicted_home_score': Decimal(str(round(random.uniform(0.8, 2.5), 2))),
                    'predicted_away_score': Decimal(str(round(random.uniform(0.5, 2.0), 2))),
                    'confidence_score': Decimal(str(round(confidence, 4))),
                    'model_type': 'xgboost',
                    'key_factors': [
                        {'factor': 'Home advantage', 'impact': 'positive'},
                        {'factor': 'Recent form', 'impact': 'neutral'},
                        {'factor': 'Head to head', 'impact': 'positive'},
                    ],
                }
            )
            predictions.append(prediction)

        return predictions
