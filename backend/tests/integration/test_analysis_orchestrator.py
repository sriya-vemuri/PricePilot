from __future__ import annotations

import inspect
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients.tavily import TavilyNotConfiguredError
from app.db.base import Base
from app.models.enums import (
    Category,
    DemandLevel,
    MarketTrend,
    PricingMode,
    RetrievalMode,
    Strategy,
)
from app.models.requests import CreateAnalysisRequest
from app.models.responses import AnalysisDetailResponse, MarketDataResponse, PricingInput, PricingResult
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.errors import DatabaseError
from app.repositories.schemas import AnalysisCreate
from app.services.analysis_orchestrator import AnalysisOrchestrator
from app.services.errors import PricingCalculationError
from app.services.market_research.models import (
    WARNING_INSUFFICIENT_MARKET_DATA,
    WARNING_STAGE3_LOW_TRUST,
    WARNING_TAVILY_UNAVAILABLE,
    MarketResearchResult,
)
from app.services.pricing.baseline import calc_baseline


PRODUCT = "Vitamin C Serum"
COMPARABLE = [135.0, 142.0, 150.0]


def _request(**overrides) -> CreateAnalysisRequest:
    payload = {
        "product_name": PRODUCT,
        "category": Category.ELECTRONICS,
        "cost": Decimal("100"),
        "target_margin": Decimal("30"),
        "target_market": "United States",
        "strategy": Strategy.BALANCED,
    }
    payload.update(overrides)
    return CreateAnalysisRequest(**payload)


def _market(**overrides) -> MarketResearchResult:
    prices = list(overrides.pop("comparable_prices", COMPARABLE))
    payload = {
        "pricing_mode": PricingMode.RETAIL,
        "competitor_price_1": prices[0] if len(prices) >= 3 else None,
        "competitor_price_2": prices[1] if len(prices) >= 3 else None,
        "competitor_price_3": prices[-1] if len(prices) >= 3 else None,
        "comparable_prices": prices,
        "filtered_range_low": prices[0] if prices else None,
        "filtered_range_high": prices[-1] if prices else None,
        "raw_prices_found": len(prices),
        "filtered_prices_count": len(prices),
        "outliers_removed": 0,
        "has_reliable_data": len(prices) >= 3,
        "retrieval_mode": RetrievalMode.PRIMARY,
        "market_trend": MarketTrend.GROWING,
        "demand_level": DemandLevel.HIGH,
        "summary": "Pricing: around $142.",
        "tavily_query": "Vitamin C Serum price US USD",
        "fetched_at": datetime.now(UTC),
        "data_trust": "high",
        "warnings": [],
        "cache_hit": False,
    }
    payload.update(overrides)
    if "filtered_prices_count" not in overrides:
        payload["filtered_prices_count"] = len(payload["comparable_prices"])
    return MarketResearchResult(**payload)


def _empty_market(**overrides) -> MarketResearchResult:
    defaults = {
        "competitor_price_1": None,
        "competitor_price_2": None,
        "competitor_price_3": None,
        "comparable_prices": [],
        "filtered_range_low": None,
        "filtered_range_high": None,
        "raw_prices_found": 0,
        "filtered_prices_count": 0,
        "outliers_removed": 0,
        "has_reliable_data": False,
        "retrieval_mode": RetrievalMode.EXHAUSTED,
        "market_trend": MarketTrend.STABLE,
        "demand_level": DemandLevel.MODERATE,
        "summary": "",
        "data_trust": "low",
        "warnings": [WARNING_INSUFFICIENT_MARKET_DATA],
    }
    defaults.update(overrides)
    return _market(**defaults)


class FakeMarketResearch:
    def __init__(self, result: MarketResearchResult | None = None, error: Exception | None = None) -> None:
        self.result = result if result is not None else _market()
        self.error = error
        self.calls: list[tuple[str, Category, str, float | None]] = []

    async def research(
        self,
        product_name: str,
        category: Category,
        target_market: str,
        baseline_price: float | None,
    ) -> MarketResearchResult:
        self.calls.append((product_name, category, target_market, baseline_price))
        if self.error is not None:
            raise self.error
        return self.result


class FakeAnalysisRepository:
    def __init__(self) -> None:
        self.saved: list[AnalysisCreate] = []
        self.error: Exception | None = None

    def save_analysis(self, payload: AnalysisCreate) -> AnalysisDetailResponse:
        if self.error is not None:
            raise self.error
        self.saved.append(payload)
        return _detail_from_create(payload)


