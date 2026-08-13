from dataclasses import dataclass

from app.core.stats import coefficient_of_variation, median
from app.models.enums import CompetitorAvgStatus, PricingMode
from app.services.pricing.baseline import round_money
from app.services.pricing.constants import (
    MIN_PRICES_FOR_COMPETITOR_AVG,
    MIN_PRICES_FOR_SUPPRESSED_MEDIAN,
    NEAR_BASELINE_PCT,
    TIGHT_CV_THRESHOLD,
)


@dataclass(frozen=True)
class MarketStats:
    comparable_prices: list[float]
    filtered_count: int
    filtered_low: float | None
    filtered_high: float | None
    mean: float | None
    median_value: float | None
    price_variance: float | None
    competitor_avg_price: float | None
    competitor_avg_status: CompetitorAvgStatus
    used_fallback: bool


def derive_market_stats(
    comparable_prices: list[float],
    baseline: float,
    pricing_mode: PricingMode,
) -> MarketStats:
    """Derive market statistics from already-cleaned comparable prices."""
    prices = sorted(price for price in comparable_prices if price > 0)
    filtered_count = len(prices)
    used_fallback = filtered_count < MIN_PRICES_FOR_COMPETITOR_AVG

    if used_fallback:
        return MarketStats(
            comparable_prices=prices,
            filtered_count=filtered_count,
            filtered_low=None,
            filtered_high=None,
            mean=None,
            median_value=median(prices) if prices else None,
            price_variance=coefficient_of_variation(prices),
            competitor_avg_price=None,
            competitor_avg_status=CompetitorAvgStatus.UNAVAILABLE_INSUFFICIENT_DATA,
            used_fallback=True,
        )

    filtered_low = prices[0]
    filtered_high = prices[-1]
    mean = sum(prices) / filtered_count
    median_value = median(prices)
    price_variance = coefficient_of_variation(prices)

    avg_price, avg_status = _calc_competitor_avg(prices, mean, median_value, price_variance, baseline, pricing_mode)

    return MarketStats(
        comparable_prices=prices,
        filtered_count=filtered_count,
        filtered_low=filtered_low,
        filtered_high=filtered_high,
        mean=mean,
        median_value=median_value,
        price_variance=price_variance,
        competitor_avg_price=avg_price,
        competitor_avg_status=avg_status,
        used_fallback=False,
    )


def _calc_competitor_avg(
    prices: list[float],
    mean: float,
    median_value: float,
    price_variance: float | None,
    baseline: float,
    pricing_mode: PricingMode,
) -> tuple[float | None, CompetitorAvgStatus]:
    if len(prices) < MIN_PRICES_FOR_COMPETITOR_AVG:
        return None, CompetitorAvgStatus.UNAVAILABLE_INSUFFICIENT_DATA

    if pricing_mode == PricingMode.SERVICE:
        return round_money(mean), CompetitorAvgStatus.AVAILABLE

    if baseline > 0:
        diff_from_baseline = abs(mean - baseline) / baseline
        if diff_from_baseline < NEAR_BASELINE_PCT:
            if len(prices) < MIN_PRICES_FOR_SUPPRESSED_MEDIAN:
                return None, CompetitorAvgStatus.UNAVAILABLE_SUPPRESSED_NEAR_BASELINE
            if price_variance is not None and price_variance < TIGHT_CV_THRESHOLD:
                return round_money(median_value), CompetitorAvgStatus.AVAILABLE

    return round_money(mean), CompetitorAvgStatus.AVAILABLE
