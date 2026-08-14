import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.db.tables import MarketData
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.mappers import cache_from_upsert
from tests.integration.db.conftest import _analysis, _cache_upsert


class TestSchema:
    def test_tables_exist(self, engine):
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"analyses", "market_data", "market_cache"}.issubset(tables)
        columns = {col["name"]: col for col in inspector.get_columns("analyses")}
        assert columns["user_id"]["nullable"] is True
        assert "user_id" not in {col["name"] for col in inspector.get_columns("market_data")}
        assert "user_id" not in {col["name"] for col in inspector.get_columns("market_cache")}
        indexes = inspector.get_indexes("analyses")
        assert any(ix.get("name") == "ix_analyses_user_id" for ix in indexes)

    def test_cache_key_is_unique(self, session):
        session.add(cache_from_upsert(_cache_upsert()))
        session.commit()
        session.add(cache_from_upsert(_cache_upsert()))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_one_market_data_per_analysis(self, session):
        saved = AnalysisRepository(session).save_analysis(_analysis())
        extra = MarketData(
            analysis_id=saved.id,
            fetched_at=saved.market_data.fetched_at,
            market_trend="stable",
            demand_level="moderate",
            pricing_mode="retail",
            comparable_prices=[],
            raw_prices_found=0,
            filtered_prices_count=0,
            outliers_removed=0,
            has_reliable_data=False,
            retrieval_mode="exhausted",
            data_trust="low",
            warnings=[],
        )
        session.add(extra)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
