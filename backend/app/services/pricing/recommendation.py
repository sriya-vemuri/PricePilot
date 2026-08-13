from dataclasses import dataclass

from app.core.stats import clamp
from app.models.enums import (
    DemandLevel,
    MarketTrend,
    PricingBasis,
    PricingMode,
    RecommendationMode,
    Strategy,
)
from app.services.pricing.baseline import round_money
from app.services.pricing.competitor_avg import MarketStats
from app.services.pricing.constants import (
    MIN_MARKET_PRICES,
    RETAIL_BLEND_SPREAD_TIGHT_10,
    RETAIL_BLEND_SPREAD_TIGHT_5,
    RETAIL_BLEND_WEIGHT_DEFAULT,
    RETAIL_BLEND_WEIGHT_TIGHT_10,
    RETAIL_BLEND_WEIGHT_TIGHT_5,
    RETAIL_DEMAND_ADJ,
    RETAIL_RANGE_PCT,
    RETAIL_SANITY,
    RETAIL_STRATEGY_POSITION,
    RETAIL_TREND_ADJ,
    SANITY_BLEND_BASELINE,
    SANITY_BLEND_CURRENT,
    SERVICE_BLEND_WEIGHT_5_PLUS,
    SERVICE_BLEND_WEIGHT_DEFAULT,
    SERVICE_DEMAND_ADJ,
    SERVICE_RANGE_PCT,
    SERVICE_SANITY,
    SERVICE_STRATEGY_POSITION,
    SERVICE_TREND_ADJ,
)
from app.services.pricing.plausibility import category_log_midpoint


@dataclass(frozen=True)
class RecommendationContext:
    recommended_price: float
    recommendation_mode: RecommendationMode
    sanity_triggered: bool
    demand_adjustment_applied: bool
    trend_adjustment_applied: bool


def calc_pricing_basis(filtered_count: int) -> PricingBasis:
    if filtered_count >= 11:
        return PricingBasis.MARKET_DRIVEN
    if filtered_count >= 5:
        return PricingBasis.MARKET_ALIGNED
    return PricingBasis.BASELINE_DRIVEN


def calc_price_range(recommended_price: float, strategy: Strategy, pricing_mode: PricingMode) -> tuple[float, float]:
    range_map = SERVICE_RANGE_PCT if pricing_mode == PricingMode.SERVICE else RETAIL_RANGE_PCT
    range_pct = range_map[strategy]
    low = round_money(recommended_price * (1.0 - range_pct))
    high = round_money(recommended_price * (1.0 + range_pct))

    if low > recommended_price:
        low = recommended_price
    if high < recommended_price:
        high = recommended_price

    return low, high


def calculate_recommendation(
    *,
    cost: float,
    baseline: float,
    strategy: Strategy,
    category,
    pricing_mode: PricingMode,
    market_stats: MarketStats,
    demand_level: DemandLevel,
    market_trend: MarketTrend,
    baseline_implausible: bool,
) -> RecommendationContext:
    filtered_count = market_stats.filtered_count
    filtered_low = market_stats.filtered_low
    filtered_high = market_stats.filtered_high
    competitor_avg = market_stats.competitor_avg_price

    if baseline_implausible:
        return _recommend_implausible(
            baseline=baseline,
            strategy=strategy,
            category=category,
            pricing_mode=pricing_mode,
            market_stats=market_stats,
        )

    if filtered_count < MIN_MARKET_PRICES:
        return RecommendationContext(
            recommended_price=max(round_money(baseline), round_money(cost)),
            recommendation_mode=RecommendationMode.BASELINE_LED,
            sanity_triggered=False,
            demand_adjustment_applied=False,
            trend_adjustment_applied=False,
        )

    if pricing_mode == PricingMode.SERVICE:
        return _recommend_service(
            cost=cost,
            baseline=baseline,
            strategy=strategy,
            filtered_low=filtered_low,
            filtered_high=filtered_high,
            competitor_avg=competitor_avg,
            filtered_count=filtered_count,
            demand_level=demand_level,
            market_trend=market_trend,
        )

    return _recommend_retail(
        cost=cost,
        baseline=baseline,
        strategy=strategy,
        filtered_low=filtered_low,
        filtered_high=filtered_high,
        competitor_avg=competitor_avg,
        filtered_count=filtered_count,
        demand_level=demand_level,
        market_trend=market_trend,
    )


