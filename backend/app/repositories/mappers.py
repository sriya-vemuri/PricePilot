from app.db.tables import Analysis, MarketCache, MarketData
from app.db.types import money_to_float
from app.models.enums import (
    BaselineStatus,
    Category,
    CompetitorAvgStatus,
    DemandLevel,
    MarketTrend,
    PricingBasis,
    PricingMode,
    RecommendationMode,
    RetrievalMode,
    Strategy,
)
from app.models.responses import (
    AnalysisDetailResponse,
    AnalysisSummaryResponse,
    MarketDataResponse,
    MarketDataSummary,
)
from app.repositories.schemas import AnalysisCreate, MarketCacheRecord, MarketCacheUpsert, MarketDataCreate


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def analysis_from_create(payload: AnalysisCreate) -> Analysis:
    market = payload.market_data
    analysis = Analysis(
        user_id=payload.user_id,
        product_name=payload.product_name,
        category=_enum_value(payload.category),
        cost=payload.cost,
        target_margin=payload.target_margin,
        target_market=payload.target_market,
        strategy=_enum_value(payload.strategy),
        pricing_mode=_enum_value(payload.pricing_mode),
        baseline_price=payload.baseline_price,
        recommended_price=payload.recommended_price,
        price_range_low=payload.price_range_low,
        price_range_high=payload.price_range_high,
        confidence_score=payload.confidence_score,
        confidence_explanation=payload.confidence_explanation,
        pricing_basis=_enum_value(payload.pricing_basis),
        recommendation_mode=_enum_value(payload.recommendation_mode),
        reasoning_summary=payload.reasoning_summary,
        demand_signal=_enum_value(payload.demand_signal),
        competitor_avg_price=payload.competitor_avg_price,
        competitor_avg_status=_enum_value(payload.competitor_avg_status),
        trace_tavily_query=payload.trace_tavily_query,
        trace_prices_found=payload.trace_prices_found,
        trace_filtered_low=payload.trace_filtered_low,
        trace_filtered_high=payload.trace_filtered_high,
        trace_filtered_count=payload.trace_filtered_count,
        trace_used_fallback=payload.trace_used_fallback,
        trace_market_trend=_enum_value(payload.trace_market_trend),
        trace_demand_level=_enum_value(payload.trace_demand_level),
        trace_competitor_avg_used=payload.trace_competitor_avg_used,
        price_variance=payload.price_variance,
        sanity_triggered=payload.sanity_triggered,
        baseline_status=_enum_value(payload.baseline_status),
        baseline_conflict=payload.baseline_conflict,
        baseline_conflict_reason=payload.baseline_conflict_reason,
        market_data=market_data_from_create(market),
    )
    return analysis


def market_data_from_create(payload: MarketDataCreate) -> MarketData:
    return MarketData(
        fetched_at=payload.fetched_at,
        summary=payload.summary,
        tavily_query=payload.tavily_query,
        market_trend=_enum_value(payload.market_trend),
        demand_level=_enum_value(payload.demand_level),
        pricing_mode=_enum_value(payload.pricing_mode),
        competitor_price_1=payload.competitor_price_1,
        competitor_price_2=payload.competitor_price_2,
        competitor_price_3=payload.competitor_price_3,
        comparable_prices=list(payload.comparable_prices),
        filtered_range_low=payload.filtered_range_low,
        filtered_range_high=payload.filtered_range_high,
        raw_prices_found=payload.raw_prices_found,
        filtered_prices_count=payload.filtered_prices_count,
        outliers_removed=payload.outliers_removed,
        has_reliable_data=payload.has_reliable_data,
        retrieval_mode=_enum_value(payload.retrieval_mode),
        data_trust=payload.data_trust,
        warnings=list(payload.warnings),
    )


def to_market_data_response(row: MarketData, *, cache_hit: bool = False) -> MarketDataResponse:
    return MarketDataResponse(
        tavily_query=row.tavily_query,
        fetched_at=row.fetched_at,
        cache_hit=cache_hit,
        market_trend=MarketTrend(row.market_trend),
        demand_level=DemandLevel(row.demand_level),
        summary=row.summary,
        competitor_price_1=money_to_float(row.competitor_price_1),
        competitor_price_2=money_to_float(row.competitor_price_2),
        competitor_price_3=money_to_float(row.competitor_price_3),
        comparable_prices=[float(price) for price in (row.comparable_prices or [])],
        filtered_range_low=money_to_float(row.filtered_range_low),
        filtered_range_high=money_to_float(row.filtered_range_high),
        raw_prices_found=row.raw_prices_found,
        filtered_prices_count=row.filtered_prices_count,
        outliers_removed=row.outliers_removed,
        has_reliable_data=row.has_reliable_data,
        retrieval_mode=RetrievalMode(row.retrieval_mode),
        pricing_mode=PricingMode(row.pricing_mode),
        data_trust=row.data_trust,  # type: ignore[arg-type]
    )


def to_market_data_summary(row: MarketData) -> MarketDataSummary:
    return MarketDataSummary(
        tavily_query=row.tavily_query,
        market_trend=MarketTrend(row.market_trend),
        demand_level=DemandLevel(row.demand_level),
        competitor_price_1=money_to_float(row.competitor_price_1),
        competitor_price_2=money_to_float(row.competitor_price_2),
        competitor_price_3=money_to_float(row.competitor_price_3),
        has_reliable_data=bool(row.has_reliable_data),
    )


