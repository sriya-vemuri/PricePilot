from sqlalchemy.engine import make_url

from app.config import Settings, parse_cors_origins
from app.db.session import _engine_kwargs, create_db_engine
from app.db.url import is_sqlite_url, normalize_database_url


class TestNormalizeDatabaseUrl:
    def test_sqlite_unchanged(self):
        url = "sqlite:///./pricepilot.db"
        assert normalize_database_url(url) == url
        assert is_sqlite_url(url) is True

    def test_postgresql_scheme_uses_psycopg(self):
        url = "postgresql://user:pass@host:5432/db"
        assert normalize_database_url(url) == "postgresql+psycopg://user:pass@host:5432/db"

    def test_postgres_scheme_uses_psycopg(self):
        url = "postgres://user:pass@host/db"
        assert normalize_database_url(url) == "postgresql+psycopg://user:pass@host/db"

    def test_existing_psycopg_dialect_not_modified(self):
        url = "postgresql+psycopg://user:pass@host/db"
        assert normalize_database_url(url) == url

    def test_query_parameters_preserved(self):
        url = "postgresql://user:pass@host/db?sslmode=require&channel_binding=require"
        normalized = normalize_database_url(url)
        assert normalized.startswith("postgresql+psycopg://")
        parsed = make_url(normalized)
        assert parsed.query["sslmode"] == "require"
        assert parsed.query["channel_binding"] == "require"
        assert parsed.username == "user"
        assert parsed.password == "pass"
        assert parsed.host == "host"
        assert parsed.database == "db"

    def test_settings_normalizes_database_url(self):
        settings = Settings(database_url="postgres://u:p@h/db")
        assert settings.database_url == "postgresql+psycopg://u:p@h/db"


class TestEngineKwargs:
    def test_sqlite_gets_check_same_thread(self):
        kwargs = _engine_kwargs("sqlite:///./pricepilot.db")
        assert kwargs["connect_args"] == {"check_same_thread": False}
        assert kwargs["pool_pre_ping"] is True

    def test_postgres_does_not_get_sqlite_connect_args(self):
        url = normalize_database_url("postgresql://user:pass@host/db")
        kwargs = _engine_kwargs(url)
        assert "connect_args" not in kwargs
        assert kwargs["pool_pre_ping"] is True

    def test_create_engine_accepts_normalized_postgres_url(self):
        # Does not connect — only builds the Engine URL/dialect.
        engine = create_db_engine("postgres://user:pass@127.0.0.1:5432/pricepilot")
        assert str(engine.url).startswith("postgresql+psycopg://")
        assert engine.dialect.name == "postgresql"
        engine.dispose()


class TestCorsOrigins:
    def test_default_localhost_origins(self):
        settings = Settings()
        assert settings.cors_origins == [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    def test_comma_separated_production_origin(self):
        settings = Settings(
            cors_origins="http://localhost:5173,https://pricepilot.vercel.app"
        )
        assert settings.cors_origins == [
            "http://localhost:5173",
            "https://pricepilot.vercel.app",
        ]

    def test_whitespace_normalization(self):
        origins = parse_cors_origins(
            " http://localhost:5173 , http://127.0.0.1:5173 , https://app.example.com "
        )
        assert origins == [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://app.example.com",
        ]

    def test_json_array_still_supported(self):
        settings = Settings(
            cors_origins='["http://localhost:5173","https://pricepilot.vercel.app"]'
        )
        assert settings.cors_origins == [
            "http://localhost:5173",
            "https://pricepilot.vercel.app",
        ]

    def test_no_wildcard_added(self):
        settings = Settings(cors_origins="https://pricepilot.vercel.app")
        assert "*" not in settings.cors_origins
        assert settings.cors_origins == ["https://pricepilot.vercel.app"]
