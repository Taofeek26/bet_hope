"""
Merge duplicate Team rows into one Team per club (Phase 2, DATA-01).

Default is a dry-run report; nothing changes without --apply.

  1. Repair double-encoded names ("PreuÃen MÃ¼nster" -> "Preußen Münster").
  2. CSV rows for the same club in different divisions of one country
     (same football-data.co.uk name) -> one Team, kept in its current division.
  3. Teams created by the football-data.org sync with no CSV history ->
     merged into the matching CSV team (Champions/Europa League teams are
     matched across countries).
  4. Every remaining team's names are recorded as TeamAlias rows so the
     syncs resolve them by alias from now on.

Replaces cleanup_duplicate_teams, which deleted one of two rows for the
same match (with its odds, stats and predictions) instead of merging them.
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count, Max, Q

from apps.teams.identity import best_match, canonical_key, fix_mojibake
from apps.teams.merge import merge_teams, record_alias, update_current_league


class Command(BaseCommand):
    help = 'Merge duplicate teams into one Team per club (dry run unless --apply)'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Make the changes (default: report only)')

    def handle(self, *args, **opts):
        from apps.teams.models import Team

        apply = opts['apply']
        mode = 'APPLY' if apply else 'DRY RUN (use --apply to make changes)'
        self.stdout.write(f'== merge_duplicate_teams: {mode}')
        stats = None
        before = Team.objects.count()

        # 1. Names
        fixed = 0
        for t in Team.objects.all():
            name, fd = fix_mojibake(t.name), fix_mojibake(t.fd_name)
            if (name, fd) != (t.name, t.fd_name):
                self.stdout.write(f'  name fix: {t.name!r} -> {name!r}')
                fixed += 1
                if apply:
                    t.name, t.fd_name = name, fd
                    t.save(update_fields=['name', 'fd_name', 'updated_at'])

        teams = list(self._annotated())

        # 2. Same CSV name within a country (split by promotion/relegation)
        groups = defaultdict(list)
        for t in teams:
            if t.csv_m and t.fd_name:
                groups[(t.league.country, fix_mojibake(t.fd_name).strip().lower())].append(t)
        split = [g for g in groups.values() if len(g) > 1]
        self.stdout.write(f'\n-- Step 2: {len(split)} clubs split across divisions '
                          f'({sum(len(g) for g in split)} rows)')
        for g in sorted(split, key=lambda g: (g[0].league.country, g[0].fd_name)):
            g.sort(key=lambda t: t.last_match or t.created_at.date(), reverse=True)
            keep, drops = g[0], g[1:]
            self.stdout.write(f'  {keep.league.country}: {keep.fd_name} keep #{keep.pk} ({keep.league.code}), '
                              f'merge {", ".join(f"#{d.pk} ({d.league.code})" for d in drops)}')
            if apply:
                for d in drops:
                    stats = merge_teams(d, keep, 'merge:division', stats)

        # 3. football-data.org-only teams -> their CSV team
        teams = list(self._annotated())
        csv_by_country = defaultdict(list)
        for t in teams:
            if t.csv_m:
                csv_by_country[t.league.country].append(t)
        org_only = [t for t in teams if t.org_m and not t.csv_m]
        pairs, unmatched = [], []
        for t in sorted(org_only, key=lambda t: (t.league.code, t.name)):
            countries = list(csv_by_country) if t.league.country == 'Europe' else [t.league.country]
            found = [m for c in countries if (m := best_match(t.name, c, csv_by_country[c]))]
            if len(found) == 1:
                pairs.append((t, found[0]))
            else:
                unmatched.append(t)
        self.stdout.write(f'\n-- Step 3: {len(pairs)} football-data.org teams matched to CSV teams, '
                          f'{len(unmatched)} left as they are')
        for drop, keep in pairs:
            self.stdout.write(f'  {drop.league.code:4} {drop.name:38} -> {keep.fd_name or keep.name} '
                              f'(#{keep.pk}, {keep.league.code})')
            if apply:
                stats = merge_teams(drop, keep, 'merge:football-data.org', stats)
        if unmatched:
            self.stdout.write('  Unmatched (kept as separate teams; add to KNOWN_ALIASES if wrong):')
            for t in unmatched:
                self.stdout.write(f'    {t.league.code:4} {t.name} [{canonical_key(t.name, t.league.country)}]')

        # 4. Aliases for everything that remains
        if apply:
            n = 0
            for t in Team.objects.select_related('league'):
                for name in {t.name, t.fd_name} - {''}:
                    if record_alias(t, name, 'seed'):
                        n += 1
                update_current_league(t)
            self.stdout.write(f'\n-- Step 4: {n} aliases recorded')

        after = Team.objects.count()
        self.stdout.write(f'\n== Names fixed: {fixed}. Teams: {before} -> {after if apply else before} '
                          f'{"" if apply else "(unchanged, dry run)"}')
        if stats:
            self.stdout.write(f'   {stats}')

    def _annotated(self):
        from apps.teams.models import Team

        csv = ~Q(home_matches__fd_match_id__startswith='fdorg_')
        org = Q(home_matches__fd_match_id__startswith='fdorg_')
        csv_a = ~Q(away_matches__fd_match_id__startswith='fdorg_')
        org_a = Q(away_matches__fd_match_id__startswith='fdorg_')
        home = Team.objects.select_related('league').annotate(
            csv_h=Count('home_matches', filter=csv, distinct=True),
            org_h=Count('home_matches', filter=org, distinct=True),
            last_h=Max('home_matches__match_date'),
        )
        away = {t.pk: t for t in Team.objects.annotate(
            csv_a=Count('away_matches', filter=csv_a, distinct=True),
            org_a=Count('away_matches', filter=org_a, distinct=True),
            last_a=Max('away_matches__match_date'),
        )}
        for t in home:
            a = away[t.pk]
            t.csv_m = t.csv_h + a.csv_a
            t.org_m = t.org_h + a.org_a
            t.last_match = max(filter(None, [t.last_h, a.last_a]), default=None)
            yield t
