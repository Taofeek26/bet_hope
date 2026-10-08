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
