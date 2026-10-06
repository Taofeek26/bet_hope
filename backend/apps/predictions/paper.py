"""
Paper betting (Phase 5, step 2): log pretend 1-unit bets before kickoff and
settle them after the result, so Analytics can show the real return of
following the model, at the prices that were actually available.

Called from generate_predictions: after upcoming predictions are written
(log) and after predictions are validated (settle). Both are idempotent.
"""
from datetime import datetime, time, timedelta, timezone as dt_tz
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

VALUE_EDGE = Decimal('0.05')   # same bar as /predictions/value_bets/
LOG_WINDOW = timedelta(hours=26)  # log at the last daily run before kickoff

_OUTCOME = {'HOME': 'H', 'DRAW': 'D', 'AWAY': 'A'}


def _kickoff(match):
    if match.kickoff_at:
        return match.kickoff_at
    # No exact time known: treat as midday UTC, so the bet is still logged
    # the day before (never on the match day itself, when it may have started).
    return datetime.combine(match.match_date, time(12, 0), tzinfo=dt_tz.utc)


def log_paper_bets(now=None):
    """Create bets for matches kicking off within LOG_WINDOW that have odds."""
    from apps.matches.models import Match
    from apps.predictions.models import PaperBet

    now = now or timezone.now()
    created = skipped_no_odds = 0
    matches = (
        Match.objects.filter(
            status=Match.Status.SCHEDULED,
            match_date__gte=(now - timedelta(days=1)).date(),
            match_date__lte=(now + LOG_WINDOW).date(),
        )
        .select_related('odds')
        .prefetch_related('predictions')
    )
    for match in matches:
        ko = _kickoff(match)
        if not (now < ko <= now + LOG_WINDOW):
            continue
        preds = sorted(match.predictions.all(), key=lambda p: p.updated_at, reverse=True)
        pred = preds[0] if preds else None
        if pred is None or pred.created_at >= ko:
            continue
        odds = getattr(match, 'odds', None)
        prices = {
            'H': odds and odds.home_odds, 'D': odds and odds.draw_odds, 'A': odds and odds.away_odds,
        }
        if not all(v and v > 1 for v in prices.values()):
            skipped_no_odds += 1
            continue
        probs = {
            'H': pred.home_win_probability, 'D': pred.draw_probability, 'A': pred.away_win_probability,
        }
        wanted = []
        pick = _OUTCOME.get(pred.recommended_outcome)
        if pick:
            wanted.append((PaperBet.Strategy.PICK, pick))
        for sel in 'HDA':
            if Decimal(probs[sel]) - (1 / Decimal(prices[sel])) > VALUE_EDGE:
                wanted.append((PaperBet.Strategy.VALUE, sel))
        for strategy, sel in wanted:
            implied = (1 / Decimal(prices[sel])).quantize(Decimal('0.0001'))
            try:
                with transaction.atomic():
                    _, made = PaperBet.objects.get_or_create(
                        match=match, strategy=strategy, selection=sel,
                        defaults=dict(
                            prediction=pred, model_version=pred.model_version,
                            odds=prices[sel], odds_source=odds.bookmaker or '',
                            model_probability=probs[sel], implied_probability=implied,
                            edge=(Decimal(probs[sel]) - implied).quantize(Decimal('0.0001')),
                            confidence=pred.confidence_score,
                        ),
                    )
            except IntegrityError:
                made = False
            created += made
    return {'created': created, 'skipped_no_odds': skipped_no_odds}


def settle_paper_bets():
    """Settle open bets whose match has a result (or was called off)."""
    from apps.matches.models import Match
    from apps.predictions.models import PaperBet

    won = lost = void = 0
    now = timezone.now()
    for bet in PaperBet.objects.filter(status=PaperBet.Status.OPEN).select_related('match'):
        m = bet.match
        if m.status in (Match.Status.POSTPONED, Match.Status.CANCELLED):
            bet.status, bet.profit = PaperBet.Status.VOID, Decimal('0')
            void += 1
        elif m.status == Match.Status.FINISHED and m.home_score is not None and m.away_score is not None:
            result = 'H' if m.home_score > m.away_score else 'A' if m.home_score < m.away_score else 'D'
            if result == bet.selection:
                bet.status, bet.profit = PaperBet.Status.WON, (bet.odds - 1) * bet.stake
                won += 1
            else:
                bet.status, bet.profit = PaperBet.Status.LOST, -bet.stake
                lost += 1
        else:
            continue
        bet.settled_at = now
        bet.save(update_fields=['status', 'profit', 'settled_at', 'updated_at'])
    return {'won': won, 'lost': lost, 'void': void}
