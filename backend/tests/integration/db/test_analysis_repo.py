from decimal import Decimal
from time import sleep
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, select

from app.db.tables import Analysis, MarketCache, MarketData
from app.models.enums import (
    Category,
    DemandLevel,
    RecommendationMode,
    Strategy,
)
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.errors import DatabaseError
from app.repositories.mappers import analysis_from_create
from app.repositories.market_cache_repo import MarketCacheRepository
from tests.integration.db.conftest import _analysis, _cache_upsert, _market_data

OWNER = "test-user-id"
USER_A = "user-a"
USER_B = "user-b"


class TestAnalysisSave:
    def test_save_complete_analysis_and_market_data(self, session):
        saved = AnalysisRepository(session).save_analysis(_analysis())

        assert isinstance(saved.id, UUID)
        assert saved.created_at is not None
        assert saved.created_at.tzinfo is not None
        assert saved.cost == pytest.approx(19.99)
        assert saved.target_margin == pytest.approx(30)
        assert saved.recommended_price == pytest.approx(26.50)
        assert saved.market_data.comparable_prices == [24.99, 26.00, 28.00]
        assert saved.market_warnings == ["tavily_partial_failure"]
        assert saved.recommendation_mode == RecommendationMode.BASELINE_LED
        assert saved.category == Category.ELECTRONICS
        assert saved.strategy == Strategy.BALANCED
        assert saved.demand_signal == DemandLevel.HIGH
        assert saved.market_data.data_trust == "high"

        row_count = session.scalar(select(Analysis).where(Analysis.id == saved.id))
        assert row_count is not None
        market_count = session.scalar(select(MarketData).where(MarketData.analysis_id == saved.id))
        assert market_count is not None

    def test_money_values_round_trip(self, session):
        payload = _analysis(cost=Decimal("19.99"), target_margin=Decimal("12.5"), recommended_price=27.41)
        saved = AnalysisRepository(session).save_analysis(payload)
        loaded = AnalysisRepository(session).get_by_id(saved.id, OWNER)
        assert loaded is not None
        assert loaded.cost == pytest.approx(19.99)
        assert loaded.target_margin == pytest.approx(12.5)
        assert loaded.recommended_price == pytest.approx(27.41)
        assert loaded.market_data.competitor_price_1 == pytest.approx(24.99)


class TestAnalysisTransaction:
    def test_market_data_failure_rolls_back_analysis(self, session):
        def fail_market_data(*_args, **_kwargs):
            raise RuntimeError("forced market_data failure")

        event.listen(MarketData, "after_insert", fail_market_data)
        try:
            with pytest.raises((RuntimeError, DatabaseError)):
                AnalysisRepository(session).save_analysis(_analysis())
        finally:
            event.remove(MarketData, "after_insert", fail_market_data)

        session.rollback()
        assert session.scalar(select(Analysis)) is None
        assert session.scalar(select(MarketData)) is None


class TestAnalysisGet:
    def test_get_existing_includes_market_data(self, session):
        saved = AnalysisRepository(session).save_analysis(_analysis())
        loaded = AnalysisRepository(session).get_by_id(saved.id, OWNER)
        assert loaded is not None
        assert loaded.id == saved.id
        assert loaded.market_data.filtered_prices_count == 3
        assert loaded.market_data.tavily_query == "Widget price US USD"

    def test_missing_id_returns_none(self, session):
        assert AnalysisRepository(session).get_by_id(uuid4(), OWNER) is None


class TestAnalysisList:
    def test_list_newest_first_with_limit_offset_and_total(self, session):
        repo = AnalysisRepository(session)
        first = repo.save_analysis(_analysis(product_name="Older Widget"))
        sleep(0.02)
        second = repo.save_analysis(_analysis(product_name="Newer Widget"))
        sleep(0.02)
        third = repo.save_analysis(_analysis(product_name="Newest Widget"))

        page = repo.list_analyses(OWNER, limit=2, offset=0)
        assert page.total == 3
        assert page.limit == 2
        assert page.offset == 0
        assert [item.product_name for item in page.items] == ["Newest Widget", "Newer Widget"]
        assert page.items[0].id == third.id
        assert page.items[0].market_data.competitor_price_1 == pytest.approx(24.99)

        page2 = repo.list_analyses(OWNER, limit=2, offset=2)
        assert page2.total == 3
        assert [item.product_name for item in page2.items] == ["Older Widget"]
        assert page2.items[0].id == first.id
        assert page2.items[0].market_data.demand_level == DemandLevel.HIGH
        _ = second


