"""Compatibility layer kept while the project returns to SimpleJWT blacklist.

This module intentionally delegates to the official relational blacklist
implementation so older imports do not break during the transition.
"""

from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenRefreshSerializer, TokenVerifySerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView


class RedisBlacklistJWTAuthentication(JWTAuthentication):
    """Backward-compatible alias for the standard SimpleJWT authentication."""


class RedisTokenRefreshSerializer(TokenRefreshSerializer):
    """Backward-compatible alias for the standard SimpleJWT serializer."""


class RedisTokenVerifySerializer(TokenVerifySerializer):
    """Backward-compatible alias for the standard SimpleJWT serializer."""


class RedisTokenRefreshView(TokenRefreshView):
    serializer_class = RedisTokenRefreshSerializer


class RedisTokenVerifyView(TokenVerifyView):
    serializer_class = RedisTokenVerifySerializer


def blacklist_token(token) -> None:
    """Blacklist a refresh token using the official SimpleJWT models."""
    if token is None:
        return
    if isinstance(token, str):
        token = RefreshToken(token)
    if isinstance(token, UntypedToken):
        return
    token.blacklist()


def revoke_user_tokens(user_id: str) -> None:
    """Blacklist all outstanding refresh tokens for a user."""
    tokens = OutstandingToken.objects.filter(user_id=user_id)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)


def is_token_revoked(token) -> bool:
    """Compatibility helper based on the official blacklist tables."""
    if token is None or isinstance(token, UntypedToken):
        return False
    jti = getattr(token, "payload", {}).get("jti")
    if not jti:
        return False
    return BlacklistedToken.objects.filter(token__jti=jti).exists()
