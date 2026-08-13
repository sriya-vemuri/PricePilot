from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


BACKEND_ROOT = Path(__file__).resolve().parents[3]


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
        assert version == "0001_initial_schema"
        engine.dispose()

        command.downgrade(config, "base")
        engine = create_engine(db_url)
        tables_after = set(inspect(engine).get_table_names())
        assert "analyses" not in tables_after
        assert "market_data" not in tables_after
        assert "market_cache" not in tables_after
        engine.dispose()
