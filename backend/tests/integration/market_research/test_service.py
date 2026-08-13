from __future__ import annotations

from unittest.mock import patch
import inspect

import pytest

from app.clients.tavily import (
    TavilyHTTPError,
    TavilyNotConfiguredError,
    TavilySearchResult,
    TavilyTimeoutError,
)
from app.models.enums import Category, DemandLevel, MarketTrend, PricingMode, RetrievalMode
from app.services.market_research.models import (
    WARNING_DEMAND_UNAVAILABLE,
    WARNING_INSUFFICIENT_MARKET_DATA,
    WARNING_STAGE3_LOW_TRUST,
    WARNING_TAVILY_PARTIAL_FAILURE,
    WARNING_TAVILY_UNAVAILABLE,
    WARNING_TREND_UNAVAILABLE,
)
from app.services.market_research.query_builder import build_demand_query, build_trend_query
from app.services.market_research.service import MarketResearchService
from tests.integration.market_research.conftest import (
    FakeTavilyClient,
    build_default_signal_responses,
    demand_result,
    price_result,
    stage_query_texts,
    trend_result,
)

PRODUCT = "Vitamin C Serum"
TARGET_MARKET = "United States"
BASELINE = 30.0


def _service(handler) -> MarketResearchService:
    return MarketResearchService(FakeTavilyClient(handler))


def _stage_sets(category: Category, pricing_mode: PricingMode):
    stage1 = stage_query_texts(PRODUCT, category, TARGET_MARKET, pricing_mode, 1)
    stage2 = stage_query_texts(PRODUCT, category, TARGET_MARKET, pricing_mode, 2)
    stage3 = stage_query_texts(PRODUCT, category, TARGET_MARKET, pricing_mode, 3)
    signals = build_default_signal_responses(PRODUCT, category, TARGET_MARKET)
    return stage1, stage2, stage3, signals


@pytest.mark.anyio
class TestStage1Success:
    async def test_stage1_success_primary_high_reliable(self):
        stage1, stage2, stage3, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                return price_result(24.99, 26.0, 28.0, answer="Typical price around $26.")
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.retrieval_mode == RetrievalMode.PRIMARY
        assert result.data_trust == "high"
        assert result.has_reliable_data is True
        assert result.filtered_prices_count == 3
        assert result.competitor_price_1 == 24.99
        assert result.competitor_price_2 == 26.0
        assert result.competitor_price_3 == 28.0
        assert result.raw_prices_found == 3
        assert result.outliers_removed == 0

        called_queries = {query for query, _ in service._tavily.calls}
        assert not called_queries.intersection(stage2)
        assert not called_queries.intersection(stage3)


@pytest.mark.anyio
class TestStage2Success:
    async def test_stage2_merges_and_succeeds(self):
        stage1, stage2, stage3, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                return price_result(24.99, 26.0)
            if query == stage2[0]:
                return price_result(28.0)
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.retrieval_mode == RetrievalMode.STAGE2_SUCCESS
        assert result.data_trust == "medium"
        assert result.has_reliable_data is True
        assert result.filtered_prices_count == 3
        assert result.competitor_price_1 == 24.99
        assert result.competitor_price_3 == 28.0

        called_queries = {query for query, _ in service._tavily.calls}
        assert called_queries.intersection(stage2)
        assert not called_queries.intersection(stage3)


@pytest.mark.anyio
class TestStage3Success:
    async def test_stage3_low_trust_success(self):
        stage1, stage2, stage3, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                return price_result(24.99)
            if query == stage2[0]:
                return price_result(26.0)
            if query == stage3[0]:
                return price_result(28.0)
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.retrieval_mode == RetrievalMode.STAGE3_SUCCESS
        assert result.data_trust == "low"
        assert WARNING_STAGE3_LOW_TRUST in result.warnings
        assert result.has_reliable_data is True
        assert result.filtered_prices_count == 3


@pytest.mark.anyio
class TestExhausted:
    async def test_exhausted_insufficient_data(self):
        stage1, stage2, stage3, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query in {stage1[0], stage2[0], stage3[0]}:
                return price_result(24.99, 26.0)
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.retrieval_mode == RetrievalMode.EXHAUSTED
        assert result.has_reliable_data is False
        assert WARNING_INSUFFICIENT_MARKET_DATA in result.warnings
        assert result.competitor_price_1 is None
        assert result.competitor_price_2 is None
        assert result.competitor_price_3 is None
        assert result.filtered_prices_count == 2


@pytest.mark.anyio
class TestDuplicateEvidence:
    async def test_duplicate_prices_deduplicated(self):
        stage1, _, _, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query in stage1:
                return price_result(29.99)
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.raw_prices_found == 1
        assert result.filtered_prices_count == 1
        assert result.comparable_prices == [29.99]


