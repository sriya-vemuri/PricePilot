from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

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
from app.models.responses import DataTrust


class MarketDataCreate(BaseModel):
    fetched_at: datetime
    summary: str | None = None
    tavily_query: str | None = None
    market_trend: MarketTrend
    demand_level: DemandLevel
    pricing_mode: PricingMode
    competitor_price_1: float | None = None
    competitor_price_2: float | None = None
    competitor_price_3: float | None = None
    comparable_prices: list[float] = Field(default_factory=list)
    filtered_range_low: float | None = None
    filtered_range_high: float | None = None
    raw_prices_found: int
    filtered_prices_count: int
    outliers_removed: int
    has_reliable_data: bool
    retrieval_mode: RetrievalMode
    data_trust: DataTrust
    warnings: list[str] = Field(default_factory=list)


class AnalysisCreate(BaseModel):
    product_name: str
    category: Category
    cost: Decimal
    target_margin: Decimal
    target_market: str
    strategy: Strategy
    pricing_mode: PricingMode
    baseline_price: float
    recommended_price: float
    price_range_low: float
    price_range_high: float
    confidence_score: int
    confidence_explanation: str
    pricing_basis: PricingBasis
    recommendation_mode: RecommendationMode
    reasoning_summary: str
    demand_signal: DemandLevel
    competitor_avg_price: float | None = None
    competitor_avg_status: CompetitorAvgStatus
    trace_tavily_query: str | None = None
    trace_prices_found: int
    trace_filtered_low: float | None = None
    trace_filtered_high: float | None = None
    trace_filtered_count: int
    trace_used_fallback: bool
    trace_market_trend: MarketTrend
    trace_demand_level: DemandLevel
    trace_competitor_avg_used: float | None = None
    price_variance: float | None = None
    sanity_triggered: bool
    baseline_status: BaselineStatus
    baseline_conflict: bool
    baseline_conflict_reason: str | None = None
    market_data: MarketDataCreate


class MarketCacheRecord(BaseModel):
    id: UUID
    cache_key: str
    created_at: datetime
    expires_at: datetime
    product_name: str
    category: Category
    target_market: str
    pricing_mode: PricingMode
    candidate_prices: list[float] = Field(default_factory=list)
    competitor_price_1: float | None = None
    competitor_price_2: float | None = None
    competitor_price_3: float | None = None
    comparable_prices: list[float] = Field(default_factory=list)
    filtered_range_low: float | None = None
    filtered_range_high: float | None = None
    raw_prices_found: int
    filtered_prices_count: int
    outliers_removed: int
    has_reliable_data: bool
    retrieval_mode: RetrievalMode
    market_trend: MarketTrend
    demand_level: DemandLevel
    summary: str
    tavily_query: str
    fetched_at: datetime
    data_trust: DataTrust
    warnings: list[str] = Field(default_factory=list)


class MarketCacheUpsert(BaseModel):
    cache_key: str
    expires_at: datetime
    product_name: str
    category: Category
    target_market: str
    pricing_mode: PricingMode
    candidate_prices: list[float] = Field(default_factory=list)
    competitor_price_1: float | None = None
    competitor_price_2: float | None = None
    competitor_price_3: float | None = None
    comparable_prices: list[float] = Field(default_factory=list)
    filtered_range_low: float | None = None
    filtered_range_high: float | None = None
    raw_prices_found: int
    filtered_prices_count: int
    outliers_removed: int
    has_reliable_data: bool
    retrieval_mode: RetrievalMode
    market_trend: MarketTrend
    demand_level: DemandLevel
    summary: str = ""
    tavily_query: str = ""
    fetched_at: datetime
    data_trust: DataTrust
    warnings: list[str] = Field(default_factory=list)
