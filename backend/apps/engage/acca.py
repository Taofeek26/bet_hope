"""
Acca of the day (Phase 6): the strongest 3-4 home/draw/away picks kicking
off in the next 36 hours, built once per day and then tracked in public.

Honest by construction: the combined chance is shown (it is the product of
the legs, so it drops fast), and losses are flashed like wins.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

MIN_LEGS, MAX_LEGS = 3, 4
MIN_CONFIDENCE = Decimal('0.55')
WINDOW = timedelta(hours=36)


def build_daily_acca(now=None):
    """Create today's acca if it doesn't exist yet. Returns the DailyAcca or None."""
    from apps.matches.models import Match
    from apps.predictions.models import Prediction
    from .flash import _add
    from .models import DailyAcca

    now = now or timezone.now()
    today = now.date()
    existing = DailyAcca.objects.filter(date=today).first()
    if existing:
        return existing

    preds = (Prediction.objects.filter(model_version__startswith='v2_', match__status=Match.Status.SCHEDULED,
                                       match__kickoff_at__gt=now, match__kickoff_at__lte=now + WINDOW,
                                       confidence_score__gte=MIN_CONFIDENCE)
             .select_related('match__home_team', 'match__away_team', 'match__season__league')
             .prefetch_related('match__bookmaker_prices')
             .order_by('-confidence_score'))
    legs, used = [], set()
    for p in preds:
        if p.match_id in used:
            continue
        used.add(p.match_id)
        m = p.match
        side = {'HOME': ('1', 'home', f'{m.home_team.name} to win'), 'DRAW': ('X', 'draw', 'Draw'),
                'AWAY': ('2', 'away', f'{m.away_team.name} to win')}.get(p.recommended_outcome)
        if not side:
            continue
        key, field, label = side
        prob = float(getattr(p, {'home': 'home_win_probability', 'draw': 'draw_probability', 'away': 'away_win_probability'}[field]))
        books = [b for b in m.bookmaker_prices.all() if not b.is_exchange]
        best = max((float(getattr(b, f'{field}_odds')) for b in books), default=None)
        legs.append({
            'match_id': m.id, 'match': f'{m.home_team.name} v {m.away_team.name}',
            'home': m.home_team.name, 'away': m.away_team.name,
            'kickoff': m.kickoff_at.isoformat(), 'league': m.season.league.name, 'league_code': m.season.league.code,
            'key': key, 'label': label, 'group': '1X2',
            'probability': round(prob, 4), 'fair_odds': round(1 / prob, 2), 'best_odds': best, 'result': None,
        })
        if len(legs) == MAX_LEGS:
            break

    if len(legs) < MIN_LEGS:
        _add(kind='acca', importance=1, title='No acca of the day today',
             body=f'Fewer than {MIN_LEGS} picks at {int(MIN_CONFIDENCE * 100)}%+ kick off in the next 36 hours, '
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
        date=today, legs=legs, model_version=preds[0].model_version if preds else '',
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
                res = '1' if m.home_score > m.away_score else '2' if m.home_score < m.away_score else 'X'
                leg['result'] = 'won' if res == leg['key'] else 'lost'
                leg['score'] = f'{m.home_score}-{m.away_score}'
                won += leg['result'] == 'won'
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