def _strategy_anchor(
    *,
    strategy: Strategy,
    pricing_mode: PricingMode,
    filtered_low: float,
    filtered_high: float,
    competitor_avg: float | None,
) -> float:
    position_map = (
        SERVICE_STRATEGY_POSITION
        if pricing_mode == PricingMode.SERVICE
        else RETAIL_STRATEGY_POSITION
    )
    position = position_map[strategy]
    span = filtered_high - filtered_low

    if strategy == Strategy.BALANCED and competitor_avg is not None:
        return competitor_avg

    return filtered_low + span * position


def _retail_blend_weight(filtered_count: int, filtered_low: float, filtered_high: float) -> tuple[float, RecommendationMode]:
    spread = (filtered_high - filtered_low) / filtered_high if filtered_high > 0 else 1.0

    if filtered_count >= 10 and spread < RETAIL_BLEND_SPREAD_TIGHT_10:
        return RETAIL_BLEND_WEIGHT_TIGHT_10, RecommendationMode.MARKET_LED
    if filtered_count >= 5 and spread < RETAIL_BLEND_SPREAD_TIGHT_5:
        return RETAIL_BLEND_WEIGHT_TIGHT_5, RecommendationMode.MARKET_LED
    if filtered_count >= MIN_MARKET_PRICES:
        return RETAIL_BLEND_WEIGHT_DEFAULT, RecommendationMode.BASELINE_LED

    return 0.0, RecommendationMode.BASELINE_LED


def _recommend_implausible(
    *,
    baseline: float,
    strategy: Strategy,
    category,
    pricing_mode: PricingMode,
    market_stats: MarketStats,
) -> RecommendationContext:
    filtered_low = market_stats.filtered_low
    filtered_high = market_stats.filtered_high

    if (
        market_stats.filtered_count >= MIN_MARKET_PRICES
        and filtered_low is not None
        and filtered_high is not None
    ):
        anchor = _strategy_anchor(
            strategy=strategy,
            pricing_mode=pricing_mode,
            filtered_low=filtered_low,
            filtered_high=filtered_high,
            competitor_avg=market_stats.competitor_avg_price,
        )
        price = round_money(anchor)
        return RecommendationContext(
            recommended_price=price,
            recommendation_mode=RecommendationMode.MARKET_LED,
            sanity_triggered=False,
            demand_adjustment_applied=False,
            trend_adjustment_applied=False,
        )

    price = round_money(category_log_midpoint(category))
    return RecommendationContext(
        recommended_price=price,
        recommendation_mode=RecommendationMode.FEASIBILITY_OVERRIDE,
        sanity_triggered=False,
        demand_adjustment_applied=False,
        trend_adjustment_applied=False,
    )


def _recommend_retail(
    *,
    cost: float,
    baseline: float,
    strategy: Strategy,
    filtered_low: float | None,
    filtered_high: float | None,
    competitor_avg: float | None,
    filtered_count: int,
    demand_level: DemandLevel,
    market_trend: MarketTrend,
) -> RecommendationContext:
    assert filtered_low is not None and filtered_high is not None

    market_anchor = _strategy_anchor(
        strategy=strategy,
        pricing_mode=PricingMode.RETAIL,
        filtered_low=filtered_low,
        filtered_high=filtered_high,
        competitor_avg=competitor_avg,
    )
    blend_weight, recommendation_mode = _retail_blend_weight(filtered_count, filtered_low, filtered_high)
    price = baseline * (1.0 - blend_weight) + market_anchor * blend_weight

    demand_adj = RETAIL_DEMAND_ADJ[demand_level]
    trend_adj = RETAIL_TREND_ADJ[market_trend]
    price = price * (1.0 + demand_adj + trend_adj)

    price = _apply_retail_bounds(price, cost=cost, baseline=baseline, filtered_low=filtered_low, filtered_high=filtered_high)
    price = round_money(price)

    sanity_triggered = _sanity_triggered(
        price,
        baseline=baseline,
        filtered_low=filtered_low,
        filtered_high=filtered_high,
        pricing_mode=PricingMode.RETAIL,
    )
    if sanity_triggered:
        price = round_money(price * SANITY_BLEND_CURRENT + baseline * SANITY_BLEND_BASELINE)
        price = _apply_retail_bounds(price, cost=cost, baseline=baseline, filtered_low=filtered_low, filtered_high=filtered_high)
        price = round_money(price)

    return RecommendationContext(
        recommended_price=max(price, round_money(cost)),
        recommendation_mode=recommendation_mode,
        sanity_triggered=sanity_triggered,
        demand_adjustment_applied=not sanity_triggered,
        trend_adjustment_applied=not sanity_triggered,
    )


