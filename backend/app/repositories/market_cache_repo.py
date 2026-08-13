from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.tables import MarketCache
from app.db.types import utc_now
from app.repositories.errors import DatabaseError
from app.repositories.mappers import apply_cache_upsert, cache_from_upsert, to_cache_record
from app.repositories.schemas import MarketCacheRecord, MarketCacheUpsert


class MarketCacheRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_fresh(self, cache_key: str, now: datetime | None = None) -> MarketCacheRecord | None:
        try:
            current = now or utc_now()
            row = self.session.scalar(select(MarketCache).where(MarketCache.cache_key == cache_key))
            if row is None:
                return None
            if row.expires_at <= current:
                return None
            return to_cache_record(row)
        except SQLAlchemyError as exc:
            raise DatabaseError("Failed to read market cache") from exc

    def upsert(self, payload: MarketCacheUpsert) -> MarketCacheRecord:
        try:
            row = self.session.scalar(select(MarketCache).where(MarketCache.cache_key == payload.cache_key))
            if row is None:
                row = cache_from_upsert(payload)
                self.session.add(row)
            else:
                apply_cache_upsert(row, payload)
            self.session.commit()
            self.session.refresh(row)
            return to_cache_record(row)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseError("Failed to upsert market cache") from exc

    def delete_expired(self, now: datetime | None = None) -> int:
        try:
            current = now or utc_now()
            result = self.session.execute(delete(MarketCache).where(MarketCache.expires_at <= current))
            self.session.commit()
            return result.rowcount or 0
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseError("Failed to delete expired cache entries") from exc