def _detail_from_create(payload: AnalysisCreate) -> AnalysisDetailResponse:
    market = payload.market_data
    return AnalysisDetailResponse(
        id=uuid4(),
        created_at=datetime.now(UTC),
        product_name=payload.product_name,
        category=payload.category,
        cost=float(payload.cost),
        target_margin=float(payload.target_margin),
        target_market=payload.target_market,
        strategy=payload.strategy,
        pricing_mode=payload.pricing_mode,
        baseline_price=payload.baseline_price,
        recommended_price=payload.recommended_price,
        price_range_low=payload.price_range_low,
        price_range_high=payload.price_range_high,
        confidence_score=payload.confidence_score,
        confidence_explanation=payload.confidence_explanation,
        pricing_basis=payload.pricing_basis,
        recommendation_mode=payload.recommendation_mode,
        reasoning_summary=payload.reasoning_summary,
        demand_signal=payload.demand_signal,
        competitor_avg_price=payload.competitor_avg_price,
        competitor_avg_status=payload.competitor_avg_status,
        trace_tavily_query=payload.trace_tavily_query,
        trace_prices_found=payload.trace_prices_found,
        trace_filtered_low=payload.trace_filtered_low,
        trace_filtered_high=payload.trace_filtered_high,
        trace_filtered_count=payload.trace_filtered_count,
        trace_used_fallback=payload.trace_used_fallback,
        trace_market_trend=payload.trace_market_trend,
        trace_demand_level=payload.trace_demand_level,
        trace_competitor_avg_used=payload.trace_competitor_avg_used,
        price_variance=payload.price_variance,
        sanity_triggered=payload.sanity_triggered,
        baseline_status=payload.baseline_status,
        baseline_conflict=payload.baseline_conflict,
        baseline_conflict_reason=payload.baseline_conflict_reason,
        market_data=MarketDataResponse(
            tavily_query=market.tavily_query,
            fetched_at=market.fetched_at,
            cache_hit=False,
            market_trend=market.market_trend,
            demand_level=market.demand_level,
            summary=market.summary,
            competitor_price_1=market.competitor_price_1,
            competitor_price_2=market.competitor_price_2,
            competitor_price_3=market.competitor_price_3,
            comparable_prices=list(market.comparable_prices),
            filtered_range_low=market.filtered_range_low,
            filtered_range_high=market.filtered_range_high,
            raw_prices_found=market.raw_prices_found,
            filtered_prices_count=market.filtered_prices_count,
            outliers_removed=market.outliers_removed,
            has_reliable_data=market.has_reliable_data,
            retrieval_mode=market.retrieval_mode,
            pricing_mode=market.pricing_mode,
            data_trust=market.data_trust,
        ),
        market_warnings=list(market.warnings),
    )


def _orchestrator(
    market: FakeMarketResearch | None = None,
    repo: FakeAnalysisRepository | None = None,
) -> tuple[AnalysisOrchestrator, FakeMarketResearch, FakeAnalysisRepository]:
    research = market or FakeMarketResearch()
    store = repo or FakeAnalysisRepository()
    return AnalysisOrchestrator(research, store), research, store


@pytest.fixture
def sqlite_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.anyio
class TestSuccessfulAnalysis:
    async def test_reliable_analysis_saves_pricing_and_market_data(self):
        orchestrator, research, repo = _orchestrator()
        request = _request()
        result = await orchestrator.create_analysis(request, user_id="test-user-id")

        assert isinstance(result.id, UUID)
        assert result.product_name == PRODUCT
        assert result.pricing_mode == PricingMode.RETAIL
        assert result.baseline_price == pytest.approx(142.86)
        assert result.recommended_price > 0
        assert result.market_data.comparable_prices == COMPARABLE
        assert result.market_data.data_trust == "high"
        assert result.trace_tavily_query == "Vitamin C Serum price US USD"
        assert result.trace_prices_found == 3
        assert result.trace_filtered_count == 3
        assert result.trace_used_fallback is False
        assert result.trace_market_trend == MarketTrend.GROWING
        assert result.trace_demand_level == DemandLevel.HIGH
        assert result.trace_competitor_avg_used == result.competitor_avg_price
        assert len(repo.saved) == 1
        assert repo.saved[0].user_id == "test-user-id"
        assert repo.saved[0].market_data.comparable_prices == COMPARABLE
        assert research.calls[0][0] == PRODUCT


