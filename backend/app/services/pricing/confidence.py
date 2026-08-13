from app.core.stats import clamp
from app.models.enums import DemandLevel, MarketTrend, PricingMode
from app.services.pricing.competitor_avg import MarketStats
from app.services.pricing.constants import CONFIDENCE_MAX, CONFIDENCE_MIN, MIN_MARKET_PRICES


def calc_confidence(
    *,
    market_stats: MarketStats,
    raw_prices_found: int,
    demand_level: DemandLevel,
    market_trend: MarketTrend,
    recommended_price: float,
    used_fallback: bool,
) -> int:
    filtered_count = market_stats.filtered_count
    filtered_low = market_stats.filtered_low
    filtered_high = market_stats.filtered_high
    filtered_avg = market_stats.competitor_avg_price
    price_variance = market_stats.price_variance

    if used_fallback or filtered_count < MIN_MARKET_PRICES:
        if raw_prices_found >= 2:
            return 26
        if raw_prices_found == 1:
            return 22
        return CONFIDENCE_MIN

    score = 30.0
    if filtered_count >= 10:
        score += 28
    elif filtered_count >= 5:
        score += 20
    elif filtered_count >= MIN_MARKET_PRICES:
        score += 10
    else:
        score += 4

    if raw_prices_found > filtered_count:
        outlier_ratio = (raw_prices_found - filtered_count) / raw_prices_found
        if outlier_ratio <= 0.1:
            score += 12
        elif outlier_ratio <= 0.3:
            score += 6
        else:
            score -= 6

    if price_variance is not None:
        if price_variance <= 0.10:
            score += 14
        elif price_variance <= 0.25:
            score += 7
        elif price_variance > 0.5:
            score -= 8
    elif filtered_avg and filtered_low and filtered_high:
        spread = (filtered_high - filtered_low) / filtered_avg
        if spread <= 0.15:
            score += 10
        elif spread <= 0.35:
            score += 5
        elif spread > 0.7:
            score -= 8

    strong_demand = demand_level in {
        DemandLevel.HIGH,
        DemandLevel.VERY_HIGH,
        DemandLevel.LOW,
        DemandLevel.VERY_LOW,
    }
    strong_trend = market_trend in {
        MarketTrend.GROWING,
        MarketTrend.SURGING,
        MarketTrend.DECLINING,
    }
    if strong_demand and strong_trend:
        score += 8
    elif strong_demand or strong_trend:
        score += 4

    if (
        filtered_low is not None
        and filtered_high is not None
        and filtered_low * 0.85 <= recommended_price <= filtered_high * 1.15
    ):
        score += 8
    elif filtered_low is not None and filtered_high is not None:
        score -= 8

    return int(clamp(score, CONFIDENCE_MIN, CONFIDENCE_MAX))