def _recommend_service(
    *,
    cost: float,
    baseline: float,
    strategy: Strategy,
    filtered_low: float | None,
    filtered_high: float | None,
    competitor_avg: float | None,
    filtered_count: int,
    demand_level: DemandLevel,
    market_trend: MarketTrend,
) -> RecommendationContext:
    assert filtered_low is not None and filtered_high is not None

    service_mid = competitor_avg if competitor_avg is not None else filtered_low + (filtered_high - filtered_low) * 0.5
    market_anchor = _strategy_anchor(
        strategy=strategy,
        pricing_mode=PricingMode.SERVICE,
        filtered_low=filtered_low,
        filtered_high=filtered_high,
        competitor_avg=service_mid if strategy == Strategy.BALANCED else competitor_avg,
    )

    blend_weight = SERVICE_BLEND_WEIGHT_5_PLUS if filtered_count >= 5 else SERVICE_BLEND_WEIGHT_DEFAULT
    price = baseline * (1.0 - blend_weight) + market_anchor * blend_weight

    demand_adj = SERVICE_DEMAND_ADJ[demand_level]
    trend_adj = SERVICE_TREND_ADJ[market_trend]
    price = price * (1.0 + demand_adj + trend_adj)

    price = _apply_service_bounds(price, cost=cost, baseline=baseline, filtered_high=filtered_high)
    price = round_money(price)

    sanity_triggered = _sanity_triggered(
        price,
        baseline=baseline,
        filtered_low=filtered_low,
        filtered_high=filtered_high,
        pricing_mode=PricingMode.SERVICE,
    )
    if sanity_triggered:
        price = round_money(price * SANITY_BLEND_CURRENT + baseline * SANITY_BLEND_BASELINE)
        price = _apply_service_bounds(price, cost=cost, baseline=baseline, filtered_high=filtered_high)
        price = round_money(price)

    recommendation_mode = (
        RecommendationMode.MARKET_LED
        if filtered_count >= 5
        else RecommendationMode.BASELINE_LED
    )
    return RecommendationContext(
        recommended_price=max(price, round_money(cost)),
        recommendation_mode=recommendation_mode,
        sanity_triggered=sanity_triggered,
        demand_adjustment_applied=not sanity_triggered,
        trend_adjustment_applied=not sanity_triggered,
    )


def _apply_retail_bounds(
    price: float,
    *,
    cost: float,
    baseline: float,
    filtered_low: float,
    filtered_high: float,
) -> float:
    lower_bound = max(cost, filtered_low * RETAIL_SANITY["below_market_low"])
    upper_bound = min(baseline * 2.0, filtered_high * 1.2)
    if upper_bound < lower_bound:
        upper_bound = max(lower_bound, baseline)
    return clamp(price, lower_bound, upper_bound)


def _apply_service_bounds(
    price: float,
    *,
    cost: float,
    baseline: float,
    filtered_high: float | None,
) -> float:
    lower_bound = max(cost, baseline * 0.5)
    if filtered_high is not None:
        upper_bound = min(baseline * 3.0, filtered_high * 1.3)
    else:
        upper_bound = baseline * 2.5
    if upper_bound < lower_bound:
        upper_bound = max(lower_bound, baseline)
    return clamp(price, lower_bound, upper_bound)


def _sanity_triggered(
    recommended_price: float,
    *,
    baseline: float,
    filtered_low: float | None,
    filtered_high: float | None,
    pricing_mode: PricingMode,
) -> bool:
    if filtered_low is None or filtered_high is None:
        return False

    thresholds = SERVICE_SANITY if pricing_mode == PricingMode.SERVICE else RETAIL_SANITY
    return (
        recommended_price > filtered_high * thresholds["above_market_high"]
        or recommended_price < filtered_low * thresholds["below_market_low"]
        or recommended_price > baseline * thresholds["above_baseline"]
    )