def to_analysis_detail(row: Analysis) -> AnalysisDetailResponse:
    market = row.market_data
    return AnalysisDetailResponse(
        id=row.id,
        created_at=row.created_at,
        product_name=row.product_name,
        category=Category(row.category),
        cost=float(row.cost),
        target_margin=float(row.target_margin),
        target_market=row.target_market,
        strategy=Strategy(row.strategy),
        pricing_mode=PricingMode(row.pricing_mode),
        baseline_price=float(row.baseline_price),
        recommended_price=float(row.recommended_price),
        price_range_low=float(row.price_range_low),
        price_range_high=float(row.price_range_high),
        confidence_score=row.confidence_score,
        confidence_explanation=row.confidence_explanation,
        pricing_basis=PricingBasis(row.pricing_basis),
        recommendation_mode=RecommendationMode(row.recommendation_mode),
        reasoning_summary=row.reasoning_summary,
        demand_signal=DemandLevel(row.demand_signal),
        competitor_avg_price=money_to_float(row.competitor_avg_price),
        competitor_avg_status=CompetitorAvgStatus(row.competitor_avg_status),
        trace_tavily_query=row.trace_tavily_query,
        trace_prices_found=row.trace_prices_found,
        trace_filtered_low=money_to_float(row.trace_filtered_low),
        trace_filtered_high=money_to_float(row.trace_filtered_high),
        trace_filtered_count=row.trace_filtered_count,
        trace_used_fallback=row.trace_used_fallback,
        trace_market_trend=MarketTrend(row.trace_market_trend),
        trace_demand_level=DemandLevel(row.trace_demand_level),
        trace_competitor_avg_used=money_to_float(row.trace_competitor_avg_used),
        price_variance=row.price_variance,
        sanity_triggered=row.sanity_triggered,
        baseline_status=BaselineStatus(row.baseline_status),
        baseline_conflict=row.baseline_conflict,
        baseline_conflict_reason=row.baseline_conflict_reason,
        market_data=to_market_data_response(market),
        market_warnings=list(market.warnings or []),
    )


def to_analysis_summary(row: Analysis) -> AnalysisSummaryResponse:
    return AnalysisSummaryResponse(
        id=row.id,
        created_at=row.created_at,
        product_name=row.product_name,
        category=Category(row.category),
        strategy=Strategy(row.strategy),
        baseline_price=float(row.baseline_price),
        recommended_price=float(row.recommended_price),
        competitor_avg_price=money_to_float(row.competitor_avg_price),
        confidence_score=row.confidence_score,
        demand_signal=DemandLevel(row.demand_signal),
        market_data=to_market_data_summary(row.market_data),
    )


def apply_cache_upsert(row: MarketCache, payload: MarketCacheUpsert) -> None:
    row.expires_at = payload.expires_at
    row.product_name = payload.product_name
    row.category = _enum_value(payload.category)
    row.target_market = payload.target_market
    row.pricing_mode = _enum_value(payload.pricing_mode)
    row.candidate_prices = list(payload.candidate_prices)
    row.competitor_price_1 = payload.competitor_price_1
    row.competitor_price_2 = payload.competitor_price_2
    row.competitor_price_3 = payload.competitor_price_3
    row.comparable_prices = list(payload.comparable_prices)
    row.filtered_range_low = payload.filtered_range_low
    row.filtered_range_high = payload.filtered_range_high
    row.raw_prices_found = payload.raw_prices_found
    row.filtered_prices_count = payload.filtered_prices_count
    row.outliers_removed = payload.outliers_removed
    row.has_reliable_data = payload.has_reliable_data
    row.retrieval_mode = _enum_value(payload.retrieval_mode)
    row.market_trend = _enum_value(payload.market_trend)
    row.demand_level = _enum_value(payload.demand_level)
    row.summary = payload.summary
    row.tavily_query = payload.tavily_query
    row.fetched_at = payload.fetched_at
    row.data_trust = payload.data_trust
    row.warnings = list(payload.warnings)


def cache_from_upsert(payload: MarketCacheUpsert) -> MarketCache:
    row = MarketCache(cache_key=payload.cache_key)
    apply_cache_upsert(row, payload)
    return row


def to_cache_record(row: MarketCache) -> MarketCacheRecord:
    return MarketCacheRecord(
        id=row.id,
        cache_key=row.cache_key,
        created_at=row.created_at,
        expires_at=row.expires_at,
        product_name=row.product_name,
        category=Category(row.category),
        target_market=row.target_market,
        pricing_mode=PricingMode(row.pricing_mode),
        candidate_prices=[float(price) for price in (row.candidate_prices or [])],
        competitor_price_1=money_to_float(row.competitor_price_1),
        competitor_price_2=money_to_float(row.competitor_price_2),
        competitor_price_3=money_to_float(row.competitor_price_3),
        comparable_prices=[float(price) for price in (row.comparable_prices or [])],
        filtered_range_low=money_to_float(row.filtered_range_low),
        filtered_range_high=money_to_float(row.filtered_range_high),
        raw_prices_found=row.raw_prices_found,
        filtered_prices_count=row.filtered_prices_count,
        outliers_removed=row.outliers_removed,
        has_reliable_data=row.has_reliable_data,
        retrieval_mode=RetrievalMode(row.retrieval_mode),
        market_trend=MarketTrend(row.market_trend),
        demand_level=DemandLevel(row.demand_level),
        summary=row.summary,
        tavily_query=row.tavily_query,
        fetched_at=row.fetched_at,
        data_trust=row.data_trust,  # type: ignore[arg-type]
        warnings=list(row.warnings or []),
    )
