"""
Management command to clean up duplicate teams in the database.
Merges teams that represent the same real-world team (e.g., "Sheffield Utd" and "Sheffield United").
"""
import unicodedata
import re
from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.teams.models import Team
from apps.matches.models import Match


class Command(BaseCommand):
    help = 'Clean up duplicate teams (same team with different name spellings)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be merged without actually merging',
        )

    def _normalize_team_name(self, name: str) -> str:
        """Normalize team name for matching."""
        if not name:
            return ''

        # Remove accents (é → e, ü → u, etc.)
        normalized = unicodedata.normalize('NFKD', name)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))

        # Lowercase
        normalized = normalized.lower().strip()

        # Common abbreviations mapping
        abbreviations = {
            ' fc': '',
            ' cf': '',
            ' sc': '',
            ' ac': '',
            ' afc': '',
            ' utd': ' united',
            ' weds': ' wednesday',
        }

        for abbrev, full in abbreviations.items():
            normalized = normalized.replace(abbrev, full)

        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write('Finding duplicate teams...')

        # Group teams by league and normalized name
        teams_by_league = {}
        for team in Team.objects.select_related('league').all():
            league_id = team.league_id
            normalized = self._normalize_team_name(team.name)

            key = (league_id, normalized)
            if key not in teams_by_league:
                teams_by_league[key] = []
            teams_by_league[key].append(team)

        # Find duplicates (groups with more than one team)
        duplicate_groups = {k: v for k, v in teams_by_league.items() if len(v) > 1}

        total_duplicates = len(duplicate_groups)
        self.stdout.write(f'Found {total_duplicates} sets of duplicate teams')

        if total_duplicates == 0:
            self.stdout.write(self.style.SUCCESS('No duplicate teams found!'))
            return

        merged_count = 0
        deleted_count = 0

        for (league_id, normalized), teams in duplicate_groups.items():
            # Sort to prefer: most matches, has fd_name different from name, most recent
            teams_sorted = sorted(
                teams,
                key=lambda t: (
                    Match.objects.filter(home_team=t).count() + Match.objects.filter(away_team=t).count(),
                    1 if (t.fd_name and t.fd_name != t.name) else 0,
                    t.updated_at if hasattr(t, 'updated_at') else t.id
                ),
                reverse=True
            )

            keeper = teams_sorted[0]
            to_merge = teams_sorted[1:]

            league_name = keeper.league.name if keeper.league else 'Unknown'
            self.stdout.write(
                f'\n  Duplicate group in {league_name}:'
            )
            self.stdout.write(f'    Keeping: "{keeper.name}" (fd_name: {keeper.fd_name}, id: {keeper.id})')

            for team in to_merge:
                home_matches = Match.objects.filter(home_team=team).count()
                away_matches = Match.objects.filter(away_team=team).count()
                total_matches = home_matches + away_matches

                self.stdout.write(
                    f'    Merging: "{team.name}" (fd_name: {team.fd_name}, id: {team.id}, matches: {total_matches})'
                )

                if not dry_run:
                    # First, handle matches that would become duplicates
                    # For home matches
                    for match in Match.objects.filter(home_team=team):
                        # Check if this match would conflict with an existing one
                        existing = Match.objects.filter(
                            season=match.season,
                            home_team=keeper,
                            away_team=match.away_team,
                            match_date=match.match_date
                        ).first()
                        if existing:
                            # Delete the duplicate match (keep the one with keeper team)
                            self.stdout.write(f'      Deleting duplicate match: {match}')
                            match.delete()
                        else:
                            # Update this match to use keeper team
                            match.home_team = keeper
                            match.save(update_fields=['home_team'])

                    # For away matches
                    for match in Match.objects.filter(away_team=team):
                        # Check if this match would conflict with an existing one
                        existing = Match.objects.filter(
                            season=match.season,
                            home_team=match.home_team,
                            away_team=keeper,
                            match_date=match.match_date
                        ).first()
                        if existing:
                            # Delete the duplicate match
                            self.stdout.write(f'      Deleting duplicate match: {match}')
                            match.delete()
                        else:
                            # Update this match to use keeper team
                            match.away_team = keeper
                            match.save(update_fields=['away_team'])

                    # Update TeamSeasonStats if exists
                    from apps.teams.models import TeamSeasonStats
                    TeamSeasonStats.objects.filter(team=team).update(team=keeper)

                    # Delete the duplicate team
                    team.delete()

                deleted_count += 1

            merged_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\nDry run complete. Would merge {merged_count} groups, '
                f'deleting {deleted_count} duplicate teams.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nCleanup complete. Merged {merged_count} groups, '
                f'deleted {deleted_count} duplicate teams.'
            ))
