from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    RiskLevel,
    SimulationType,
    Strategy,
)

DataTrust = Literal["high", "medium", "low"]


class MarketDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tavily_query: str | None = None
    fetched_at: datetime
    cache_hit: bool = False
    market_trend: MarketTrend
    demand_level: DemandLevel
    summary: str | None = None
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
    pricing_mode: PricingMode
    data_trust: DataTrust


class MarketDataSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tavily_query: str | None = None
    market_trend: MarketTrend
    demand_level: DemandLevel
    competitor_price_1: float | None = None
    competitor_price_2: float | None = None
    competitor_price_3: float | None = None


class AnalysisSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    product_name: str
    category: Category
    strategy: Strategy
    recommended_price: float
    competitor_avg_price: float | None = None
    confidence_score: int
    demand_signal: DemandLevel
    market_data: MarketDataSummary


class AnalysisListResponse(BaseModel):
    items: list[AnalysisSummaryResponse]
    total: int
    limit: int
    offset: int


class AnalysisDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    product_name: str
    category: Category
    cost: float
    target_margin: float
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
    market_data: MarketDataResponse
    market_warnings: list[str] = Field(default_factory=list)


class PricingInput(BaseModel):
    """Internal contract for the pricing engine (not an HTTP endpoint)."""

    cost: Decimal
    target_margin: Decimal
    strategy: Strategy
    category: Category
    pricing_mode: PricingMode
    comparable_prices: list[float]
    demand_level: DemandLevel
    market_trend: MarketTrend
    raw_prices_found: int
    data_trust: DataTrust


class PricingResult(BaseModel):
    """Internal contract for pricing-engine output (not an HTTP endpoint)."""

    baseline_price: float
    recommended_price: float
    price_range_low: float
    price_range_high: float
    confidence_score: int
    confidence_explanation: str
    pricing_basis: PricingBasis
    recommendation_mode: RecommendationMode
    reasoning_summary: str
    competitor_avg_price: float | None = None
    competitor_avg_status: CompetitorAvgStatus
    price_variance: float | None = None
    sanity_triggered: bool
    baseline_status: BaselineStatus
    baseline_conflict: bool
    baseline_conflict_reason: str | None = None
    used_fallback: bool


class SimulationRequest(BaseModel):
    simulation_type: SimulationType
    custom_price: float | None = Field(default=None, gt=0)
    current_price: float | None = None
    competitor_avg: float | None = None
    demand_level: DemandLevel | None = None
    strategy: Strategy | None = None


class SimulationResponse(BaseModel):
    new_price: float
    pct_change: float
    risk_level: RiskLevel
    demand_impact: int
    demand_note: str
    vs_competitor: str | None = None
    explanation: str
