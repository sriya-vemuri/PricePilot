from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


BACKEND_ROOT = Path(__file__).resolve().parents[3]
HEAD_REVISION = "0003_widen_target_market"


def _alembic_config(db_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


class TestAlembic:
    def test_upgrade_and_downgrade_on_empty_sqlite(self, tmp_path):
        db_path = tmp_path / "alembic_test.db"
        db_url = f"sqlite:///{db_path}"
        config = _alembic_config(db_url)

        command.upgrade(config, "head")
        engine = create_engine(db_url)
        tables = set(inspect(engine).get_table_names())
        assert {"analyses", "market_data", "market_cache", "alembic_version"}.issubset(tables)
        version = engine.connect().execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version == HEAD_REVISION
        columns = {col["name"] for col in inspect(engine).get_columns("analyses")}
        assert "user_id" in columns
        engine.dispose()

        command.downgrade(config, "base")
        engine = create_engine(db_url)
        tables_after = set(inspect(engine).get_table_names())
        assert "analyses" not in tables_after
        assert "market_data" not in tables_after
        assert "market_cache" not in tables_after
        engine.dispose()

    def test_user_id_migration_preserves_existing_sqlite_rows(self, tmp_path):
        db_path = tmp_path / "alembic_legacy.db"
        db_url = f"sqlite:///{db_path}"
        config = _alembic_config(db_url)

        command.upgrade(config, "0001_initial_schema")
        engine = create_engine(db_url)
        with engine.begin() as connection:
            analysis_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                text(
                    """
                    INSERT INTO analyses (
                        id, created_at, product_name, category, cost, target_margin,
                        target_market, strategy, pricing_mode, baseline_price, recommended_price,
                        price_range_low, price_range_high, confidence_score, confidence_explanation,
                        pricing_basis, recommendation_mode, reasoning_summary, demand_signal,
                        competitor_avg_status, trace_prices_found, trace_filtered_count,
                        trace_used_fallback, trace_market_trend, trace_demand_level,
                        sanity_triggered, baseline_status, baseline_conflict
                    ) VALUES (
                        :id, :created_at, 'Legacy Widget', 'electronics', 10, 30,
                        'United States', 'balanced', 'retail', 14.29, 14.29,
                        12, 16, 50, 'ok',
                        'baseline_driven', 'baseline_led', 'legacy', 'moderate',
                        'unavailable', 0, 0,
                        1, 'stable', 'moderate',
                        0, 'plausible', 0
                    )
                    """
                ),
                {"id": analysis_id, "created_at": now},
            )
        engine.dispose()

        command.upgrade(config, "head")
        engine = create_engine(db_url)
        row = engine.connect().execute(
            text("SELECT product_name, user_id FROM analyses WHERE id = :id"),
            {"id": analysis_id},
        ).mappings().one()
        assert row["product_name"] == "Legacy Widget"
        assert row["user_id"] is None
        version = engine.connect().execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version == HEAD_REVISION
        index_names = {ix["name"] for ix in inspect(engine).get_indexes("analyses")}
        assert "ix_analyses_user_id" in index_names
        engine.dispose()
