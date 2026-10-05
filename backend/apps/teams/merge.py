"""
Merge two Team rows that are the same club (Phase 2, DATA-01).

Unlike the old cleanup_duplicate_teams command, nothing is thrown away:
when both teams have a row for the same match, the two rows are merged
(odds, statistics, scores and predictions are kept) instead of one being
deleted with everything attached to it.
"""
import logging

from django.db import transaction
from django.db.models import Q

from .identity import canonical_key, fix_mojibake

logger = logging.getLogger(__name__)


def _merge_match_into(src, dst, stats):
    """Fold match `src` into `dst` (same fixture), then delete `src`."""
    from apps.matches.models import MatchOdds, MatchStatistics
    from apps.predictions.models import Prediction

    changed = []
    for field in ('home_score', 'away_score', 'home_halftime_score', 'away_halftime_score',
                  'kickoff_time', 'matchweek'):
        if getattr(dst, field) is None and getattr(src, field) is not None:
            setattr(dst, field, getattr(src, field))
            changed.append(field)
    # A finished result beats "scheduled"; keep the provider id that has one.
    if src.status == 'finished' and dst.status != 'finished':
        dst.status = 'finished'
        changed.append('status')
    if not dst.fd_match_id and src.fd_match_id:
        dst.fd_match_id = src.fd_match_id
        changed.append('fd_match_id')
    if changed:
        dst.save()  # save() recomputes outcome from the scores

    for model in (MatchOdds, MatchStatistics):
        src_row = model.objects.filter(match=src).first()
        if src_row and not model.objects.filter(match=dst).exists():
            src_row.match = dst
            src_row.save(update_fields=['match'])

    # Predictions: keep dst's if it has any (history stays one-per-match);
    # otherwise move src's over so predictions made on the other row survive.
    if Prediction.objects.filter(match=dst).exists():
        stats['predictions_dropped'] += Prediction.objects.filter(match=src).count()
    else:
        stats['predictions_moved'] += Prediction.objects.filter(match=src).update(match=dst)

    src.delete()
    stats['matches_merged'] += 1


@transaction.atomic
def merge_teams(drop, keep, source='merge', stats=None):
    """
    Move everything that references `drop` onto `keep`, record `drop`'s
    names as aliases of `keep`, then delete `drop`. Returns the stats dict.
    """
    from apps.matches.models import Match
    from apps.teams.models import TeamAlias, TeamSeasonStats, HeadToHead
    from apps.documents.models import Document

    if stats is None:
        stats = {'teams_merged': 0, 'matches_moved': 0, 'matches_merged': 0,
                 'predictions_moved': 0, 'predictions_dropped': 0}
    if drop.pk == keep.pk:
        return stats

    # 1. Matches
    for match in Match.objects.filter(Q(home_team=drop) | Q(away_team=drop)).select_related('season'):
        home = keep if match.home_team_id == drop.pk else match.home_team
        away = keep if match.away_team_id == drop.pk else match.away_team
        twin = Match.objects.filter(
            season=match.season, home_team=home, away_team=away, match_date=match.match_date,
        ).exclude(pk=match.pk).first()
        if twin:
            _merge_match_into(match, twin, stats)
        else:
            match.home_team = home
            match.away_team = away
            match.save(update_fields=['home_team', 'away_team', 'updated_at'])
            stats['matches_moved'] += 1

    # 2. Rows with a per-team uniqueness rule: move, or drop on conflict
    for row in TeamSeasonStats.objects.filter(team=drop):
        if TeamSeasonStats.objects.filter(team=keep, season=row.season).exists():
            row.delete()
        else:
            row.team = keep
            row.save(update_fields=['team'])
    for row in HeadToHead.objects.filter(Q(team_a=drop) | Q(team_b=drop)):
        row.delete()  # derived data; the table is unused (API-03) and rebuilt from matches

    # 3. Plain foreign keys
    for rel in drop._meta.related_objects:
        model = rel.related_model
        if model in (Match, TeamSeasonStats, HeadToHead, TeamAlias, Document) or rel.many_to_many:
            continue
        model.objects.filter(**{rel.field.name: drop}).update(**{rel.field.name: keep})

    # 4. Many-to-many (documents about the club)
    for doc in Document.objects.filter(teams=drop):
        doc.teams.add(keep)
        doc.teams.remove(drop)

    # 5. Aliases: drop's own aliases move over, plus its names
    country = keep.league.country
    TeamAlias.objects.filter(team=drop).update(team=keep)
    for name in {drop.name, drop.fd_name} - {''}:
        record_alias(keep, name, source, country)

    # 6. Keep the best display data: official name and crest from
    # football-data.org when the kept row came from the CSVs.
    updates = []
    if not keep.logo_url and drop.logo_url:
        keep.logo_url = drop.logo_url
        updates.append('logo_url')
    if drop.fd_name and not keep.fd_name:
        keep.fd_name = drop.fd_name
        updates.append('fd_name')
    for field in ('code', 'stadium', 'founded'):
        if not getattr(keep, field) and getattr(drop, field):
            setattr(keep, field, getattr(drop, field))
            updates.append(field)
    if updates:
        keep.save(update_fields=updates + ['updated_at'])

    drop.delete()
    update_current_league(keep)
    stats['teams_merged'] += 1
    return stats


def update_current_league(team):
    """
    Point team.league at the domestic division of its most recent match.
    A promoted/relegated club is now one Team across divisions, so its
    "league" is simply where it plays now (cup competitions don't count).
    """
    from apps.matches.models import Match

    latest = (Match.objects.filter(Q(home_team=team) | Q(away_team=team))
              .exclude(season__league__country='Europe')
              .select_related('season__league')
              .order_by('-match_date').first())
    if latest and latest.season.league_id != team.league_id:
        team.league = latest.season.league
        team.save(update_fields=['league', 'updated_at'])


def record_alias(team, name, source='', country=None):
    """Remember `name` as a name for `team` (idempotent)."""
    from apps.teams.models import TeamAlias

    country = country or team.league.country
    name = fix_mojibake(name)
    key = canonical_key(name, country)
    if not key:
        return None
    alias, created = TeamAlias.objects.get_or_create(
        country=country, key=key, defaults={'team': team, 'name': name, 'source': source},
    )
    if not created and alias.team_id != team.pk:
        logger.warning('Alias %r (%s) already points at team %s, not %s',
                       name, country, alias.team_id, team.pk)
    return alias
