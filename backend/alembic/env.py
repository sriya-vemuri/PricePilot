from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.base import Base
from app.db.tables import Analysis, MarketCache, MarketData  # noqa: F401
from app.db.url import normalize_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL priority:
# 1) DATABASE_URL in the process environment (production migrations)
# 2) sqlalchemy.url already on the Alembic Config (tests / alembic.ini)
# 3) Settings (.env / defaults)
# Never log the URL — it may contain credentials.
_raw_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or get_settings().database_url
config.set_main_option("sqlalchemy.url", normalize_database_url(_raw_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
