from decimal import Decimal

import pytest

from app.models.enums import (
    Category,
    DemandLevel,
    MarketTrend,
    PricingBasis,
    PricingMode,
    RecommendationMode,
    Strategy,
)
from app.models.responses import PricingInput
from app.services.pricing import generate_pricing


def make_input(**overrides) -> PricingInput:
    defaults = {
        "cost": Decimal("100"),
        "target_margin": Decimal("30"),
        "strategy": Strategy.BALANCED,
        "category": Category.ELECTRONICS,
        "pricing_mode": PricingMode.RETAIL,
        "comparable_prices": [],
        "demand_level": DemandLevel.MODERATE,
        "market_trend": MarketTrend.STABLE,
        "raw_prices_found": 0,
        "data_trust": "medium",
    }
    defaults.update(overrides)
    return PricingInput(**defaults)


def uniform_prices(center: float, count: int, spread: float = 0.05) -> list[float]:
    """Generate `count` comparable prices around `center` with modest spread."""
    if count == 0:
        return []
    if count == 1:
        return [center]
    step = (center * spread) / max(count - 1, 1)
    return [round(center - center * spread / 2 + step * i, 2) for i in range(count)]
