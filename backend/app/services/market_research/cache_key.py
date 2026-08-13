"""Normalize market-research cache keys.

target_market is part of the key because it changes Tavily query text.
baseline_price is intentionally excluded: cached candidate_prices are
re-filtered against the current analysis baseline on read.
"""

from app.models.enums import Category, PricingMode


def normalize_cache_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def build_cache_key(
    product_name: str,
    category: Category | str,
    target_market: str,
    pricing_mode: PricingMode | str,
) -> str:
    category_value = category.value if isinstance(category, Category) else str(category)
    mode_value = pricing_mode.value if isinstance(pricing_mode, PricingMode) else str(pricing_mode)
    return "|".join(
        [
            normalize_cache_text(product_name),
            normalize_cache_text(category_value),
            normalize_cache_text(target_market),
            normalize_cache_text(mode_value),
        ]
    )
