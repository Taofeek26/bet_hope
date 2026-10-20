"""
Acca of the day: the strongest 3-4 picks kicking off in the next 36 hours,
built once per day and then tracked in public.

Since Phase 8 each leg is that match's pick across markets (result, double
chance, GG/NG, over/under; see apps/predictions/picks.py), and at most two
legs share a market family, so the acca is a real mix rather than four
home wins.

Honest by construction: the combined chance is shown (it is the product of
the legs, so it drops fast), and losses are flashed like wins.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

MIN_LEGS, MAX_LEGS = 3, 4
MAX_PER_FAMILY = 2
WINDOW = timedelta(hours=36)


def choose_legs(candidates):
    """[(prediction, pick)] strongest first -> up to MAX_LEGS, at most MAX_PER_FAMILY per family."""
    chosen, per_family = [], {}
    for p, pick in candidates:
        if per_family.get(pick['family'], 0) >= MAX_PER_FAMILY:
            continue
        per_family[pick['family']] = per_family.get(pick['family'], 0) + 1
        chosen.append((p, pick))
        if len(chosen) == MAX_LEGS:
            break
    return chosen


def build_daily_acca(now=None):
    """Create today's acca if it doesn't exist yet. Returns the DailyAcca or None."""
    from apps.matches.models import Match
    from apps.predictions.picks import MIN_PROB, picks_for, top_pick_queryset
    from .flash import _add
    from .models import DailyAcca

    now = now or timezone.now()
    today = now.date()
    existing = DailyAcca.objects.filter(date=today).first()
    if existing:
        return existing

    preds = top_pick_queryset(status=Match.Status.SCHEDULED, kickoff_at__gt=now, kickoff_at__lte=now + WINDOW)
    legs = []
    for p, pick in choose_legs(picks_for(preds)):
        m = p.match
        legs.append({
            'match_id': m.id, 'match': f'{m.home_team.name} v {m.away_team.name}',
            'home': m.home_team.name, 'away': m.away_team.name,
            'kickoff': m.kickoff_at.isoformat(), 'league': m.season.league.name, 'league_code': m.season.league.code,
            'key': pick['key'], 'label': pick['label'], 'group': pick['group'],
            'probability': pick['probability'], 'fair_odds': pick['fair_odds'], 'best_odds': pick['best_odds'],
            'result': None,
        })

    if len(legs) < MIN_LEGS:
        _add(kind='acca', importance=1, title='No acca of the day today',
             body=f'Fewer than {MIN_LEGS} matches with a {int(MIN_PROB * 100)}%+ pick kick off in the next 36 hours, '
                  'so there is no acca rather than a weak one.',
             source='Bet Hope', dedupe_key=f'acca:none:{today}')
        return None

    chance = 1.0
    for leg in legs:
        chance *= leg['probability']
    best_total = None
    if all(leg['best_odds'] for leg in legs):
        best_total = 1.0
        for leg in legs:
            best_total *= leg['best_odds']
    acca = DailyAcca.objects.create(
        date=today, legs=legs, model_version=p.model_version,
        combined_probability=Decimal(str(round(chance, 4))),
        combined_fair_odds=Decimal(str(round(1 / chance, 2))),
        combined_best_odds=Decimal(str(round(best_total, 2))) if best_total else None,
    )
    _add(kind='acca', importance=3,
         title=f'Acca of the day: {len(legs)} picks, all win {chance * 100:.0f}% of the time',
         body='\n'.join(f"• {leg['match']}: {leg['label']} ({leg['probability'] * 100:.0f}%)" for leg in legs)
              + f'\nFair total odds {1 / chance:.2f}' + (f' · best total price {best_total:.2f}' if best_total else ''),
         source='Bet Hope', dedupe_key=f'acca:{today}')
    return acca


def settle_accas():
    """Mark each leg and the acca won/lost once all its matches are settled."""
    from apps.accounts.settle import leg_result
    from apps.matches.models import Match
    from .flash import _add
    from .models import DailyAcca

    settled = 0
    for acca in DailyAcca.objects.filter(status=DailyAcca.Status.OPEN):
        matches = {m.id: m for m in Match.objects.filter(id__in=[leg['match_id'] for leg in acca.legs])}
        done, won, void = True, 0, 0
        for leg in acca.legs:
            m = matches.get(leg['match_id'])
            if m is None or m.status in (Match.Status.POSTPONED, Match.Status.CANCELLED):
                leg['result'] = 'void'
                void += 1
            elif m.status == Match.Status.FINISHED and m.home_score is not None:
                # Any market (GG, over 2.5, double chance ...), same rules as My bets.
                leg['result'] = leg_result(leg['key'], m.home_score, m.away_score, m.status)
                leg['score'] = f'{m.home_score}-{m.away_score}'
                won += leg['result'] == 'won'
                void += leg['result'] == 'void'  # draw no bet on a draw
            else:
                done = False
        if not done:
            acca.save(update_fields=['legs', 'updated_at'])
            continue
        live_legs = len(acca.legs) - void
        acca.legs_won = won
        acca.status = (DailyAcca.Status.VOID if live_legs == 0
                       else DailyAcca.Status.WON if won == live_legs else DailyAcca.Status.LOST)
        acca.settled_at = timezone.now()
        acca.save()
        settled += 1
        _add(kind='acca', importance=3,
             title=(f"✅ Acca of {acca.date:%d %b} won: all {won} picks" if acca.status == 'won'
                    else f"❌ Acca of {acca.date:%d %b} lost: {won} of {live_legs} picks won"),
             body='\n'.join(f"{'✅' if leg.get('result') == 'won' else '❌' if leg.get('result') == 'lost' else '➖'} "
                            f"{leg['match']}: {leg['label']} {leg.get('score', '')}".strip() for leg in acca.legs),
             source='Bet Hope record', dedupe_key=f'acca:settled:{acca.date}')
    return settled


def acca_record(days=30):
    from .models import DailyAcca
    since = timezone.now().date() - timedelta(days=days)
    rows = DailyAcca.objects.filter(date__gte=since).exclude(status=DailyAcca.Status.OPEN)
    total = rows.exclude(status=DailyAcca.Status.VOID).count()
    won = rows.filter(status=DailyAcca.Status.WON).count()
    return {'days': days, 'settled': total, 'won': won}
