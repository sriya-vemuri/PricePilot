from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db.url import normalize_database_url

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def parse_cors_origins(value: Any) -> list[str]:
    """Parse CORS origins from a list, JSON array string, or comma-separated string."""
    if value is None:
        return list(_DEFAULT_CORS_ORIGINS)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return list(_DEFAULT_CORS_ORIGINS)
        if text.startswith("["):
            import json

            parsed = json.loads(text)
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS JSON must be an array of strings")
            origins = [str(item).strip() for item in parsed if str(item).strip()]
        else:
            origins = [part.strip() for part in text.split(",") if part.strip()]
        return origins or list(_DEFAULT_CORS_ORIGINS)

    if isinstance(value, (list, tuple)):
        origins = [str(item).strip() for item in value if str(item).strip()]
        return origins or list(_DEFAULT_CORS_ORIGINS)

    raise ValueError("CORS_ORIGINS must be a list or comma-separated string")


class Settings(BaseSettings):
    """Application settings. TAVILY_API_KEY is optional at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./pricepilot.db"
    tavily_api_key: str | None = None
    tavily_timeout_seconds: float = 15
    tavily_max_retries: int = 3
    market_cache_reliable_ttl_seconds: int = 24 * 60 * 60
    market_cache_low_quality_ttl_seconds: int = 15 * 60
    cors_origins: list[str] = Field(default_factory=lambda: list(_DEFAULT_CORS_ORIGINS))
    supabase_url: str = Field(min_length=1)

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: Any) -> Any:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        return parse_cors_origins(value)

    @field_validator("supabase_url", mode="before")
    @classmethod
    def _normalize_supabase_url(cls, value: Any) -> Any:
        if value is None:
            return value
        text = str(value).strip().rstrip("/")
        return text

    @property
    def supabase_jwt_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
