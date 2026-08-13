"""Portable SQLAlchemy column types.

Money:
    Stored as Numeric(12, 2) and mapped to Decimal in Python.
    API responses still convert to float because the frontend contract
    expects JSON numbers.

JSON lists:
    comparable_prices, candidate_prices, and warnings are stored with
    SQLAlchemy's JSON type. SQLite persists JSON as TEXT; PostgreSQL
    can use native JSON without changing the ORM mapping.

UUIDs:
    Stored via SQLAlchemy Uuid(as_uuid=True) so Python sees uuid.UUID.
    SQLite stores a CHAR representation; PostgreSQL can use UUID later.

Datetimes:
    Always UTC. SQLite has no timezone type, so values are normalized
    to timezone-aware UTC on bind and result.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Numeric, TypeDecorator
from sqlalchemy import JSON as SA_JSON


MONEY_PRECISION = 12
MONEY_SCALE = 2
MARGIN_PRECISION = 5
MARGIN_SCALE = 2


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetime, portable across SQLite and PostgreSQL."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Money(TypeDecorator):
    """Decimal money with 2-cent scale. Avoids binary float storage."""

    impl = Numeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True)
    cache_ok = True

    def process_bind_param(self, value: Decimal | float | int | str | None, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def process_result_value(self, value: Any, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.01"))


class MarginPercent(TypeDecorator):
    """Target margin percent stored as Numeric(5, 2)."""

    impl = Numeric(MARGIN_PRECISION, MARGIN_SCALE, asdecimal=True)
    cache_ok = True

    def process_bind_param(self, value: Decimal | float | int | str | None, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def process_result_value(self, value: Any, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))


JSONList = SA_JSON


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def money_to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)
