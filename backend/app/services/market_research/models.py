from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import DemandLevel, MarketTrend, PricingMode, RetrievalMode
from app.models.responses import DataTrust

QueryKind = Literal["pricing", "trend", "demand"]

# Deterministic warning codes returned by MarketResearchService.
WARNING_TAVILY_PARTIAL_FAILURE = "tavily_partial_failure"
WARNING_TAVILY_UNAVAILABLE = "tavily_unavailable"
WARNING_TREND_UNAVAILABLE = "trend_unavailable"
WARNING_DEMAND_UNAVAILABLE = "demand_unavailable"
WARNING_INSUFFICIENT_MARKET_DATA = "insufficient_market_data"
WARNING_STAGE3_LOW_TRUST = "stage3_low_trust"


class PriceSource(StrEnum):
    PRODUCT_PAGE = "product_page"
    EDITORIAL = "editorial"
    SERVICE_CONTEXT = "service_context"


class ExtractedPrice(BaseModel):
    price: float
    source: PriceSource
    context: str = ""


class MarketQuery(BaseModel):
    text: str
    stage: int
    trust: DataTrust
    query_kind: QueryKind
    include_domains: tuple[str, ...] = ()


class FilteredMarketResult(BaseModel):
    comparable_prices: list[float] = Field(default_factory=list)
    competitor_price_1: float | None = None
    competitor_price_2: float | None = None
    competitor_price_3: float | None = None
    filtered_range_low: float | None = None
    filtered_range_high: float | None = None
    raw_prices_found: int
    filtered_prices_count: int
    outliers_removed: int
    has_reliable_data: bool

    @model_validator(mode="after")
    def _counts_are_consistent(self) -> "FilteredMarketResult":
        if self.filtered_prices_count != len(self.comparable_prices):
            raise ValueError("filtered_prices_count must equal len(comparable_prices)")
        if self.outliers_removed < 0:
            raise ValueError("outliers_removed must never be negative")
        return self


class MarketResearchResult(BaseModel):
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
    market_trend: MarketTrend
    demand_level: DemandLevel
    summary: str
    tavily_query: str
    fetched_at: datetime
    data_trust: DataTrust
    warnings: list[str] = Field(default_factory=list)
    cache_hit: bool = False

    @model_validator(mode="after")
    def _counts_are_consistent(self) -> "MarketResearchResult":
        if self.filtered_prices_count != len(self.comparable_prices):
            raise ValueError("filtered_prices_count must equal len(comparable_prices)")
        if self.outliers_removed < 0:
            raise ValueError("outliers_removed must never be negative")
        return self
