from __future__ import annotations

import pytest
from jwt import PyJWKClientError

from app.api.errors import UnauthorizedError
from app.auth import decode_supabase_token, parse_bearer_token, reset_jwks_client_cache
from app.config import Settings
from tests.auth_tokens import (
    TEST_ISSUER,
    TEST_SUPABASE_URL,
    TEST_USER_ID,
    fake_jwks_client,
    generate_ec_keypair,
    make_access_token,
)


def _settings(**overrides) -> Settings:
    defaults = {"supabase_url": TEST_SUPABASE_URL}
    defaults.update(overrides)
    return Settings(**defaults)


class TestParseBearerToken:
    def test_extracts_token(self):
        assert parse_bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"

    def test_accepts_lowercase_scheme(self):
        assert parse_bearer_token("bearer abc.def.ghi") == "abc.def.ghi"

    def test_missing_header(self):
        with pytest.raises(UnauthorizedError, match="Missing Authorization header"):
            parse_bearer_token(None)

    def test_empty_header(self):
        with pytest.raises(UnauthorizedError, match="Missing Authorization header"):
            parse_bearer_token("   ")

    def test_wrong_scheme(self):
        with pytest.raises(UnauthorizedError, match="Invalid Authorization header"):
            parse_bearer_token("Basic abc.def.ghi")

    def test_missing_token(self):
        with pytest.raises(UnauthorizedError, match="Invalid Authorization header"):
            parse_bearer_token("Bearer")

    def test_token_with_whitespace(self):
        with pytest.raises(UnauthorizedError, match="Invalid Authorization header"):
            parse_bearer_token("Bearer abc def")


class TestDecodeSupabaseToken:
    def setup_method(self):
        reset_jwks_client_cache()

    def teardown_method(self):
        reset_jwks_client_cache()

    def test_valid_token_returns_user(self, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token = make_access_token(private_key)
        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(public_key))

        user = decode_supabase_token(token, _settings())
        assert user.user_id == TEST_USER_ID
        assert user.role == "authenticated"

    def test_expired_token_rejected(self, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token = make_access_token(private_key, expired=True)
        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(public_key))

        with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
            decode_supabase_token(token, _settings())

    def test_wrong_issuer_rejected(self, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token = make_access_token(private_key, iss="https://other.supabase.co/auth/v1")
        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(public_key))

        with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
            decode_supabase_token(token, _settings())

    def test_wrong_audience_rejected(self, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token = make_access_token(private_key, aud="anon")
        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(public_key))

        with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
            decode_supabase_token(token, _settings())

    def test_wrong_signature_rejected(self, monkeypatch):
        private_key, _ = generate_ec_keypair()
        _, other_public = generate_ec_keypair()
        token = make_access_token(private_key)
        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(other_public))

        with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
            decode_supabase_token(token, _settings())

    def test_jwks_failure_rejected(self, monkeypatch):
        private_key, _ = generate_ec_keypair()
        token = make_access_token(private_key)

        class FailingClient:
            def get_signing_key_from_jwt(self, _token):
                raise PyJWKClientError("unable to find a signing key")

        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: FailingClient())

        with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
            decode_supabase_token(token, _settings())

    def test_jwks_url_derived_from_settings(self):
        settings = _settings(supabase_url="https://proj.supabase.co/")
        assert settings.supabase_url == "https://proj.supabase.co"
        assert settings.supabase_jwt_issuer == "https://proj.supabase.co/auth/v1"
        assert settings.supabase_jwks_url == "https://proj.supabase.co/auth/v1/.well-known/jwks.json"
        assert TEST_ISSUER == f"{TEST_SUPABASE_URL}/auth/v1"