@pytest.mark.anyio
class TestBaselinePreview:
    async def test_market_research_receives_calc_baseline(self):
        orchestrator, research, _repo = _orchestrator()
        await orchestrator.create_analysis(
            _request(cost=Decimal("100"), target_margin=Decimal("30")),
            user_id="test-user-id",
        )
        expected = calc_baseline(Decimal("100"), Decimal("30"))
        assert expected == pytest.approx(142.86)
        assert research.calls[0][3] == pytest.approx(expected)

    async def test_zero_margin_baseline_equals_cost(self):
        orchestrator, research, _repo = _orchestrator()
        await orchestrator.create_analysis(
            _request(cost=Decimal("80"), target_margin=Decimal("0")),
            user_id="test-user-id",
        )
        assert research.calls[0][3] == pytest.approx(80.0)


@pytest.mark.anyio
class TestPricingInput:
    async def test_pricing_input_uses_market_comparables_not_filtered_count(self, monkeypatch):
        captured: list[PricingInput] = []
        original = __import__("app.services.pricing", fromlist=["generate_pricing"]).generate_pricing

        def capturing(pricing_input: PricingInput) -> PricingResult:
            captured.append(pricing_input)
            return original(pricing_input)

        monkeypatch.setattr("app.services.analysis_orchestrator.generate_pricing", capturing)

        market = _market(
            comparable_prices=COMPARABLE,
            filtered_prices_count=3,
            market_trend=MarketTrend.SURGING,
            demand_level=DemandLevel.VERY_HIGH,
            data_trust="medium",
            raw_prices_found=5,
        )
        orchestrator, _, _ = _orchestrator(FakeMarketResearch(market))
        await orchestrator.create_analysis(_request(), user_id="test-user-id")

        assert len(captured) == 1
        pricing_input = captured[0]
        assert pricing_input.comparable_prices == COMPARABLE
        assert pricing_input.market_trend == MarketTrend.SURGING
        assert pricing_input.demand_level == DemandLevel.VERY_HIGH
        assert pricing_input.data_trust == "medium"
        assert pricing_input.raw_prices_found == 5
        assert not hasattr(pricing_input, "filtered_prices_count") or "filtered_prices_count" not in pricing_input.model_fields
        dumped = pricing_input.model_dump()
        assert "filtered_prices_count" not in dumped
        assert "competitor_price_1" not in dumped
        assert "number_of_valid_prices" not in dumped


@pytest.mark.anyio
class TestDegradedMarket:
    async def test_no_market_fallback_still_saves(self):
        orchestrator, _, repo = _orchestrator(FakeMarketResearch(_empty_market()))
        result = await orchestrator.create_analysis(_request(), user_id="test-user-id")

        assert result.trace_used_fallback is True
        assert result.market_data.comparable_prices == []
        assert result.recommended_price == pytest.approx(result.baseline_price, abs=0.01)
        assert len(repo.saved) == 1
        assert WARNING_INSUFFICIENT_MARKET_DATA in result.market_warnings

    async def test_tavily_outage_still_creates_analysis(self):
        market = _empty_market(warnings=[WARNING_TAVILY_UNAVAILABLE, WARNING_INSUFFICIENT_MARKET_DATA])
        orchestrator, _, repo = _orchestrator(FakeMarketResearch(market))
        result = await orchestrator.create_analysis(_request(), user_id="test-user-id")

        assert WARNING_TAVILY_UNAVAILABLE in result.market_warnings
        assert result.market_data.comparable_prices == []
        assert result.recommended_price > 0
        assert len(repo.saved) == 1


@pytest.mark.anyio
class TestMissingTavilyConfig:
    async def test_missing_api_key_does_not_save(self):
        research = FakeMarketResearch(error=TavilyNotConfiguredError("missing"))
        orchestrator, _, repo = _orchestrator(research)
        with pytest.raises(TavilyNotConfiguredError):
            await orchestrator.create_analysis(_request(), user_id="test-user-id")
        assert repo.saved == []


@pytest.mark.anyio
class TestCacheHit:
    async def test_create_response_preserves_runtime_cache_hit(self):
        orchestrator, _, repo = _orchestrator(FakeMarketResearch(_market(cache_hit=True)))
        result = await orchestrator.create_analysis(_request(), user_id="test-user-id")
        assert result.market_data.cache_hit is True
        assert not hasattr(repo.saved[0].market_data, "cache_hit") or "cache_hit" not in repo.saved[0].market_data.model_fields
        assert "cache_hit" not in repo.saved[0].market_data.model_dump()
        assert "cache_key" not in repo.saved[0].market_data.model_dump()
        assert "candidate_prices" not in repo.saved[0].market_data.model_dump()

    async def test_live_research_returns_cache_hit_false(self):
        orchestrator, _, _ = _orchestrator(FakeMarketResearch(_market(cache_hit=False)))
        result = await orchestrator.create_analysis(_request(), user_id="test-user-id")
        assert result.market_data.cache_hit is False


