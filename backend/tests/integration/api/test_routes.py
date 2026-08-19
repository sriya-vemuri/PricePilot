from __future__ import annotations

from time import sleep
from uuid import uuid4

from app.clients.tavily import TavilyNotConfiguredError
from app.repositories.errors import DatabaseError
from app.services.errors import PricingCalculationError
from app.services.market_research.models import (
    WARNING_INSUFFICIENT_MARKET_DATA,
    WARNING_STAGE3_LOW_TRUST,
    WARNING_TAVILY_UNAVAILABLE,
)
from tests.integration.api.conftest import CREATE_PAYLOAD, SECRET_TAVILY_KEY, api_client, unique_tmp
from tests.integration.test_analysis_orchestrator import FakeMarketResearch, _empty_market, _market


def _assert_no_secrets(payload: dict) -> None:
    text = str(payload).lower()
    assert SECRET_TAVILY_KEY.lower() not in text
    assert "authorization" not in text
    assert "bearer " not in text


class TestHealthAndDocs:
    def test_health_ok(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_docs_and_openapi_available(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            docs = client.get("/docs")
            openapi = client.get("/openapi.json")
        assert docs.status_code == 200
        assert openapi.status_code == 200
        assert openapi.json()["info"]["title"] == "PricePilot API"


class TestCreateAnalysis:
    def test_create_reliable_analysis_returns_201(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            response = client.post("/api/analyses", json=CREATE_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert body["id"]
        assert body["recommended_price"] > 0
        assert body["market_data"]["comparable_prices"]
        assert body["market_data"]["has_reliable_data"] is True
        assert body["product_name"] == CREATE_PAYLOAD["product_name"]

    def test_create_fallback_analysis(self, tmp_path):
        market = FakeMarketResearch(_empty_market())
        with api_client(unique_tmp(tmp_path), market=market) as client:
            response = client.post("/api/analyses", json=CREATE_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert body["recommended_price"] > 0
        assert body["market_data"]["has_reliable_data"] is False
        assert body["market_data"]["comparable_prices"] == []
        assert body["recommended_price"] == body["baseline_price"]
        assert WARNING_INSUFFICIENT_MARKET_DATA in body["market_warnings"]

    def test_tavily_outage_still_returns_201(self, tmp_path):
        market = FakeMarketResearch(
            _empty_market(warnings=[WARNING_TAVILY_UNAVAILABLE, WARNING_INSUFFICIENT_MARKET_DATA])
        )
        with api_client(unique_tmp(tmp_path), market=market) as client:
            response = client.post("/api/analyses", json=CREATE_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert WARNING_TAVILY_UNAVAILABLE in body["market_warnings"]
        assert body["recommended_price"] > 0

    def test_missing_tavily_key_returns_503(self, tmp_path):
        market = FakeMarketResearch(error=TavilyNotConfiguredError("TAVILY_API_KEY is not configured"))
        with api_client(unique_tmp(tmp_path), market=market) as client:
            response = client.post("/api/analyses", json=CREATE_PAYLOAD)
            listed = client.get("/api/analyses")
        assert response.status_code == 503
        body = response.json()
        assert body["error"] == "tavily_not_configured"
        assert "message" in body
        assert listed.json()["total"] == 0
        _assert_no_secrets(body)

    def test_pricing_failure_returns_500(self, tmp_path):
        class FailingPricingOrchestrator:
            async def create_analysis(self, _request, user_id: str):
                raise PricingCalculationError("Unexpected pricing-engine failure") from RuntimeError("boom")

        with api_client(unique_tmp(tmp_path), orchestrator=FailingPricingOrchestrator()) as client:
            response = client.post("/api/analyses", json=CREATE_PAYLOAD)
        assert response.status_code == 500
        body = response.json()
        assert body["error"] == "pricing_calculation_error"
        assert "boom" not in str(body).lower()
        _assert_no_secrets(body)

    def test_database_failure_returns_500(self, tmp_path):
        class FailingDbOrchestrator:
            async def create_analysis(self, _request, user_id: str):
                raise DatabaseError("Failed to save analysis") from RuntimeError("sqlite exploded")

        with api_client(unique_tmp(tmp_path), orchestrator=FailingDbOrchestrator()) as client:
            response = client.post("/api/analyses", json=CREATE_PAYLOAD)
        assert response.status_code == 500
        body = response.json()
        assert body["error"] == "database_error"
        assert "sqlite exploded" not in str(body).lower()
        _assert_no_secrets(body)

    def test_warnings_are_returned(self, tmp_path):
        market = FakeMarketResearch(_market(warnings=[WARNING_STAGE3_LOW_TRUST], data_trust="low"))
        with api_client(unique_tmp(tmp_path), market=market) as client:
            response = client.post("/api/analyses", json=CREATE_PAYLOAD)
        assert response.status_code == 201
        assert WARNING_STAGE3_LOW_TRUST in response.json()["market_warnings"]


class TestListAndPagination:
    def test_list_returns_items_total_limit_offset(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            first = client.post("/api/analyses", json={**CREATE_PAYLOAD, "product_name": "Older Serum"})
            sleep(0.02)
            second = client.post("/api/analyses", json={**CREATE_PAYLOAD, "product_name": "Newer Serum"})
            listed = client.get("/api/analyses")
        assert listed.status_code == 200
        body = listed.json()
        assert body["total"] == 2
        assert body["limit"] == 50
        assert body["offset"] == 0
        names = [item["product_name"] for item in body["items"]]
        assert names == ["Newer Serum", "Older Serum"]
        assert body["items"][0]["id"] == second.json()["id"]
        assert body["items"][1]["id"] == first.json()["id"]
        assert "competitor_price_1" in body["items"][0]["market_data"]
        assert "has_reliable_data" in body["items"][0]["market_data"]
        assert body["items"][0]["baseline_price"] == second.json()["baseline_price"]

    def test_pagination_limit_and_offset(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            for index in range(3):
                client.post("/api/analyses", json={**CREATE_PAYLOAD, "product_name": f"Serum {index}"})
                sleep(0.02)
            page = client.get("/api/analyses", params={"limit": 2, "offset": 0})
            rest = client.get("/api/analyses", params={"limit": 2, "offset": 2})
        assert page.status_code == 200
        assert rest.status_code == 200
        assert page.json()["total"] == 3
        assert len(page.json()["items"]) == 2
        assert rest.json()["total"] == 3
        assert len(rest.json()["items"]) == 1

    def test_limit_over_100_rejected(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            response = client.get("/api/analyses", params={"limit": 101})
        assert response.status_code == 422
        assert response.json()["error"] == "validation_error"

    def test_negative_offset_rejected(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            response = client.get("/api/analyses", params={"offset": -1})
        assert response.status_code == 422
        assert response.json()["error"] == "validation_error"


class TestGetAnalysis:
    def test_get_existing_analysis(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            created = client.post("/api/analyses", json=CREATE_PAYLOAD)
            analysis_id = created.json()["id"]
            fetched = client.get(f"/api/analyses/{analysis_id}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == analysis_id
        assert fetched.json()["recommended_price"] == created.json()["recommended_price"]

    def test_missing_analysis_returns_404(self, tmp_path):
        missing = uuid4()
        with api_client(unique_tmp(tmp_path)) as client:
            response = client.get(f"/api/analyses/{missing}")
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "analysis_not_found"
        assert body["details"]["analysis_id"] == str(missing)

    def test_invalid_uuid_returns_422(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            response = client.get("/api/analyses/not-a-uuid")
        assert response.status_code == 422
        assert response.json()["error"] == "validation_error"


class TestDeleteAnalysis:
    def test_delete_own_analysis_returns_204(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            created = client.post("/api/analyses", json=CREATE_PAYLOAD)
            analysis_id = created.json()["id"]
            deleted = client.delete(f"/api/analyses/{analysis_id}")
            fetched = client.get(f"/api/analyses/{analysis_id}")
            listed = client.get("/api/analyses")
        assert deleted.status_code == 204
        assert fetched.status_code == 404
        assert listed.json()["total"] == 0

    def test_delete_missing_returns_404(self, tmp_path):
        missing = uuid4()
        with api_client(unique_tmp(tmp_path)) as client:
            response = client.delete(f"/api/analyses/{missing}")
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "analysis_not_found"
        assert body["details"]["analysis_id"] == str(missing)


class TestPersistenceAndCacheHit:
    def test_post_then_get_round_trip(self, tmp_path):
        with api_client(unique_tmp(tmp_path)) as client:
            created = client.post("/api/analyses", json=CREATE_PAYLOAD).json()
            loaded = client.get(f"/api/analyses/{created['id']}").json()
        assert loaded["id"] == created["id"]
        assert loaded["product_name"] == created["product_name"]
        assert loaded["cost"] == created["cost"]
        assert loaded["target_margin"] == created["target_margin"]
        assert loaded["recommended_price"] == created["recommended_price"]
        assert loaded["trace_tavily_query"] == created["trace_tavily_query"]
        assert loaded["trace_filtered_count"] == created["trace_filtered_count"]
        assert loaded["market_data"]["comparable_prices"] == created["market_data"]["comparable_prices"]
        assert loaded["market_warnings"] == created["market_warnings"]

    def test_cache_hit_is_runtime_only(self, tmp_path):
        market = FakeMarketResearch(_market(cache_hit=True))
        with api_client(unique_tmp(tmp_path), market=market) as client:
            created = client.post("/api/analyses", json=CREATE_PAYLOAD).json()
            loaded = client.get(f"/api/analyses/{created['id']}").json()
        assert created["market_data"]["cache_hit"] is True
        assert loaded["market_data"]["cache_hit"] is False
