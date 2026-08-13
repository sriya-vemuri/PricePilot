"""Coordinate one complete PricePilot analysis from request to persistence.

This is an application-layer use case. It does not own Tavily, caching,
price extraction/filtering, or pricing math. Those stay in MarketResearchService
and generate_pricing.

cache_hit is runtime-only metadata from MarketResearchService. It is copied onto
the immediate AnalysisDetailResponse.market_data.cache_hit so POST /api/analyses
can show a cache badge. It is not persisted. A later GET /api/analyses/{id}
reconstructs MarketData from the database and therefore returns cache_hit=false.
"""

from __future__ import annotations

from typing import Protocol

from app.core.categories import get_pricing_mode
from app.models.enums import Category, PricingMode
from app.models.requests import CreateAnalysisRequest
from app.models.responses import AnalysisDetailResponse, PricingInput, PricingResult
from app.repositories.schemas import AnalysisCreate, MarketDataCreate
from app.services.errors import PricingCalculationError
from app.services.market_research.models import MarketResearchResult
from app.services.pricing import generate_pricing
from app.services.pricing.baseline import calc_baseline


class MarketResearch(Protocol):
    async def research(
        self,
        product_name: str,
        category: Category,
        target_market: str,
        baseline_price: float | None,
    ) -> MarketResearchResult: ...


class AnalysisStore(Protocol):
    def save_analysis(self, payload: AnalysisCreate) -> AnalysisDetailResponse: ...


class AnalysisOrchestrator:
    """Create one analysis: baseline → market research → pricing → persist."""

    def __init__(self, market_research: MarketResearch, analysis_repo: AnalysisStore) -> None:
        self._market_research = market_research
        self._analysis_repo = analysis_repo

    async def create_analysis(self, request: CreateAnalysisRequest) -> AnalysisDetailResponse:
        pricing_mode = get_pricing_mode(request.category)
        baseline_price = calc_baseline(request.cost, request.target_margin)

        market = await self._market_research.research(
            request.product_name,
            request.category,
            request.target_market,
            baseline_price,
        )

        pricing_input = PricingInput(
            cost=request.cost,
            target_margin=request.target_margin,
            strategy=request.strategy,
            category=request.category,
            pricing_mode=pricing_mode,
            comparable_prices=list(market.comparable_prices),
            demand_level=market.demand_level,
            market_trend=market.market_trend,
            raw_prices_found=market.raw_prices_found,
            data_trust=market.data_trust,
        )
        try:
            pricing = generate_pricing(pricing_input)
        except Exception as exc:
            raise PricingCalculationError("Unexpected pricing-engine failure") from exc

        saved = self._analysis_repo.save_analysis(
            _to_analysis_create(request, pricing_mode, market, pricing)
        )
        # Runtime cache_hit is not stored. Override only the create response.
        return saved.model_copy(
            update={
                "market_data": saved.market_data.model_copy(update={"cache_hit": market.cache_hit}),
            }
        )


def _to_analysis_create(
    request: CreateAnalysisRequest,
    pricing_mode: PricingMode,
    market: MarketResearchResult,
    pricing: PricingResult,
) -> AnalysisCreate:
    return AnalysisCreate(
        product_name=request.product_name,
        category=request.category,
        cost=request.cost,
        target_margin=request.target_margin,
        target_market=request.target_market,
        strategy=request.strategy,
        pricing_mode=pricing_mode,
        baseline_price=pricing.baseline_price,
        recommended_price=pricing.recommended_price,
        price_range_low=pricing.price_range_low,
        price_range_high=pricing.price_range_high,
        confidence_score=pricing.confidence_score,
        confidence_explanation=pricing.confidence_explanation,
        pricing_basis=pricing.pricing_basis,
        recommendation_mode=pricing.recommendation_mode,
        reasoning_summary=pricing.reasoning_summary,
        demand_signal=market.demand_level,
        competitor_avg_price=pricing.competitor_avg_price,
        competitor_avg_status=pricing.competitor_avg_status,
        trace_tavily_query=market.tavily_query,
        trace_prices_found=market.raw_prices_found,
        trace_filtered_low=market.filtered_range_low,
        trace_filtered_high=market.filtered_range_high,
        trace_filtered_count=market.filtered_prices_count,
        trace_used_fallback=not market.has_reliable_data,
        trace_market_trend=market.market_trend,
        trace_demand_level=market.demand_level,
        trace_competitor_avg_used=pricing.competitor_avg_price,
        price_variance=pricing.price_variance,
        sanity_triggered=pricing.sanity_triggered,
        baseline_status=pricing.baseline_status,
        baseline_conflict=pricing.baseline_conflict,
        baseline_conflict_reason=pricing.baseline_conflict_reason,
        market_data=MarketDataCreate(
            fetched_at=market.fetched_at,
            summary=market.summary or None,
            tavily_query=market.tavily_query or None,
            market_trend=market.market_trend,
            demand_level=market.demand_level,
            pricing_mode=market.pricing_mode,
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
            data_trust=market.data_trust,
            warnings=list(market.warnings),
        ),
    )
