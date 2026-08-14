"""Supabase JWT verification for FastAPI.

Access tokens are verified locally against the project's JWKS public keys.
No Admin API, service_role key, or database lookup is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Header
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError

from app.api.deps import get_app_settings
from app.api.errors import UnauthorizedError
from app.config import Settings

SUPABASE_AUDIENCE = "authenticated"
ALLOWED_ALGORITHMS = ("ES256", "RS256")
CLOCK_SKEW_LEEWAY_SECONDS = 30
JWKS_CACHE_LIFESPAN_SECONDS = 3600


@dataclass(frozen=True)
class AuthenticatedUser:
    """Authenticated caller derived from a verified Supabase access token."""

    user_id: str
    role: str | None = None


@lru_cache(maxsize=8)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Return a JWKS client cached per URL so requests reuse fetched keys."""
    return PyJWKClient(
        jwks_url,
        cache_jwk_set=True,
        lifespan=JWKS_CACHE_LIFESPAN_SECONDS,
        timeout=5,
    )


def reset_jwks_client_cache() -> None:
    get_jwks_client.cache_clear()


def parse_bearer_token(authorization: str | None) -> str:
    if authorization is None or not authorization.strip():
        raise UnauthorizedError("Missing Authorization header")

    scheme, separator, remainder = authorization.strip().partition(" ")
    token = remainder.strip()
    if separator != " " or scheme.lower() != "bearer" or not token or any(ch.isspace() for ch in token):
        raise UnauthorizedError("Invalid Authorization header")
    return token


def _signing_key(jwks_client: PyJWKClient, token: str):
    try:
        return jwks_client.get_signing_key_from_jwt(token)
    except PyJWKClientError:
        # Unknown kid is often key rotation; refetch once then fail closed.
        if getattr(jwks_client, "jwk_set_cache", None) is not None:
            jwks_client.jwk_set_cache = None
        return jwks_client.get_signing_key_from_jwt(token)


def decode_supabase_token(token: str, settings: Settings) -> AuthenticatedUser:
    jwks_client = get_jwks_client(settings.supabase_jwks_url)
    try:
        signing_key = _signing_key(jwks_client, token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=list(ALLOWED_ALGORITHMS),
            audience=SUPABASE_AUDIENCE,
            issuer=settings.supabase_jwt_issuer,
            leeway=CLOCK_SKEW_LEEWAY_SECONDS,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except (InvalidTokenError, PyJWKClientError, KeyError, ValueError, AttributeError) as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise UnauthorizedError("Invalid or expired token")

    role = claims.get("role")
    return AuthenticatedUser(
        user_id=user_id,
        role=role if isinstance(role, str) else None,
    )


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    settings: Settings = Depends(get_app_settings),
) -> AuthenticatedUser:
    token = parse_bearer_token(authorization)
    return decode_supabase_token(token, settings)
