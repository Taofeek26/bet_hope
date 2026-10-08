"""
Bet settlement on the server (admin statistics). Same rules as the app's
lib/mybets.ts: lost if any leg lost, won when every leg is won or void
(void legs count as odds 1).
"""
import re


def leg_result(key, h, a, status):
    if status in ('postponed', 'cancelled'):
        return 'void'
    if status != 'finished' or h is None or a is None:
        return 'pending'
    w = lambda c: 'won' if c else 'lost'
    t = h + a
    fixed = {'1': h > a, 'X': h == a, '2': a > h, '1X': h >= a, '12': h != a, 'X2': a >= h,
             'GG': h > 0 and a > 0, 'NG': not (h > 0 and a > 0), 'HCS': a == 0, 'ACS': h == 0}
    if key in fixed:
        return w(fixed[key])
    if key == 'DNB1':
        return 'void' if h == a else w(h > a)
    if key == 'DNB2':
        return 'void' if h == a else w(a > h)
    m = re.match(r'^([OU])(\d+\.5)$', key)
    if m:
        return w(t > float(m[2]) if m[1] == 'O' else t < float(m[2]))
    m = re.match(r'^([HA])O(\d+\.5)$', key)
    if m:
        return w((h if m[1] == 'H' else a) > float(m[2]))
    m = re.match(r'^CS(\d+)-(\d+)$', key)
    if m:
        return w(h == int(m[1]) and a == int(m[2]))
    return 'pending'


def bet_result(legs):
    if 'lost' in legs:
        return 'lost'
    if 'pending' in legs:
        return 'pending'
    if all(l == 'void' for l in legs):
        return 'void'
    return 'won'


def settle_bets(bets):
    """[(bet, status, profit)] for UserBet rows, with one query for all their matches."""
    from apps.matches.models import Match
    ids = {s.get('matchId') for b in bets for s in (b.selections or []) if s.get('matchId')}
    matches = {m['id']: m for m in Match.objects.filter(id__in=ids).values('id', 'status', 'home_score', 'away_score')}
    out = []
    for b in bets:
        legs = []
        for s in b.selections or []:
            m = matches.get(s.get('matchId')) or {}
            legs.append(leg_result(str(s.get('key', '')), m.get('home_score'), m.get('away_score'), m.get('status')))
        st = bet_result(legs) if legs else 'pending'
        stake, odds = float(b.stake), float(b.odds)
        profit = stake * odds - stake if st == 'won' else -stake if st == 'lost' else 0.0
        out.append((b, st, round(profit, 2)))
    return out
