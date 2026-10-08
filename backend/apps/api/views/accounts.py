"""
User accounts (Phase 7).

  POST   /auth/register/            {username, email, password, name} -> JWT pair
  POST   /auth/token/               {username: <username or email>, password}
  GET    /me/  PATCH /me/  DELETE /me/
  POST   /me/password/              {old_password, new_password}
  GET    /me/bets/  POST /me/bets/  {bets: [...]} (upsert by client_id)
  DELETE /me/bets/<client_id>/
  Admin (staff only):
  GET    /admin-users/?search=      users with bet statistics
  GET    /admin-users/<id>/         one user with their bets
  POST   /admin-users/<id>/set_active/      {active}
  POST   /admin-users/<id>/reset_password/  -> temporary password (shown once)
"""
import re
import secrets
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserBet, UserProfile
from apps.accounts.settle import settle_bets

User = get_user_model()
USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,30}$')


class RegisterThrottle(AnonRateThrottle):
    rate = '10/hour'


def _profile(user):
    return UserProfile.objects.get_or_create(user=user)[0]


def _me(user):
    p = _profile(user)
    return {
        'id': user.id, 'username': user.username, 'email': user.email, 'name': p.display_name or user.first_name,
        'is_staff': user.is_staff, 'joined': user.date_joined.isoformat(),
        'favourite_teams': p.favourite_teams, 'favourite_leagues': p.favourite_leagues,
        'weekly_limit': p.weekly_limit,
    }


def _bet_row(b, st=None, profit=None):
    return {
        'id': b.client_id, 'placedAt': b.placed_at.isoformat(), 'bookmaker': b.bookmaker,
        'stake': float(b.stake), 'odds': float(b.odds), 'selections': b.selections, 'source': b.source,
        'bookingCode': b.booking_code or None, 'ticketId': b.ticket_id or None, 'legOdds': b.leg_odds or None,
        **({'status': st, 'profit': profit} if st else {}),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterThrottle])
def register(request):
    email = (request.data.get('email') or '').strip().lower()
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''
    name = (request.data.get('name') or '').strip()[:60]
    if not USERNAME_RE.match(username):
        return Response({'error': 'Username: 3-30 letters, numbers, dots, dashes or underscores (no spaces or @)'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return Response({'error': 'Enter a valid email address'}, status=400)
    if User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).exists():
        return Response({'error': 'That username is taken'}, status=409)
    if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
        return Response({'error': 'An account with this email already exists. Sign in instead.'}, status=409)
    try:
        password_validation.validate_password(password, User(username=username, email=email, first_name=name))
    except ValidationError as e:
        return Response({'error': ' '.join(e.messages)}, status=400)
    with transaction.atomic():
        user = User.objects.create_user(username=username, email=email, password=password, first_name=name)
        UserProfile.objects.create(user=user, display_name=name)
    refresh = RefreshToken.for_user(user)
    return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'user': _me(user)}, status=201)


class MeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(_me(request.user))

    @action(detail=False, methods=['patch'], url_path='update')
    def update_me(self, request):
        p = _profile(request.user)
        d = request.data
        if 'name' in d:
            p.display_name = str(d['name'] or '').strip()[:60]
        if 'favourite_teams' in d:
            p.favourite_teams = [int(x) for x in (d['favourite_teams'] or []) if str(x).isdigit()][:200]
        if 'favourite_leagues' in d:
            p.favourite_leagues = [str(x)[:10] for x in (d['favourite_leagues'] or [])][:50]
        if 'weekly_limit' in d:
            v = d['weekly_limit']
            p.weekly_limit = int(v) if v not in (None, '') and str(v).isdigit() else None
        p.save()
        return Response(_me(request.user))

    @action(detail=False, methods=['post'])
    def password(self, request):
        u = request.user
        if not u.check_password(request.data.get('old_password') or ''):
            return Response({'error': 'Current password is wrong'}, status=400)
        new = request.data.get('new_password') or ''
        try:
            password_validation.validate_password(new, u)
        except ValidationError as e:
            return Response({'error': ' '.join(e.messages)}, status=400)
        u.set_password(new)
        u.save()
        return Response({'ok': True})

    @action(detail=False, methods=['post'], url_path='delete')
    def delete_me(self, request):
        """Delete the account and everything stored with it (right to erasure)."""
        if not request.user.check_password(request.data.get('password') or ''):
            return Response({'error': 'Password is wrong'}, status=400)
        if request.user.is_superuser:
            return Response({'error': 'The main admin account cannot delete itself here'}, status=400)
        request.user.delete()
        return Response({'ok': True})

    @action(detail=False, methods=['get', 'post'])
    def bets(self, request):
        if request.method == 'GET':
            rows = list(UserBet.objects.filter(user=request.user)[:500])
            return Response({'bets': [_bet_row(b) for b in rows]})
        saved = 0
        for b in (request.data.get('bets') or [])[:200]:
            try:
                cid = str(b['id'])[:80]
                stake, odds = Decimal(str(b['stake'])), Decimal(str(b['odds']))
                placed = parse_datetime(str(b.get('placedAt') or '')) or timezone.now()
                sels = b.get('selections') or []
                if stake <= 0 or odds <= 1 or not isinstance(sels, list) or not sels:
                    continue
            except (KeyError, InvalidOperation, TypeError, ValueError):
                continue
            UserBet.objects.update_or_create(user=request.user, client_id=cid, defaults={
                'placed_at': placed, 'bookmaker': str(b.get('bookmaker') or '')[:30], 'stake': stake,
                'odds': odds.quantize(Decimal('0.01')), 'selections': sels[:30],
                'source': 'extension' if b.get('source') == 'extension' else 'manual',
                'booking_code': str(b.get('bookingCode') or '')[:40], 'ticket_id': str(b.get('ticketId') or '')[:60],
                'leg_odds': b.get('legOdds') if isinstance(b.get('legOdds'), dict) else {},
            })
            saved += 1
        return Response({'saved': saved})

    @action(detail=False, methods=['post'], url_path='bets/delete')
    def delete_bet(self, request):
        n, _ = UserBet.objects.filter(user=request.user, client_id=str(request.data.get('id') or '')).delete()
        return Response({'deleted': n})


