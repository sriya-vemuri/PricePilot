from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.clients.tavily import TavilyNotConfiguredError, TavilySearchResult, TavilyTimeoutError
from app.config import Settings
from app.models.enums import Category, DemandLevel, MarketTrend, PricingMode, RetrievalMode
from app.repositories.errors import DatabaseError
from app.repositories.schemas import MarketCacheRecord, MarketCacheUpsert
from app.services.market_research.cache_key import build_cache_key
from app.services.market_research.models import (
    WARNING_INSUFFICIENT_MARKET_DATA,
    WARNING_STAGE3_LOW_TRUST,
    WARNING_TAVILY_PARTIAL_FAILURE,
    WARNING_TAVILY_UNAVAILABLE,
)
from app.services.market_research.service import MarketResearchService
from tests.integration.market_research.conftest import (
    FakeTavilyClient,
    build_default_signal_responses,
    price_result,
    stage_query_texts,
)

PRODUCT = "Vitamin C Serum"
TARGET_MARKET = "United States"
BASELINE = 30.0


class FakeMarketCache:
    def __init__(self) -> None:
        self.records: dict[str, MarketCacheRecord] = {}
        self.upserts: list[MarketCacheUpsert] = []
        self.get_fresh_calls: list[str] = []
        self.get_error: Exception | None = None
        self.upsert_error: Exception | None = None

    def get_fresh(self, cache_key: str, now: datetime | None = None) -> MarketCacheRecord | None:
        if self.get_error is not None:
            raise self.get_error
        self.get_fresh_calls.append(cache_key)
        record = self.records.get(cache_key)
        if record is None:
            return None
        current = now or datetime.now(UTC)
        if record.expires_at <= current:
            return None
        return record

    def upsert(self, payload: MarketCacheUpsert) -> MarketCacheRecord:
        if self.upsert_error is not None:
            raise self.upsert_error
        self.upserts.append(payload)
        record = MarketCacheRecord(
            id=uuid4(),
            created_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        self.records[payload.cache_key] = record
        return record


def _settings(**overrides) -> Settings:
    defaults = {
        "market_cache_reliable_ttl_seconds": 86400,
        "market_cache_low_quality_ttl_seconds": 900,
        "supabase_url": "https://example.supabase.co",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _service(handler, cache: FakeMarketCache | None = None) -> MarketResearchService:
    return MarketResearchService(
        FakeTavilyClient(handler),
        cache_repo=cache,
        settings=_settings(),
    )


def _live_handler(prices: tuple[float, ...] = (24.99, 26.0, 28.0)):
    stage1, _, _, signals = (
        stage_query_texts(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, PricingMode.RETAIL, 1),
        None,
        None,
        build_default_signal_responses(PRODUCT, Category.ELECTRONICS, TARGET_MARKET),
    )

    def handler(query: str, _domains):
        if query in signals:
            return signals[query]
        if query == stage1[0]:
            return price_result(*prices, answer="Typical price around $26.")
        return TavilySearchResult()

    return handler, stage1, signals


def _cached_record(**overrides) -> MarketCacheRecord:
    now = datetime.now(UTC)
    payload = {
        "id": uuid4(),
        "cache_key": build_cache_key(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, PricingMode.RETAIL),
        "created_at": now,
        "expires_at": now + timedelta(hours=24),
        "product_name": PRODUCT,
        "category": Category.ELECTRONICS,
        "target_market": TARGET_MARKET,
        "pricing_mode": PricingMode.RETAIL,
        "candidate_prices": [24.99, 26.0, 28.0],
        "competitor_price_1": 24.99,
        "competitor_price_2": 26.0,
        "competitor_price_3": 28.0,
        "comparable_prices": [24.99, 26.0, 28.0],
        "filtered_range_low": 24.99,
        "filtered_range_high": 28.0,
        "raw_prices_found": 3,
        "filtered_prices_count": 3,
        "outliers_removed": 0,
        "has_reliable_data": True,
        "retrieval_mode": RetrievalMode.PRIMARY,
        "market_trend": MarketTrend.GROWING,
        "demand_level": DemandLevel.HIGH,
        "summary": "Pricing: around $26.",
        "tavily_query": "Vitamin C Serum price US USD",
        "fetched_at": now,
        "data_trust": "high",
        "warnings": [],
    }
    payload.update(overrides)
    return MarketCacheRecord(**payload)


@pytest.mark.anyio
class TestCacheMissAndWrite:
    async def test_cache_miss_runs_tavily_and_upserts(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        service = _service(handler, cache)

        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.cache_hit is False
        assert service._tavily.calls
        assert len(cache.upserts) == 1
        assert cache.upserts[0].candidate_prices == [24.99, 26.0, 28.0]
        assert cache.upserts[0].cache_key == build_cache_key(
            PRODUCT, Category.ELECTRONICS, TARGET_MARKET, PricingMode.RETAIL
        )

    async def test_live_research_caches_pre_filter_candidate_prices(self):
        stage1 = stage_query_texts(PRODUCT, Category.CLOTHING, TARGET_MARKET, PricingMode.RETAIL, 1)
        signals = build_default_signal_responses(PRODUCT, Category.CLOTHING, TARGET_MARKET)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                return price_result(80.0, 90.0, 100.0, 200.0)
            return TavilySearchResult()

        cache = FakeMarketCache()
        service = _service(handler, cache)
        result = await service.research(PRODUCT, Category.CLOTHING, TARGET_MARKET, 30.0)

        assert result.cache_hit is False
        assert 200.0 not in result.comparable_prices
        assert cache.upserts[0].candidate_prices == [80.0, 90.0, 100.0, 200.0]


@pytest.mark.anyio
class TestCacheHit:
    async def test_fresh_cache_skips_tavily(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        record = _cached_record()
        cache.records[record.cache_key] = record
        service = _service(handler, cache)

        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.cache_hit is True
        assert service._tavily.calls == []
        assert cache.upserts == []
        assert result.comparable_prices == [24.99, 26.0, 28.0]
        assert result.market_trend == MarketTrend.GROWING


@pytest.mark.anyio
class TestDifferentBaselines:
    async def test_cache_hit_refilters_candidate_prices(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        record = _cached_record(
            category=Category.CLOTHING,
            cache_key=build_cache_key(PRODUCT, Category.CLOTHING, TARGET_MARKET, PricingMode.RETAIL),
            candidate_prices=[80.0, 90.0, 100.0, 200.0],
            comparable_prices=[80.0, 90.0, 100.0],
        )
        cache.records[record.cache_key] = record
        service = _service(handler, cache)

        tight = await service.research(PRODUCT, Category.CLOTHING, TARGET_MARKET, 30.0)
        wide = await service.research(PRODUCT, Category.CLOTHING, TARGET_MARKET, 100.0)

        assert tight.cache_hit is True
        assert wide.cache_hit is True
        assert service._tavily.calls == []
        assert 200.0 not in tight.comparable_prices
        assert 200.0 in wide.comparable_prices
        assert tight.filtered_prices_count == len(tight.comparable_prices)
        assert wide.filtered_prices_count == len(wide.comparable_prices)
        assert tight.outliers_removed >= 0
        assert wide.competitor_price_1 == wide.comparable_prices[0]
        assert wide.competitor_price_3 == wide.comparable_prices[-1]


@pytest.mark.anyio
class TestTtl:
    async def test_reliable_research_uses_reliable_ttl(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        service = _service(handler, cache)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)
        assert result.has_reliable_data is True
        ttl = (cache.upserts[0].expires_at - cache.upserts[0].fetched_at).total_seconds()
        assert ttl == pytest.approx(86400)

    async def test_low_quality_research_uses_short_ttl(self):
        handler, _, _ = _live_handler(prices=(24.99,))
        cache = FakeMarketCache()
        service = _service(handler, cache)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)
        assert result.has_reliable_data is False
        ttl = (cache.upserts[0].expires_at - cache.upserts[0].fetched_at).total_seconds()
        assert ttl == pytest.approx(900)


@pytest.mark.anyio
class TestTransportAndConfig:
    async def test_complete_outage_is_not_cached(self):
        def handler(_query: str, _domains):
            raise TavilyTimeoutError("timeout")

        cache = FakeMarketCache()
        service = _service(handler, cache)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.cache_hit is False
        assert WARNING_TAVILY_UNAVAILABLE in result.warnings
        assert cache.upserts == []

    async def test_missing_api_key_does_not_write_cache(self):
        def handler(_query: str, _domains):
            raise TavilyNotConfiguredError("missing")

        cache = FakeMarketCache()
        service = _service(handler, cache)
        with pytest.raises(TavilyNotConfiguredError):
            await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)
        assert cache.upserts == []

    async def test_successful_zero_prices_are_cached_with_short_ttl(self):
        stage1, _, _, signals = (
            stage_query_texts(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, PricingMode.RETAIL, 1),
            None,
            None,
            build_default_signal_responses(PRODUCT, Category.ELECTRONICS, TARGET_MARKET),
        )

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            return TavilySearchResult(answer="No prices found.")

        cache = FakeMarketCache()
        service = _service(handler, cache)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.has_reliable_data is False
        assert result.filtered_prices_count == 0
        assert len(cache.upserts) == 1
        ttl = (cache.upserts[0].expires_at - cache.upserts[0].fetched_at).total_seconds()
        assert ttl == pytest.approx(900)
        _ = stage1


@pytest.mark.anyio
class TestCacheErrors:
    async def test_cache_read_error_falls_back_to_tavily(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        cache.get_error = DatabaseError("cache down")
        service = _service(handler, cache)

        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.cache_hit is False
        assert result.has_reliable_data is True
        assert service._tavily.calls

    async def test_cache_write_error_still_returns_research(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        cache.upsert_error = DatabaseError("write failed")
        service = _service(handler, cache)

        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.cache_hit is False
        assert result.has_reliable_data is True
        assert WARNING_TAVILY_UNAVAILABLE not in result.warnings


@pytest.mark.anyio
class TestExpiredCacheAndKeys:
    async def test_expired_cache_runs_tavily(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        expired = _cached_record(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        cache.records[expired.cache_key] = expired
        service = _service(handler, cache)

        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.cache_hit is False
        assert service._tavily.calls
        assert len(cache.upserts) == 1

    async def test_same_normalized_inputs_share_cache_key(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        record = _cached_record(
            cache_key=build_cache_key("vitamin c serum", Category.ELECTRONICS, "united states", PricingMode.RETAIL)
        )
        cache.records[record.cache_key] = record
        service = _service(handler, cache)

        result = await service.research("  Vitamin   C Serum ", Category.ELECTRONICS, " United States ", BASELINE)
        assert result.cache_hit is True
        assert service._tavily.calls == []

    async def test_different_target_market_does_not_reuse_cache(self):
        handler, _, _ = _live_handler()
        cache = FakeMarketCache()
        us_key = build_cache_key(PRODUCT, Category.ELECTRONICS, "United States", PricingMode.RETAIL)
        cache.records[us_key] = _cached_record(cache_key=us_key)
        service = _service(handler, cache)

        uk_stage1 = stage_query_texts(PRODUCT, Category.ELECTRONICS, "United Kingdom", PricingMode.RETAIL, 1)
        uk_signals = build_default_signal_responses(PRODUCT, Category.ELECTRONICS, "United Kingdom")

        def uk_handler(query: str, _domains):
            if query in uk_signals:
                return uk_signals[query]
            if query == uk_stage1[0]:
                return price_result(24.99, 26.0, 28.0)
            return TavilySearchResult()

        uk_service = MarketResearchService(
            FakeTavilyClient(uk_handler),
            cache_repo=cache,
            settings=_settings(),
        )
        result = await uk_service.research(PRODUCT, Category.ELECTRONICS, "United Kingdom", BASELINE)
        assert result.cache_hit is False
        assert uk_service._tavily.calls
        _ = handler


@pytest.mark.anyio
class TestCacheHitCountsAndWarnings:
    async def test_cache_hit_counts_and_competitor_triple(self):
        cache = FakeMarketCache()
        record = _cached_record()
        cache.records[record.cache_key] = record
        service = _service(lambda q, d: TavilySearchResult(), cache)

        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)
        assert result.filtered_prices_count == len(result.comparable_prices)
        assert result.outliers_removed >= 0
        assert result.competitor_price_1 == 24.99
        assert result.competitor_price_2 == 26.0
        assert result.competitor_price_3 == 28.0
        assert WARNING_TAVILY_PARTIAL_FAILURE not in result.warnings

    async def test_stage3_warning_preserved_and_cache_hit_is_not_a_warning(self):
        cache = FakeMarketCache()
        record = _cached_record(
            retrieval_mode=RetrievalMode.STAGE3_SUCCESS,
            data_trust="low",
            warnings=[WARNING_STAGE3_LOW_TRUST, WARNING_TAVILY_PARTIAL_FAILURE],
        )
        cache.records[record.cache_key] = record
        service = _service(lambda q, d: TavilySearchResult(), cache)

        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)
        assert result.cache_hit is True
        assert WARNING_STAGE3_LOW_TRUST in result.warnings
        assert WARNING_TAVILY_PARTIAL_FAILURE not in result.warnings
        assert result.warnings.count(WARNING_STAGE3_LOW_TRUST) == 1
        assert "cache" not in " ".join(result.warnings).lower()

    async def test_insufficient_data_warning_follows_refilter(self):
        cache = FakeMarketCache()
        record = _cached_record(
            category=Category.CLOTHING,
            cache_key=build_cache_key(PRODUCT, Category.CLOTHING, TARGET_MARKET, PricingMode.RETAIL),
            candidate_prices=[80.0, 90.0],
            comparable_prices=[80.0, 90.0],
            warnings=[WARNING_INSUFFICIENT_MARKET_DATA],
            has_reliable_data=False,
        )
        cache.records[record.cache_key] = record
        service = _service(lambda q, d: TavilySearchResult(), cache)

        result = await service.research(PRODUCT, Category.CLOTHING, TARGET_MARKET, 30.0)
        assert result.has_reliable_data is False
        assert WARNING_INSUFFICIENT_MARKET_DATA in result.warnings
        assert result.warnings.count(WARNING_INSUFFICIENT_MARKET_DATA) == 1
