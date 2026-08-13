"""Pure market-price outlier filtering.

This is the only layer that performs comparable-price outlier filtering.
The pricing engine must continue to trust `comparable_prices` as already cleaned.
"""

from collections.abc import Sequence

from app.core.stats import median, percentile
from app.models.enums import Category, PricingMode
from app.services.market_research.constants import (
    IQR_MIN_SAMPLE_SIZE,
    LOW_TICKET_BASELINE_CAP,
    LOW_TICKET_CATEGORIES,
    MIN_RELIABLE_PRICES,
    RETAIL_COARSE_MULTIPLIER,
    RETAIL_IQR_MULTIPLIER,
    SERVICE_COARSE_MULTIPLIER,
    SERVICE_IQR_MULTIPLIER,
)
from app.services.market_research.models import ExtractedPrice, FilteredMarketResult


def filter_comparable_prices(
    prices: Sequence[float] | Sequence[ExtractedPrice],
    *,
    baseline_price: float | None,
    category: Category,
    pricing_mode: PricingMode,
) -> FilteredMarketResult:
    values = _as_positive_unique_prices(prices)
    raw_prices_found = len(values)

    values = _apply_baseline_cap(values, baseline_price=baseline_price, category=category, pricing_mode=pricing_mode)
    values = _apply_coarse_filter(values, pricing_mode)
    values = _apply_iqr_filter(values, pricing_mode)

    comparable = sorted(round(price, 2) for price in values)
    filtered_count = len(comparable)
    outliers_removed = max(0, raw_prices_found - filtered_count)
    has_reliable_data = filtered_count >= MIN_RELIABLE_PRICES

    competitor_1 = competitor_2 = competitor_3 = None
    range_low = range_high = None
    if comparable:
        range_low = comparable[0]
        range_high = comparable[-1]
    if has_reliable_data:
        competitor_1 = comparable[0]
        competitor_2 = round(median(comparable), 2)
        competitor_3 = comparable[-1]

    return FilteredMarketResult(
        comparable_prices=comparable,
        competitor_price_1=competitor_1,
        competitor_price_2=competitor_2,
        competitor_price_3=competitor_3,
        filtered_range_low=range_low,
        filtered_range_high=range_high,
        raw_prices_found=raw_prices_found,
        filtered_prices_count=filtered_count,
        outliers_removed=outliers_removed,
        has_reliable_data=has_reliable_data,
    )


def _as_positive_unique_prices(prices: Sequence[float] | Sequence[ExtractedPrice]) -> list[float]:
    unique: dict[float, float] = {}
    for item in prices:
        value = item.price if isinstance(item, ExtractedPrice) else float(item)
        if value <= 0:
            continue
        key = round(value, 2)
        unique[key] = key
    return list(unique.values())


def _apply_baseline_cap(
    prices: list[float],
    *,
    baseline_price: float | None,
    category: Category,
    pricing_mode: PricingMode,
) -> list[float]:
    if (
        pricing_mode != PricingMode.RETAIL
        or baseline_price is None
        or baseline_price <= 0
        or category not in LOW_TICKET_CATEGORIES
    ):
        return prices

    cap_multiple = LOW_TICKET_BASELINE_CAP.get(category, 5.0)
    ceiling = baseline_price * cap_multiple
    return [price for price in prices if price <= ceiling]


def _apply_coarse_filter(prices: list[float], pricing_mode: PricingMode) -> list[float]:
    if len(prices) < MIN_RELIABLE_PRICES:
        return prices

    mid = median(prices)
    if mid <= 0:
        return prices

    multiplier = (
        SERVICE_COARSE_MULTIPLIER
        if pricing_mode == PricingMode.SERVICE
        else RETAIL_COARSE_MULTIPLIER
    )
    lo = mid / multiplier
    hi = mid * multiplier
    coarse = [price for price in prices if lo <= price <= hi]
    return coarse if coarse else prices


def _apply_iqr_filter(prices: list[float], pricing_mode: PricingMode) -> list[float]:
    """Tukey fences with linear-interpolated quartiles.

    Skipped for small samples so a reasonable 3–5 point set is not collapsed.
    If IQR would drop the set below the reliability threshold, the pre-IQR
    values are kept.
    """
    if len(prices) < IQR_MIN_SAMPLE_SIZE:
        return prices

    q1 = percentile(prices, 25)
    q3 = percentile(prices, 75)
    iqr = q3 - q1
    if iqr == 0:
        return prices

    multiplier = (
        SERVICE_IQR_MULTIPLIER
        if pricing_mode == PricingMode.SERVICE
        else RETAIL_IQR_MULTIPLIER
    )
    lo = q1 - iqr * multiplier
    hi = q3 + iqr * multiplier
    filtered = [price for price in prices if lo <= price <= hi]
    if len(filtered) < MIN_RELIABLE_PRICES:
        return prices
    return filtered
