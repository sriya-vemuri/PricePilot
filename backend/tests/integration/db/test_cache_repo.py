from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.tables import MarketCache
from app.db.types import utc_now
from app.models.enums import Category, PricingMode
from app.repositories.mappers import cache_from_upsert
from app.repositories.market_cache_repo import MarketCacheRepository
from app.services.market_research.cache_key import build_cache_key
from app.services.market_research.price_filter import filter_comparable_prices
from tests.integration.db.conftest import _cache_upsert


class TestMarketCache:
    def test_insert_and_fresh_hit(self, session):
        repo = MarketCacheRepository(session)
        stored = repo.upsert(_cache_upsert())
        hit = repo.get_fresh(stored.cache_key)
        assert hit is not None
        assert hit.cache_key == stored.cache_key
        assert hit.candidate_prices == [24.99, 26.0, 28.0, 400.0]
        assert hit.comparable_prices == [24.99, 26.0, 28.0]
        assert hit.warnings == ["stage3_low_trust"]

    def test_expired_entry_returns_none(self, session):
        repo = MarketCacheRepository(session)
        expired = _cache_upsert(expires_at=utc_now() - timedelta(minutes=1))
        repo.upsert(expired)
        assert repo.get_fresh(expired.cache_key) is None

    def test_upsert_replaces_same_key(self, session):
        repo = MarketCacheRepository(session)
        first = repo.upsert(_cache_upsert(summary="first"))
        second = repo.upsert(_cache_upsert(summary="updated", comparable_prices=[10.0, 11.0, 12.0]))
        assert first.id == second.id
        assert second.summary == "updated"
        assert second.comparable_prices == [10.0, 11.0, 12.0]
        count = session.scalar(select(func.count()).select_from(MarketCache))
        assert count == 1

    def test_unique_key_constraint(self, session):
        session.add(cache_from_upsert(_cache_upsert()))
        session.commit()
        session.add(cache_from_upsert(_cache_upsert(summary="other")))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


class TestCacheKeyNormalization:
    def test_product_casing_and_spaces_normalized(self):
        left = build_cache_key("  Vitamin   C Serum ", Category.HEALTH_BEAUTY, "United States", PricingMode.RETAIL)
        right = build_cache_key("vitamin c serum", Category.HEALTH_BEAUTY, "united states", PricingMode.RETAIL)
        assert left == right

    def test_target_market_normalization(self):
        left = build_cache_key("Widget", Category.ELECTRONICS, "  United   Kingdom ", PricingMode.RETAIL)
        right = build_cache_key("Widget", Category.ELECTRONICS, "united kingdom", PricingMode.RETAIL)
        assert left == right

    def test_different_target_market_produces_different_key(self):
        us = build_cache_key("Widget", Category.ELECTRONICS, "United States", PricingMode.RETAIL)
        uk = build_cache_key("Widget", Category.ELECTRONICS, "United Kingdom", PricingMode.RETAIL)
        assert us != uk


class TestBaselineCacheCorrectness:
    def test_candidate_prices_can_be_refiltered_for_different_baselines(self, session):
        repo = MarketCacheRepository(session)
        stored = repo.upsert(
            _cache_upsert(
                category=Category.CLOTHING,
                candidate_prices=[80.0, 90.0, 100.0, 200.0],
                comparable_prices=[80.0, 90.0, 100.0],
            )
        )
        hit = repo.get_fresh(stored.cache_key)
        assert hit is not None
        assert 200.0 in hit.candidate_prices

        tight = filter_comparable_prices(
            hit.candidate_prices,
            baseline_price=30.0,
            category=Category.CLOTHING,
            pricing_mode=PricingMode.RETAIL,
        )
        wide = filter_comparable_prices(
            hit.candidate_prices,
            baseline_price=100.0,
            category=Category.CLOTHING,
            pricing_mode=PricingMode.RETAIL,
        )
        assert 200.0 not in tight.comparable_prices
        assert 200.0 in wide.comparable_prices
        assert hit.candidate_prices == [80.0, 90.0, 100.0, 200.0]
