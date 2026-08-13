"""Database URL helpers for SQLite (local) and PostgreSQL (production)."""


def normalize_database_url(url: str) -> str:
    """Normalize provider URLs to the SQLAlchemy Psycopg 3 dialect.

    - postgres://... → postgresql+psycopg://...
    - postgresql://... → postgresql+psycopg://...
    - postgresql+psycopg://... left unchanged
    - sqlite://... left unchanged

    Credentials, host, path, and query parameters are preserved.
    """
    value = (url or "").strip()
    if not value:
        return value

    lower = value.lower()
    if lower.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if lower.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    return value


def is_sqlite_url(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite:")
