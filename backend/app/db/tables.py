"""SQLAlchemy table mappings for PricePilot persistence.

Relationships:
    Analysis 1:1 MarketData via market_data.analysis_id UNIQUE + CASCADE.
    MarketCache is independent of analyses (Tavily research reuse).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONList, MarginPercent, Money, UTCDateTime, utc_now


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now)

    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    target_margin: Mapped[Decimal] = mapped_column(MarginPercent(), nullable=False)
    target_market: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    pricing_mode: Mapped[str] = mapped_column(String(20), nullable=False)

    baseline_price: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    recommended_price: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    price_range_low: Mapped[Decimal] = mapped_column(Money(), nullable=False)
    price_range_high: Mapped[Decimal] = mapped_column(Money(), nullable=False)

    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    pricing_basis: Mapped[str] = mapped_column(String(50), nullable=False)
    recommendation_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False)
    demand_signal: Mapped[str] = mapped_column(String(50), nullable=False)

    competitor_avg_price: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    competitor_avg_status: Mapped[str] = mapped_column(String(80), nullable=False)

    trace_tavily_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_prices_found: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_filtered_low: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    trace_filtered_high: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    trace_filtered_count: Mapped[int] = mapped_column(Integer, nullable=False)
    trace_used_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False)
    trace_market_trend: Mapped[str] = mapped_column(String(50), nullable=False)
    trace_demand_level: Mapped[str] = mapped_column(String(50), nullable=False)
    trace_competitor_avg_used: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)

    price_variance: Mapped[float | None] = mapped_column(Float, nullable=True)
    sanity_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    baseline_status: Mapped[str] = mapped_column(String(50), nullable=False)
    baseline_conflict: Mapped[bool] = mapped_column(Boolean, nullable=False)
    baseline_conflict_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    market_data: Mapped[MarketData] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class MarketData(Base):
    __tablename__ = "market_data"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tavily_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_trend: Mapped[str] = mapped_column(String(50), nullable=False)
    demand_level: Mapped[str] = mapped_column(String(50), nullable=False)
    pricing_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    competitor_price_1: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    competitor_price_2: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    competitor_price_3: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    comparable_prices: Mapped[list[Any]] = mapped_column(JSONList, nullable=False, default=list)
    filtered_range_low: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    filtered_range_high: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    raw_prices_found: Mapped[int] = mapped_column(Integer, nullable=False)
    filtered_prices_count: Mapped[int] = mapped_column(Integer, nullable=False)
    outliers_removed: Mapped[int] = mapped_column(Integer, nullable=False)
    has_reliable_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    retrieval_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    data_trust: Mapped[str] = mapped_column(String(20), nullable=False)
    warnings: Mapped[list[Any]] = mapped_column(JSONList, nullable=False, default=list)

    analysis: Mapped[Analysis] = relationship(back_populates="market_data")


class MarketCache(Base):
    """Persistent Tavily research cache, independent of analyses.

    candidate_prices stores unique extracted prices BEFORE baseline-aware
    outlier filtering. comparable_prices is a snapshot of the filtered
    result from the run that wrote the cache. Future cache reads must
    re-filter candidate_prices with the current analysis baseline rather
    than reusing comparable_prices blindly.
    """

    __tablename__ = "market_cache"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    target_market: Mapped[str] = mapped_column(String(100), nullable=False)
    pricing_mode: Mapped[str] = mapped_column(String(20), nullable=False)

    candidate_prices: Mapped[list[Any]] = mapped_column(JSONList, nullable=False, default=list)
    competitor_price_1: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    competitor_price_2: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    competitor_price_3: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    comparable_prices: Mapped[list[Any]] = mapped_column(JSONList, nullable=False, default=list)
    filtered_range_low: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    filtered_range_high: Mapped[Decimal | None] = mapped_column(Money(), nullable=True)
    raw_prices_found: Mapped[int] = mapped_column(Integer, nullable=False)
    filtered_prices_count: Mapped[int] = mapped_column(Integer, nullable=False)
    outliers_removed: Mapped[int] = mapped_column(Integer, nullable=False)
    has_reliable_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    retrieval_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    market_trend: Mapped[str] = mapped_column(String(50), nullable=False)
    demand_level: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tavily_query: Mapped[str] = mapped_column(Text, nullable=False, default="")
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    data_trust: Mapped[str] = mapped_column(String(20), nullable=False)
    warnings: Mapped[list[Any]] = mapped_column(JSONList, nullable=False, default=list)
