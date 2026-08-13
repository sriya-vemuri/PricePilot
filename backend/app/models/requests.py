from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Category, Strategy

# target_margin = 0 means the desired baseline price equals cost.
# The pricing engine must not silently convert 0 to 1% or 30%.
_DEFAULT_TARGET_MARGIN = Decimal("30")
_DEFAULT_TARGET_MARKET = "United States"


class CreateAnalysisRequest(BaseModel):
    """Input for creating a complete pricing analysis. No pricing math here."""

    product_name: str
    category: Category
    cost: Decimal = Field(gt=0)
    target_margin: Decimal = Field(default=_DEFAULT_TARGET_MARGIN, ge=0, le=95)
    target_market: str = Field(default=_DEFAULT_TARGET_MARKET, max_length=100)
    strategy: Strategy

    @field_validator("product_name")
    @classmethod
    def validate_product_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("product_name must not be empty")
        if len(trimmed) > 200:
            raise ValueError("product_name must be at most 200 characters")
        return trimmed

    @field_validator("target_market")
    @classmethod
    def validate_target_market(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            return _DEFAULT_TARGET_MARKET
        if len(trimmed) > 100:
            raise ValueError("target_market must be at most 100 characters")
        return trimmed