@pytest.mark.anyio
class TestPartialFailures:
    async def test_partial_pricing_failure_continues(self):
        stage1, _, _, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                raise TavilyTimeoutError("timeout")
            if query == stage1[1]:
                return price_result(24.99, 26.0, 28.0)
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.has_reliable_data is True
        assert WARNING_TAVILY_PARTIAL_FAILURE in result.warnings

    async def test_trend_failure_defaults_stable(self):
        stage1, _, _, _ = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)
        trend = build_trend_query(PRODUCT, Category.ELECTRONICS, TARGET_MARKET)
        demand = build_demand_query(PRODUCT, Category.ELECTRONICS, TARGET_MARKET)

        def handler(query: str, _domains):
            if query == trend.text:
                raise TavilyHTTPError("bad gateway", status_code=502, retryable=True)
            if query == demand.text:
                return demand_result()
            if query == stage1[0]:
                return price_result(24.99, 26.0, 28.0)
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.market_trend == MarketTrend.STABLE
        assert WARNING_TREND_UNAVAILABLE in result.warnings

    async def test_demand_failure_defaults_moderate(self):
        stage1, _, _, _ = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)
        trend = build_trend_query(PRODUCT, Category.ELECTRONICS, TARGET_MARKET)
        demand = build_demand_query(PRODUCT, Category.ELECTRONICS, TARGET_MARKET)

        def handler(query: str, _domains):
            if query == demand.text:
                raise TavilyHTTPError("bad gateway", status_code=503, retryable=True)
            if query == trend.text:
                return trend_result()
            if query == stage1[0]:
                return price_result(24.99, 26.0, 28.0)
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.demand_level == DemandLevel.MODERATE
        assert WARNING_DEMAND_UNAVAILABLE in result.warnings


@pytest.mark.anyio
class TestCompleteOutage:
    async def test_complete_transient_outage_returns_degraded_result(self):
        def handler(_query: str, _domains):
            raise TavilyTimeoutError("timeout")

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.comparable_prices == []
        assert result.filtered_prices_count == 0
        assert result.has_reliable_data is False
        assert result.market_trend == MarketTrend.STABLE
        assert result.demand_level == DemandLevel.MODERATE
        assert result.data_trust == "low"
        assert WARNING_TAVILY_UNAVAILABLE in result.warnings
        assert WARNING_INSUFFICIENT_MARKET_DATA in result.warnings


@pytest.mark.anyio
class TestMissingApiKey:
    async def test_not_configured_propagates(self):
        def handler(_query: str, _domains):
            raise TavilyNotConfiguredError("missing")

        service = _service(handler)
        with pytest.raises(TavilyNotConfiguredError):
            await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)


@pytest.mark.anyio
class TestTargetMarketAndDomains:
    async def test_target_market_in_queries(self):
        target = "United Kingdom"
        stage1_uk = stage_query_texts(PRODUCT, Category.ELECTRONICS, target, PricingMode.RETAIL, 1)
        signals_uk = build_default_signal_responses(PRODUCT, Category.ELECTRONICS, target)

        def handler_uk(query: str, _domains):
            if query in signals_uk:
                return signals_uk[query]
            if query == stage1_uk[0]:
                return price_result(24.99, 26.0, 28.0)
            return TavilySearchResult()

        service = _service(handler_uk)
        await service.research(PRODUCT, Category.ELECTRONICS, target, BASELINE)
        joined = " ".join(query for query, _ in service._tavily.calls)
        assert "United Kingdom" in joined or "UK" in joined
        assert "United States" not in joined

    async def test_retail_pricing_uses_domains_signal_queries_do_not(self):
        stage1, _, _, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                return price_result(24.99, 26.0, 28.0)
            return TavilySearchResult()

        service = _service(handler)
        await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        pricing_calls = [
            (query, domains)
            for query, domains in service._tavily.calls
            if query not in signals
        ]
        assert pricing_calls
        assert all(domains for _, domains in pricing_calls)

        trend = build_trend_query(PRODUCT, Category.ELECTRONICS, TARGET_MARKET)
        demand = build_demand_query(PRODUCT, Category.ELECTRONICS, TARGET_MARKET)
        signal_domains = [
            domains
            for query, domains in service._tavily.calls
            if query in {trend.text, demand.text}
        ]
        assert signal_domains == [None, None]

    async def test_service_pricing_has_no_retailer_domains(self):
        stage1, _, _, signals = _stage_sets(Category.SERVICES, PricingMode.SERVICE)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                return price_result(120.0, 150.0, 180.0)
            return TavilySearchResult()

        service = _service(handler)
        await service.research(PRODUCT, Category.SERVICES, TARGET_MARKET, BASELINE)

        pricing_calls = [
            domains for query, domains in service._tavily.calls if query not in signals
        ]
        assert pricing_calls
        assert all(domains is None for domains in pricing_calls)


@pytest.mark.anyio
class TestCountsAndFiltering:
    async def test_count_fields_are_consistent(self):
        stage1, _, _, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                return price_result(24.99, 26.0, 28.0)
            return TavilySearchResult()

        service = _service(handler)
        result = await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)

        assert result.filtered_prices_count == len(result.comparable_prices)
        assert result.outliers_removed == max(0, result.raw_prices_found - result.filtered_prices_count)

    async def test_filtering_happens_only_in_filter_layer(self):
        stage1, _, _, signals = _stage_sets(Category.ELECTRONICS, PricingMode.RETAIL)

        def handler(query: str, _domains):
            if query in signals:
                return signals[query]
            if query == stage1[0]:
                return price_result(24.99, 26.0, 28.0)
            return TavilySearchResult()

        with patch(
            "app.services.market_research.service.filter_comparable_prices",
            wraps=__import__(
                "app.services.market_research.price_filter",
                fromlist=["filter_comparable_prices"],
            ).filter_comparable_prices,
        ) as filter_mock:
            service = _service(handler)
            await service.research(PRODUCT, Category.ELECTRONICS, TARGET_MARKET, BASELINE)
            assert filter_mock.call_count >= 1

        service_source = inspect.getsource(MarketResearchService)
        assert "iqr" not in service_source.lower()
        assert "percentile(" not in service_source
