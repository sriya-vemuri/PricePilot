from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_analysis_orchestrator, get_market_research_service
from app.auth import AuthenticatedUser, get_current_user
from app.config import Settings
from app.db.base import Base
from app.main import create_app
from tests.integration.test_analysis_orchestrator import FakeMarketResearch, _market

SECRET_TAVILY_KEY = "test-secret-tavily-key-do-not-leak"
TEST_AUTH_USER = AuthenticatedUser(user_id="test-user-id", role="authenticated")
TEST_SUPABASE_URL = "https://example.supabase.co"

CREATE_PAYLOAD = {
    "product_name": "Vitamin C Serum",
    "category": "electronics",
    "cost": 100,
    "target_margin": 30,
    "target_market": "United States",
    "strategy": "balanced",
}


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'api-test.db'}",
        tavily_api_key=SECRET_TAVILY_KEY,
        cors_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        supabase_url=TEST_SUPABASE_URL,
    )


@contextmanager
def api_client(
    tmp_path: Path,
    *,
    market: FakeMarketResearch | None = None,
    orchestrator: object | None = None,
    authenticate: bool = True,
) -> Iterator[TestClient]:
    application = create_app(_settings(tmp_path))
    if authenticate:
        application.dependency_overrides[get_current_user] = lambda: TEST_AUTH_USER
    if orchestrator is not None:
        application.dependency_overrides[get_analysis_orchestrator] = lambda: orchestrator
    else:
        fake = market if market is not None else FakeMarketResearch(_market())
        application.dependency_overrides[get_market_research_service] = lambda: fake
    with TestClient(application) as client:
        Base.metadata.create_all(application.state.engine)
        yield client
    application.dependency_overrides.clear()


def unique_tmp(tmp_path: Path) -> Path:
    path = tmp_path / uuid4().hex
    path.mkdir()
    return path
