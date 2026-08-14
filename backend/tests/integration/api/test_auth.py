from __future__ import annotations

from tests.auth_tokens import (
    TEST_USER_ID,
    fake_jwks_client,
    generate_ec_keypair,
    make_access_token,
)
from tests.integration.api.conftest import CREATE_PAYLOAD, api_client, unique_tmp


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAnalysisAuthRequired:
    def test_missing_authorization_header_returns_401(self, tmp_path):
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.get("/api/analyses")
        assert response.status_code == 401
        body = response.json()
        assert body["error"] == "unauthorized"
        assert body["message"] == "Missing Authorization header"

    def test_malformed_bearer_header_returns_401(self, tmp_path):
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.get("/api/analyses", headers={"Authorization": "Bearer"})
        assert response.status_code == 401
        body = response.json()
        assert body["error"] == "unauthorized"
        assert body["message"] == "Invalid Authorization header"

    def test_invalid_token_returns_401(self, tmp_path, monkeypatch):
        _private_key, public_key = generate_ec_keypair()
        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(public_key))
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.get("/api/analyses", headers=_auth_header("not-a-jwt"))
        assert response.status_code == 401
        body = response.json()
        assert body["error"] == "unauthorized"
        assert body["message"] == "Invalid or expired token"

    def test_valid_token_reaches_list_route(self, tmp_path, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token = make_access_token(private_key, sub=TEST_USER_ID)
        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(public_key))
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.get("/api/analyses", headers=_auth_header(token))
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_valid_token_can_create_analysis(self, tmp_path, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token = make_access_token(private_key)
        monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(public_key))
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.post(
                "/api/analyses",
                json=CREATE_PAYLOAD,
                headers=_auth_header(token),
            )
        assert response.status_code == 201
        assert response.json()["product_name"] == CREATE_PAYLOAD["product_name"]

    def test_health_does_not_require_auth(self, tmp_path):
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_docs_and_openapi_do_not_require_auth(self, tmp_path):
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            docs = client.get("/docs")
            openapi = client.get("/openapi.json")
        assert docs.status_code == 200
        assert openapi.status_code == 200
