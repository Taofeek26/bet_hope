"""
Flash feed, acca of the day and yesterday's results (Phase 6). Read-only.
"""
from datetime import date, timedelta

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def _flash_row(f):
    m = f.match
    return {
        'id': f.id, 'kind': f.kind, 'tag': f.tag, 'title': f.title, 'body': f.body,
        'url': f.url, 'source': f.source, 'importance': f.importance,
        'published_at': f.published_at.isoformat(),
        'match': ({'id': m.id, 'label': f'{m.home_team.name} v {m.away_team.name}',
                   'kickoff_at': m.kickoff_at.isoformat() if m.kickoff_at else None,
                   'match_date': m.match_date.isoformat()} if m else None),
        'team': {'id': f.team_id, 'name': f.team.name} if f.team_id else None,
    }


def _acca_row(a):
    return {
        'date': a.date.isoformat(), 'legs': a.legs, 'status': a.status, 'legs_won': a.legs_won,
        'combined_probability': float(a.combined_probability), 'combined_fair_odds': float(a.combined_fair_odds),
        'combined_best_odds': float(a.combined_best_odds) if a.combined_best_odds else None,
        'model_version': a.model_version,
    }


class EngageViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def flash(self, request):
        """?match=<id> · ?team=<id> · ?kind=news,odds_move · ?min_importance=2 · ?limit=30 (max 100) · ?hours=72"""
        from apps.engage.models import FlashItem
        qs = FlashItem.objects.select_related('match__home_team', 'match__away_team', 'team')
        try:
            limit = min(max(int(request.query_params.get('limit', 30)), 1), 100)
            hours = min(max(int(request.query_params.get('hours', 72)), 1), 24 * 14)
        except ValueError:
            limit, hours = 30, 72
        qs = qs.filter(published_at__gte=timezone.now() - timedelta(hours=hours))
        if request.query_params.get('match'):
            qs = qs.filter(match_id=request.query_params['match'])
        if request.query_params.get('team'):
            qs = qs.filter(team_id=request.query_params['team'])
        if request.query_params.get('min_importance', '').isdigit():
            qs = qs.filter(importance__gte=int(request.query_params['min_importance']))
        if request.query_params.get('kind'):
            qs = qs.filter(kind__in=request.query_params['kind'].split(','))
        return Response({'items': [_flash_row(f) for f in qs[:limit]]})

    @action(detail=False, methods=['get'])
    def acca(self, request):
        """Today's acca (or the latest one) plus the 30-day record and recent history."""
        from apps.engage.acca import acca_record
        from apps.engage.models import DailyAcca
        today = DailyAcca.objects.filter(date=timezone.now().date()).first()
        latest = today or DailyAcca.objects.order_by('-date').first()
        history = DailyAcca.objects.exclude(status=DailyAcca.Status.OPEN).order_by('-date')[:14]
        return Response({
            'today': _acca_row(today) if today else None,
            'latest': _acca_row(latest) if latest else None,
            'record': acca_record(30),
            'history': [_acca_row(a) for a in history],
        })

    @action(detail=False, methods=['get'])
    def results(self, request):
        """How the top picks did on ?date=YYYY-MM-DD (default yesterday)."""
        from apps.engage.flash import yesterday_results
        d = request.query_params.get('date')
        try:
            day = date.fromisoformat(d) if d else None
        except ValueError:
            day = None
        return Response(yesterday_results(day))

    # ─── Push alerts (Phase 6) ──────────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def push_key(self, request):
        import os
        return Response({'public_key': os.getenv('VAPID_PUBLIC_KEY', '')})

    @action(detail=False, methods=['post'])
    def push_subscribe(self, request):
        """Body: {subscription: {endpoint, keys: {p256dh, auth}}, teams: [ids], prefs: {...}}"""
        from apps.engage.models import PushSubscription
        sub = request.data.get('subscription') or {}
        keys = sub.get('keys') or {}
        endpoint = sub.get('endpoint') or ''
        # Only real browser push services, never arbitrary URLs.
        allowed = ('https://fcm.googleapis.com/', 'https://updates.push.services.mozilla.com/',
                   'https://web.push.apple.com/', 'https://wns2-', 'https://jmt17.google.com/')
        if not endpoint.startswith(allowed) or not keys.get('p256dh') or not keys.get('auth'):
            return Response({'error': 'invalid subscription'}, status=400)
        teams = [int(t) for t in (request.data.get('teams') or []) if str(t).isdigit()][:50]
        prefs = {k: bool(v) for k, v in (request.data.get('prefs') or {}).items() if k in ('digest', 'results', 'teams')}
        obj, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint[:1000],
            defaults={'p256dh': keys['p256dh'][:200], 'auth': keys['auth'][:100], 'teams': teams, 'prefs': prefs, 'failures': 0},
        )
        return Response({'ok': True, 'created': created})

    @action(detail=False, methods=['post'])
    def push_unsubscribe(self, request):
        from apps.engage.models import PushSubscription
        PushSubscription.objects.filter(endpoint=(request.data.get('endpoint') or '')[:1000]).delete()
        return Response({'ok': True})

    # ─── Score challenge (Phase 6) ──────────────────────────────────────────
    def _player(self, request):
        from apps.engage.game import hash_token
        from apps.engage.models import GamePlayer
        token = request.headers.get('X-Game-Token', '')
        return GamePlayer.objects.filter(token_hash=hash_token(token)).first() if token else None

    @action(detail=False, methods=['post'])
    def game_join(self, request):
        """Body {nickname}. Returns a device token: keep it, it is the only key to this player."""
        from apps.engage.game import NICK_RE, BLOCKED, hash_token, new_token
        from apps.engage.models import GamePlayer
        nick = (request.data.get('nickname') or '').strip()
        if not NICK_RE.match(nick) or nick.lower() in BLOCKED:
            return Response({'error': 'Nickname: 3-20 letters, numbers, spaces, . _ -'}, status=400)
        if GamePlayer.objects.filter(nickname__iexact=nick).exists():
            return Response({'error': 'That nickname is taken'}, status=409)
        token = new_token()
        GamePlayer.objects.create(nickname=nick, token_hash=hash_token(token))
        return Response({'nickname': nick, 'token': token})

    @action(detail=False, methods=['get'])
    def game_week(self, request):
        """This week's matches, your picks (with X-Game-Token), and the leaderboard. ?week=-1 for last week."""
        from apps.engage.game import week_bounds, week_matches, leaderboard, points
        from apps.engage.models import GamePick
        try:
            offset = max(min(int(request.query_params.get('week', 0)), 0), -12)
        except ValueError:
            offset = 0
        start, end = week_bounds(timezone.now() + timedelta(days=7 * offset))
        player = self._player(request)
        mine = {p.match_id: p for p in GamePick.objects.filter(player=player, match__kickoff_at__gte=start, match__kickoff_at__lt=end)} if player else {}
        now = timezone.now()
        rows = []
        for m in week_matches(start, end):
            p = mine.get(m.id)
            rows.append({
                'id': m.id, 'home': m.home_team.name, 'away': m.away_team.name, 'league': m.season.league.name,
                'kickoff_at': m.kickoff_at.isoformat(), 'open': m.kickoff_at > now and m.status == 'scheduled',
                'status': m.status, 'score': [m.home_score, m.away_score] if m.status == 'finished' else None,
                'pick': [p.home, p.away] if p else None,
                'points': points(p.home, p.away, m.home_score, m.away_score) if p and m.status == 'finished' else None,
            })
        return Response({'week_start': start.date().isoformat(), 'week_end': (end - timedelta(days=1)).date().isoformat(),
                         'player': player.nickname if player else None, 'matches': rows,
                         'leaderboard': leaderboard(start, end)})

    @action(detail=False, methods=['post'])
    def game_pick(self, request):
        """Body {match_id, home, away} with X-Game-Token. Allowed until kickoff."""
        from apps.engage.game import LEAGUES
        from apps.engage.models import GamePick
        from apps.matches.models import Match
        player = self._player(request)
        if not player:
            return Response({'error': 'Join the challenge first'}, status=401)
        try:
            home, away = int(request.data.get('home')), int(request.data.get('away'))
            match = Match.objects.get(id=int(request.data.get('match_id')), season__league__code__in=LEAGUES)
        except (TypeError, ValueError, Match.DoesNotExist):
            return Response({'error': 'Invalid pick'}, status=400)
        if not (0 <= home <= 15 and 0 <= away <= 15):
            return Response({'error': 'Scores must be 0-15'}, status=400)
        if not match.kickoff_at or match.kickoff_at <= timezone.now() or match.status != 'scheduled':
            return Response({'error': 'This match has started; picks are closed'}, status=400)
        GamePick.objects.update_or_create(player=player, match=match, defaults={'home': home, 'away': away})
        return Response({'ok': True})