class TestEnumRoundTrip:
    def test_enum_values_round_trip(self, session):
        saved = AnalysisRepository(session).save_analysis(
            _analysis(
                category=Category.HEALTH_BEAUTY,
                strategy=Strategy.PREMIUM,
                recommendation_mode=RecommendationMode.MARKET_LED,
                demand_signal=DemandLevel.VERY_HIGH,
                market_data=_market_data(data_trust="low"),
            )
        )
        loaded = AnalysisRepository(session).get_by_id(saved.id, OWNER)
        assert loaded is not None
        assert loaded.category == Category.HEALTH_BEAUTY
        assert loaded.strategy == Strategy.PREMIUM
        assert loaded.recommendation_mode == RecommendationMode.MARKET_LED
        assert loaded.demand_signal == DemandLevel.VERY_HIGH
        assert loaded.market_data.data_trust == "low"


class TestAnalysisOwnership:
    def test_save_stores_user_id(self, session):
        saved = AnalysisRepository(session).save_analysis(_analysis(user_id=USER_A))
        row = session.scalar(select(Analysis).where(Analysis.id == saved.id))
        assert row is not None
        assert row.user_id == USER_A

    def test_list_is_scoped_to_user(self, session):
        repo = AnalysisRepository(session)
        repo.save_analysis(_analysis(product_name="A One", user_id=USER_A))
        sleep(0.02)
        repo.save_analysis(_analysis(product_name="A Two", user_id=USER_A))
        repo.save_analysis(_analysis(product_name="B One", user_id=USER_B))

        listed_a = repo.list_analyses(USER_A)
        listed_b = repo.list_analyses(USER_B)
        assert listed_a.total == 2
        assert [item.product_name for item in listed_a.items] == ["A Two", "A One"]
        assert listed_b.total == 1
        assert [item.product_name for item in listed_b.items] == ["B One"]

    def test_list_excludes_null_legacy_rows_and_scopes_total(self, session):
        repo = AnalysisRepository(session)
        repo.save_analysis(_analysis(product_name="Owned", user_id=USER_A))
        legacy = analysis_from_create(_analysis(product_name="Legacy"))
        legacy.user_id = None
        session.add(legacy)
        session.commit()

        listed_a = repo.list_analyses(USER_A)
        listed_b = repo.list_analyses(USER_B)
        assert listed_a.total == 1
        assert [item.product_name for item in listed_a.items] == ["Owned"]
        assert listed_b.total == 0
        assert listed_b.items == []

    def test_get_by_id_requires_matching_owner(self, session):
        repo = AnalysisRepository(session)
        saved = repo.save_analysis(_analysis(product_name="A Secret", user_id=USER_A))
        loaded = repo.get_by_id(saved.id, USER_A)
        assert loaded is not None
        assert loaded.product_name == "A Secret"
        assert repo.get_by_id(saved.id, USER_B) is None

    def test_get_legacy_null_owner_returns_none(self, session):
        repo = AnalysisRepository(session)
        legacy = analysis_from_create(_analysis(product_name="Legacy"))
        legacy.user_id = None
        session.add(legacy)
        session.commit()
        session.refresh(legacy)
        assert repo.get_by_id(legacy.id, USER_A) is None
        assert repo.get_by_id(legacy.id, USER_B) is None


class TestAnalysisDelete:
    def test_owner_can_delete_analysis_and_market_data(self, session):
        repo = AnalysisRepository(session)
        saved = repo.save_analysis(_analysis(product_name="To Delete", user_id=USER_A))
        assert session.scalar(select(MarketData).where(MarketData.analysis_id == saved.id)) is not None

        assert repo.delete_for_user(saved.id, USER_A) is True
        assert repo.get_by_id(saved.id, USER_A) is None
        assert session.scalar(select(Analysis).where(Analysis.id == saved.id)) is None
        assert session.scalar(select(MarketData).where(MarketData.analysis_id == saved.id)) is None

    def test_other_user_cannot_delete(self, session):
        repo = AnalysisRepository(session)
        saved = repo.save_analysis(_analysis(product_name="A Secret", user_id=USER_A))
        assert repo.delete_for_user(saved.id, USER_B) is False
        assert repo.get_by_id(saved.id, USER_A) is not None
        assert session.scalar(select(MarketData).where(MarketData.analysis_id == saved.id)) is not None

    def test_missing_id_returns_false(self, session):
        assert AnalysisRepository(session).delete_for_user(uuid4(), USER_A) is False

    def test_delete_does_not_touch_market_cache(self, session):
        repo = AnalysisRepository(session)
        saved = repo.save_analysis(_analysis(product_name="Cached Widget", user_id=USER_A))
        cache = MarketCacheRepository(session).upsert(_cache_upsert())
        cache_id = cache.id

        assert repo.delete_for_user(saved.id, USER_A) is True
        remaining = session.scalar(select(MarketCache).where(MarketCache.id == cache_id))
        assert remaining is not None
        assert remaining.cache_key == cache.cache_key
