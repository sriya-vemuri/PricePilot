from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.url import is_sqlite_url, normalize_database_url


def _engine_kwargs(database_url: str) -> dict:
    """Build create_engine kwargs. SQLite-only options stay SQLite-only."""
    kwargs: dict = {
        "future": True,
        # Helps recover from stale serverless / pooled connections.
        "pool_pre_ping": True,
    }
    if is_sqlite_url(database_url):
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


def create_db_engine(database_url: str | None = None, settings: Settings | None = None) -> Engine:
    raw = database_url or (settings or get_settings()).database_url
    url = normalize_database_url(raw)
    return create_engine(url, **_engine_kwargs(url))


_engine: Engine | None = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)


def get_engine(settings: Settings | None = None) -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine(settings=settings)
        SessionLocal.configure(bind=_engine)
    return _engine


def get_db() -> Generator[Session, None, None]:
    get_engine()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
