from app.models.enums import Category, PricingMode

# [min_realistic, max_realistic] USD bounds from the legacy pricing engine.
# Pricing logic is not implemented in this phase.
CATEGORY_BOUNDS: dict[Category, tuple[float, float]] = {
    Category.ELECTRONICS: (5.0, 5000.0),
    Category.CLOTHING: (3.0, 2000.0),
    Category.FOOD_BEVERAGE: (0.5, 500.0),
    Category.HEALTH_BEAUTY: (1.0, 1000.0),
    Category.HOME_GARDEN: (2.0, 5000.0),
    Category.AUTOMOTIVE: (2.0, 20000.0),
    Category.SOFTWARE: (1.0, 5000.0),
    Category.SERVICES: (20.0, 50000.0),
    Category.OTHER: (1.0, 10000.0),
}

_CATEGORY_TO_PRICING_MODE: dict[Category, PricingMode] = {
    Category.ELECTRONICS: PricingMode.RETAIL,
    Category.SOFTWARE: PricingMode.RETAIL,
    Category.CLOTHING: PricingMode.RETAIL,
    Category.FOOD_BEVERAGE: PricingMode.RETAIL,
    Category.HEALTH_BEAUTY: PricingMode.RETAIL,
    Category.HOME_GARDEN: PricingMode.RETAIL,
    Category.AUTOMOTIVE: PricingMode.RETAIL,
    Category.SERVICES: PricingMode.SERVICE,
    Category.OTHER: PricingMode.RETAIL,
}


def get_pricing_mode(category: Category) -> PricingMode:
    """Map a product category to retail or service pricing mode."""
    return _CATEGORY_TO_PRICING_MODE.get(category, PricingMode.RETAIL)
