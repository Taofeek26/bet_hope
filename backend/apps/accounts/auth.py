"""
Sign in with a username OR an email address (Phase 7).

The JWT login (`/auth/token/`) still takes the field "username"; whatever is
typed there is matched case-insensitively against usernames and emails, then
checked with the user's real username. Older accounts (username = email)
keep working.
"""
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class UsernameOrEmailTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        ident = (attrs.get(self.username_field) or '').strip()
        User = get_user_model()
        match = User.objects.filter(Q(username__iexact=ident) | Q(email__iexact=ident)).order_by('id').first()
        attrs[self.username_field] = match.username if match else ident
        return super().validate(attrs)


class UsernameOrEmailTokenView(TokenObtainPairView):
    serializer_class = UsernameOrEmailTokenSerializer