@pytest.mark.anyio
class TestStage3:
    async def test_stage3_low_trust_is_passed_to_pricing_and_preserved(self, monkeypatch):
        captured: list[PricingInput] = []
        original = __import__("app.services.pricing", fromlist=["generate_pricing"]).generate_pricing

        def capturing(pricing_input: PricingInput) -> PricingResult:
            captured.append(pricing_input)
            return original(pricing_input)

        monkeypatch.setattr("app.services.analysis_orchestrator.generate_pricing", capturing)

        market = _market(
            retrieval_mode=RetrievalMode.STAGE3_SUCCESS,
            data_trust="low",
            warnings=[WARNING_STAGE3_LOW_TRUST],
        )
        orchestrator, _, _ = _orchestrator(FakeMarketResearch(market))
        result = await orchestrator.create_analysis(_request(), user_id="test-user-id")

        assert captured[0].data_trust == "low"
        assert WARNING_STAGE3_LOW_TRUST in result.market_warnings
        assert result.market_data.data_trust == "low"
        assert result.market_data.retrieval_mode == RetrievalMode.STAGE3_SUCCESS


@pytest.mark.anyio
class TestTraceMapping:
    async def test_trace_fields_match_market_and_pricing(self):
        market = _market(
            tavily_query="custom query",
            raw_prices_found=4,
            comparable_prices=COMPARABLE,
            filtered_prices_count=3,
            filtered_range_low=135.0,
            filtered_range_high=150.0,
            outliers_removed=1,
        )
        orchestrator, _, repo = _orchestrator(FakeMarketResearch(market))
        result = await orchestrator.create_analysis(_request(), user_id="test-user-id")
        saved = repo.saved[0]

        assert result.trace_tavily_query == "custom query"
        assert result.trace_prices_found == 4
        assert result.trace_filtered_low == pytest.approx(135.0)
        assert result.trace_filtered_high == pytest.approx(150.0)
        assert result.trace_filtered_count == 3
        assert result.trace_used_fallback is False
        assert result.trace_market_trend == market.market_trend
        assert result.trace_demand_level == market.demand_level
        assert result.trace_competitor_avg_used == result.competitor_avg_price
        assert saved.trace_filtered_count == market.filtered_prices_count
        assert saved.trace_used_fallback is (not market.has_reliable_data)


@pytest.mark.anyio
class TestPersistence:
    async def test_real_repository_saves_analysis_and_market_data(self, sqlite_session):
        repo = AnalysisRepository(sqlite_session)
        market = _market(cache_hit=True, warnings=[WARNING_STAGE3_LOW_TRUST])
        orchestrator = AnalysisOrchestrator(FakeMarketResearch(market), repo)

        created = await orchestrator.create_analysis(_request(), user_id="test-user-id")
        assert created.market_data.cache_hit is True
        assert WARNING_STAGE3_LOW_TRUST in created.market_warnings

        loaded = repo.get_by_id(created.id, "test-user-id")
        assert loaded is not None
        assert loaded.product_name == PRODUCT
        assert loaded.cost == pytest.approx(100)
        assert loaded.target_margin == pytest.approx(30)
        assert loaded.market_data.comparable_prices == COMPARABLE
        assert loaded.trace_filtered_count == 3
        assert loaded.market_warnings == [WARNING_STAGE3_LOW_TRUST]
        # cache_hit is runtime-only; GET reconstruction is always false.
        assert loaded.market_data.cache_hit is False


@pytest.mark.anyio
class TestFailures:
    async def test_database_error_propagates(self):
        repo = FakeAnalysisRepository()
        repo.error = DatabaseError("write failed")
        orchestrator, _, _ = _orchestrator(repo=repo)
        with pytest.raises(DatabaseError, match="write failed"):
            await orchestrator.create_analysis(_request(), user_id="test-user-id")

    async def test_pricing_failure_does_not_save(self, monkeypatch):
        def boom(_input: PricingInput):
            raise RuntimeError("engine exploded")

        monkeypatch.setattr("app.services.analysis_orchestrator.generate_pricing", boom)
        orchestrator, _, repo = _orchestrator()
        with pytest.raises(PricingCalculationError) as exc_info:
            await orchestrator.create_analysis(_request(), user_id="test-user-id")
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert repo.saved == []


class TestOrchestratorBoundaries:
    def test_does_not_import_tavily_or_filter(self):
        source = inspect.getsource(
            __import__("app.services.analysis_orchestrator", fromlist=["AnalysisOrchestrator"])
        )
        assert "TavilyClient" not in source
        assert "filter_comparable_prices" not in source
        assert "MarketCacheRepository" not in source
