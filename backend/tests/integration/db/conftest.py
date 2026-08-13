from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from alembic import command
from alembic.config import Config
from app.db.base import Base
from app.db.tables import Analysis, MarketCache, MarketData
from app.db.types import utc_now
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
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.errors import DatabaseError
from app.repositories.market_cache_repo import MarketCacheRepository
from app.repositories.schemas import AnalysisCreate, MarketCacheUpsert, MarketDataCreate
from app.services.market_research.cache_key import build_cache_key
from app.services.market_research.price_filter import filter_comparable_prices


BACKEND_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine) -> Session:
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    db_session = factory()
    try:
        yield db_session
    finally:
        db_session.close()


def _market_data(**overrides) -> MarketDataCreate:
    payload = {
        "fetched_at": utc_now(),
        "summary": "Pricing: around $26. | Trend: Growing. | Demand: High demand.",
        "tavily_query": "Widget price US USD",
        "market_trend": MarketTrend.GROWING,
        "demand_level": DemandLevel.HIGH,
        "pricing_mode": PricingMode.RETAIL,
        "competitor_price_1": 24.99,
        "competitor_price_2": 26.00,
        "competitor_price_3": 28.00,
        "comparable_prices": [24.99, 26.00, 28.00],
        "filtered_range_low": 24.99,
        "filtered_range_high": 28.00,
        "raw_prices_found": 3,
        "filtered_prices_count": 3,
        "outliers_removed": 0,
        "has_reliable_data": True,
        "retrieval_mode": RetrievalMode.PRIMARY,
        "data_trust": "high",
        "warnings": ["tavily_partial_failure"],
    }
    payload.update(overrides)
    return MarketDataCreate(**payload)


def _analysis(**overrides) -> AnalysisCreate:
    payload = {
        "product_name": "Test Widget",
        "category": Category.ELECTRONICS,
        "cost": Decimal("19.99"),
        "target_margin": Decimal("30"),
        "target_market": "United States",
        "strategy": Strategy.BALANCED,
        "pricing_mode": PricingMode.RETAIL,
        "baseline_price": 28.56,
        "recommended_price": 26.50,
        "price_range_low": 24.38,
        "price_range_high": 28.62,
        "confidence_score": 64,
        "confidence_explanation": "Medium confidence based on 3 comparable prices.",
        "pricing_basis": PricingBasis.BASELINE_DRIVEN,
        "recommendation_mode": RecommendationMode.BASELINE_LED,
        "reasoning_summary": "Recommendation is based on baseline and market blend.",
        "demand_signal": DemandLevel.HIGH,
        "competitor_avg_price": 26.33,
        "competitor_avg_status": CompetitorAvgStatus.AVAILABLE,
        "trace_tavily_query": "Widget price US USD",
        "trace_prices_found": 3,
        "trace_filtered_low": 24.99,
        "trace_filtered_high": 28.00,
        "trace_filtered_count": 3,
        "trace_used_fallback": False,
        "trace_market_trend": MarketTrend.GROWING,
        "trace_demand_level": DemandLevel.HIGH,
        "trace_competitor_avg_used": 26.33,
        "price_variance": 0.05,
        "sanity_triggered": False,
        "baseline_status": BaselineStatus.PLAUSIBLE,
        "baseline_conflict": False,
        "baseline_conflict_reason": None,
        "market_data": _market_data(),
    }
    payload.update(overrides)
    return AnalysisCreate(**payload)


def _cache_upsert(**overrides) -> MarketCacheUpsert:
    now = utc_now()
    payload = {
        "cache_key": "widget|electronics|united states|retail",
        "expires_at": now + timedelta(hours=24),
        "product_name": "Widget",
        "category": Category.ELECTRONICS,
        "target_market": "United States",
        "pricing_mode": PricingMode.RETAIL,
        "candidate_prices": [24.99, 26.0, 28.0, 400.0],
        "competitor_price_1": 24.99,
        "competitor_price_2": 26.0,
        "competitor_price_3": 28.0,
        "comparable_prices": [24.99, 26.0, 28.0],
        "filtered_range_low": 24.99,
        "filtered_range_high": 28.0,
        "raw_prices_found": 4,
        "filtered_prices_count": 3,
        "outliers_removed": 1,
        "has_reliable_data": True,
        "retrieval_mode": RetrievalMode.PRIMARY,
        "market_trend": MarketTrend.GROWING,
        "demand_level": DemandLevel.HIGH,
        "summary": "Pricing: around $26.",
        "tavily_query": "Widget price US USD",
        "fetched_at": now,
        "data_trust": "high",
        "warnings": ["stage3_low_trust"],
    }
    payload.update(overrides)
    return MarketCacheUpsert(**payload)