class AdminUsersViewSet(viewsets.ViewSet):
    """Staff only: every user, their activity and their bets."""
    permission_classes = [IsAdminUser]

    def list(self, request):
        qs = User.objects.all().select_related('profile').annotate(n_bets=Count('bets')).order_by('-date_joined')
        q = (request.query_params.get('search') or '').strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(profile__display_name__icontains=q))
        users = list(qs[:500])
        bets = list(UserBet.objects.filter(user__in=users))
        stats = {}
        for b, st, profit in settle_bets(bets):
            s = stats.setdefault(b.user_id, {'staked': 0.0, 'profit': 0.0, 'won': 0, 'lost': 0, 'pending': 0})
            s['staked'] += float(b.stake)
            s['profit'] += profit
            s[st if st in ('won', 'lost', 'pending') else 'pending'] += 1
        rows = []
        for u in users:
            p = getattr(u, 'profile', None)
            s = stats.get(u.id, {'staked': 0.0, 'profit': 0.0, 'won': 0, 'lost': 0, 'pending': 0})
            rows.append({
                'id': u.id, 'username': u.username, 'email': u.email or u.username, 'name': (p.display_name if p else '') or u.first_name,
                'joined': u.date_joined.isoformat(), 'last_login': u.last_login.isoformat() if u.last_login else None,
                'is_active': u.is_active, 'is_staff': u.is_staff, 'bets': u.n_bets,
                'favourites': len(p.favourite_teams) if p else 0,
                'staked': round(s['staked'], 2), 'profit': round(s['profit'], 2),
                'won': s['won'], 'lost': s['lost'], 'pending': s['pending'],
            })
        total = {'users': User.objects.count(), 'active_7d': User.objects.filter(last_login__gte=timezone.now() - timezone.timedelta(days=7)).count(),
                 'bets': UserBet.objects.count(), 'staked': round(sum(r['staked'] for r in rows), 2)}
        return Response({'totals': total, 'users': rows})

    def retrieve(self, request, pk=None):
        try:
            u = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        rows = [_bet_row(b, st, profit) for b, st, profit in settle_bets(list(UserBet.objects.filter(user=u)[:500]))]
        return Response({'user': _me(u) | {'is_active': u.is_active, 'last_login': u.last_login.isoformat() if u.last_login else None}, 'bets': rows})

    @action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        u = User.objects.filter(pk=pk).first()
        if not u:
            return Response({'error': 'Not found'}, status=404)
        if u == request.user or u.is_superuser:
            return Response({'error': 'You cannot disable this account'}, status=400)
        u.is_active = bool(request.data.get('active'))
        u.save(update_fields=['is_active'])
        return Response({'ok': True, 'is_active': u.is_active})

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """No email service yet: give the admin a temporary password to pass on."""
        u = User.objects.filter(pk=pk).first()
        if not u:
            return Response({'error': 'Not found'}, status=404)
        if u.is_superuser and u != request.user:
            return Response({'error': 'Not allowed for the main admin'}, status=400)
        temp = secrets.token_urlsafe(9)
        u.set_password(temp)
        u.save()
        return Response({'temporary_password': temp})
