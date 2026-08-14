from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

TEST_SUPABASE_URL = "https://example.supabase.co"
TEST_ISSUER = f"{TEST_SUPABASE_URL}/auth/v1"
TEST_USER_ID = "user-123"


def generate_ec_keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


def make_access_token(
    private_key,
    *,
    sub: str = TEST_USER_ID,
    aud: str = "authenticated",
    iss: str = TEST_ISSUER,
    expired: bool = False,
    extra: dict | None = None,
    algorithm: str = "ES256",
    kid: str = "test-kid",
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "aud": aud,
        "iss": iss,
        "role": "authenticated",
        "iat": now,
        "exp": now - timedelta(hours=1) if expired else now + timedelta(hours=1),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, private_key, algorithm=algorithm, headers={"kid": kid})


def fake_jwks_client(public_key):
    return SimpleNamespace(get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=public_key))
