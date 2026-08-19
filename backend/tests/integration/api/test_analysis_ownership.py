from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.db.tables import Analysis, MarketCache, MarketData
from app.repositories.mappers import analysis_from_create, cache_from_upsert
from tests.auth_tokens import fake_jwks_client, generate_ec_keypair, make_access_token
from tests.integration.api.conftest import CREATE_PAYLOAD, api_client, unique_tmp
from tests.integration.db.conftest import _analysis, _cache_upsert


USER_A = "user-a"
USER_B = "user-b"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _patch_jwks(monkeypatch, public_key) -> None:
    monkeypatch.setattr("app.auth.get_jwks_client", lambda _url: fake_jwks_client(public_key))


class TestAnalysisOwnershipApi:
    def test_users_only_see_their_own_analyses(self, tmp_path, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token_a = make_access_token(private_key, sub=USER_A)
        token_b = make_access_token(private_key, sub=USER_B)
        _patch_jwks(monkeypatch, public_key)

        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            created_a = client.post(
                "/api/analyses",
                json={**CREATE_PAYLOAD, "product_name": "User A Serum"},
                headers=_auth_header(token_a),
            )
            created_b = client.post(
                "/api/analyses",
                json={**CREATE_PAYLOAD, "product_name": "User B Serum"},
                headers=_auth_header(token_b),
            )
            assert created_a.status_code == 201
            assert created_b.status_code == 201
            id_a = created_a.json()["id"]
            id_b = created_b.json()["id"]
            assert "user_id" not in created_a.json()
            assert "user_id" not in created_b.json()

            session = client.app.state.session_factory()
            try:
                row_a = session.scalar(select(Analysis).where(Analysis.id == UUID(id_a)))
                row_b = session.scalar(select(Analysis).where(Analysis.id == UUID(id_b)))
                assert row_a is not None and row_a.user_id == USER_A
                assert row_b is not None and row_b.user_id == USER_B
            finally:
                session.close()

            listed_a = client.get("/api/analyses", headers=_auth_header(token_a))
            listed_b = client.get("/api/analyses", headers=_auth_header(token_b))
            assert listed_a.status_code == 200
            assert listed_b.status_code == 200
            assert listed_a.json()["total"] == 1
            assert listed_b.json()["total"] == 1
            assert listed_a.json()["items"][0]["id"] == id_a
            assert listed_b.json()["items"][0]["id"] == id_b
            assert listed_a.json()["items"][0]["product_name"] == "User A Serum"
            assert listed_b.json()["items"][0]["product_name"] == "User B Serum"

            assert client.get(f"/api/analyses/{id_a}", headers=_auth_header(token_a)).status_code == 200
            foreign = client.get(f"/api/analyses/{id_a}", headers=_auth_header(token_b))
            assert foreign.status_code == 404
            assert foreign.json()["error"] == "analysis_not_found"
            assert client.get(f"/api/analyses/{id_b}", headers=_auth_header(token_a)).status_code == 404

    def test_client_cannot_choose_owner(self, tmp_path, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token_a = make_access_token(private_key, sub=USER_A)
        _patch_jwks(monkeypatch, public_key)

        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.post(
                "/api/analyses",
                json={**CREATE_PAYLOAD, "user_id": USER_B},
                headers=_auth_header(token_a),
            )
            assert response.status_code == 201
            analysis_id = response.json()["id"]
            session = client.app.state.session_factory()
            try:
                row = session.scalar(select(Analysis).where(Analysis.id == UUID(analysis_id)))
                assert row is not None
                assert row.user_id == USER_A
            finally:
                session.close()

    def test_legacy_null_owner_is_hidden(self, tmp_path, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token_a = make_access_token(private_key, sub=USER_A)
        token_b = make_access_token(private_key, sub=USER_B)
        _patch_jwks(monkeypatch, public_key)

        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            session = client.app.state.session_factory()
            try:
                legacy = analysis_from_create(_analysis(product_name="Orphan Analysis"))
                legacy.user_id = None
                session.add(legacy)
                session.commit()
                session.refresh(legacy)
                legacy_id = str(legacy.id)
            finally:
                session.close()

            listed_a = client.get("/api/analyses", headers=_auth_header(token_a))
            listed_b = client.get("/api/analyses", headers=_auth_header(token_b))
            assert listed_a.status_code == 200
            assert listed_b.status_code == 200
            assert listed_a.json()["total"] == 0
            assert listed_b.json()["total"] == 0
            assert listed_a.json()["items"] == []
            assert listed_b.json()["items"] == []

            as_a = client.get(f"/api/analyses/{legacy_id}", headers=_auth_header(token_a))
            as_b = client.get(f"/api/analyses/{legacy_id}", headers=_auth_header(token_b))
            assert as_a.status_code == 404
            assert as_b.status_code == 404
            assert as_a.json()["error"] == "analysis_not_found"

    def test_unauthenticated_still_401(self, tmp_path):
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.get("/api/analyses")
        assert response.status_code == 401
        assert response.json()["error"] == "unauthorized"

    def test_owner_can_delete_own_analysis(self, tmp_path, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token_a = make_access_token(private_key, sub=USER_A)
        token_b = make_access_token(private_key, sub=USER_B)
        _patch_jwks(monkeypatch, public_key)

        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            created = client.post(
                "/api/analyses",
                json={**CREATE_PAYLOAD, "product_name": "User A Serum"},
                headers=_auth_header(token_a),
            )
            assert created.status_code == 201
            analysis_id = created.json()["id"]

            session = client.app.state.session_factory()
            try:
                cache_row = cache_from_upsert(_cache_upsert())
                session.add(cache_row)
                session.commit()
                cache_id = cache_row.id
                assert session.scalar(select(MarketData).where(MarketData.analysis_id == UUID(analysis_id))) is not None
                cache_count = session.scalar(select(func.count()).select_from(MarketCache))
                assert cache_count == 1
            finally:
                session.close()

            foreign = client.delete(f"/api/analyses/{analysis_id}", headers=_auth_header(token_b))
            assert foreign.status_code == 404
            assert foreign.json()["error"] == "analysis_not_found"
            still_there = client.get(f"/api/analyses/{analysis_id}", headers=_auth_header(token_a))
            assert still_there.status_code == 200

            deleted = client.delete(f"/api/analyses/{analysis_id}", headers=_auth_header(token_a))
            assert deleted.status_code == 204
            missing = client.get(f"/api/analyses/{analysis_id}", headers=_auth_header(token_a))
            assert missing.status_code == 404
            assert missing.json()["error"] == "analysis_not_found"
            listed = client.get("/api/analyses", headers=_auth_header(token_a))
            assert listed.status_code == 200
            assert listed.json()["total"] == 0

            session = client.app.state.session_factory()
            try:
                assert session.scalar(select(MarketData).where(MarketData.analysis_id == UUID(analysis_id))) is None
                leftover_cache = session.scalar(select(MarketCache).where(MarketCache.id == cache_id))
                assert leftover_cache is not None
            finally:
                session.close()

    def test_delete_unauthenticated_returns_401(self, tmp_path):
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.delete(f"/api/analyses/{uuid4()}")
        assert response.status_code == 401
        assert response.json()["error"] == "unauthorized"

    def test_delete_nonexistent_returns_404(self, tmp_path, monkeypatch):
        private_key, public_key = generate_ec_keypair()
        token_a = make_access_token(private_key, sub=USER_A)
        _patch_jwks(monkeypatch, public_key)
        missing = UUID("11111111-1111-1111-1111-111111111111")

        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.delete(f"/api/analyses/{missing}", headers=_auth_header(token_a))
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "analysis_not_found"
        assert body["details"]["analysis_id"] == str(missing)

    def test_health_still_public(self, tmp_path):
        with api_client(unique_tmp(tmp_path), authenticate=False) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
