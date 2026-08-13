"""Pure Python pricing engine — no HTTP, DB, or Tavily dependencies."""

from app.models.enums import BaselineStatus
from app.models.responses import PricingInput, PricingResult
from app.services.pricing.baseline import calc_baseline
from app.services.pricing.competitor_avg import derive_market_stats
from app.services.pricing.confidence import calc_confidence
from app.services.pricing.plausibility import check_baseline_plausibility
from app.services.pricing.reasoning import build_confidence_explanation, build_reasoning_summary
from app.services.pricing.recommendation import (
    calc_price_range,
    calc_pricing_basis,
    calculate_recommendation,
)


def generate_pricing(input: PricingInput) -> PricingResult:
    """Run the full pricing pipeline and return a structured result."""
    cost = float(input.cost)
    baseline = calc_baseline(input.cost, input.target_margin)

    market_stats = derive_market_stats(
        input.comparable_prices,
        baseline,
        input.pricing_mode,
    )

    plausibility = check_baseline_plausibility(
        baseline=baseline,
        filtered_low=market_stats.filtered_low,
        filtered_high=market_stats.filtered_high,
        filtered_count=market_stats.filtered_count,
        category=input.category,
        pricing_mode=input.pricing_mode,
    )

    baseline_implausible = plausibility.baseline_status == BaselineStatus.IMPLAUSIBLE

    recommendation = calculate_recommendation(
        cost=cost,
        baseline=baseline,
        strategy=input.strategy,
        category=input.category,
        pricing_mode=input.pricing_mode,
        market_stats=market_stats,
        demand_level=input.demand_level,
        market_trend=input.market_trend,
        baseline_implausible=baseline_implausible,
    )

    pricing_basis = calc_pricing_basis(market_stats.filtered_count)
    price_range_low, price_range_high = calc_price_range(
        recommendation.recommended_price,
        input.strategy,
        input.pricing_mode,
    )

    confidence_score = calc_confidence(
        market_stats=market_stats,
        raw_prices_found=input.raw_prices_found,
        demand_level=input.demand_level,
        market_trend=input.market_trend,
        recommended_price=recommendation.recommended_price,
        used_fallback=market_stats.used_fallback,
    )

    confidence_explanation = build_confidence_explanation(
        confidence_score=confidence_score,
        market_stats=market_stats,
        raw_prices_found=input.raw_prices_found,
        demand_level=input.demand_level,
        market_trend=input.market_trend,
        used_fallback=market_stats.used_fallback,
        sanity_triggered=recommendation.sanity_triggered,
        baseline_implausible=baseline_implausible,
        pricing_mode=input.pricing_mode,
    )

    reasoning_summary = build_reasoning_summary(
        cost=input.cost,
        target_margin=input.target_margin,
        baseline=baseline,
        strategy=input.strategy,
        pricing_mode=input.pricing_mode,
        market_stats=market_stats,
        demand_level=input.demand_level,
        market_trend=input.market_trend,
        recommendation=recommendation,
        baseline_implausible=baseline_implausible,
        baseline_conflict_reason=plausibility.baseline_conflict_reason,
        used_fallback=market_stats.used_fallback,
    )

    return PricingResult(
        baseline_price=baseline,
        recommended_price=recommendation.recommended_price,
        price_range_low=price_range_low,
        price_range_high=price_range_high,
        confidence_score=confidence_score,
        confidence_explanation=confidence_explanation,
        pricing_basis=pricing_basis,
        recommendation_mode=recommendation.recommendation_mode,
        reasoning_summary=reasoning_summary,
        competitor_avg_price=market_stats.competitor_avg_price,
        competitor_avg_status=market_stats.competitor_avg_status,
        price_variance=market_stats.price_variance,
        sanity_triggered=recommendation.sanity_triggered,
        baseline_status=plausibility.baseline_status,
        baseline_conflict=plausibility.baseline_conflict,
        baseline_conflict_reason=plausibility.baseline_conflict_reason,
        used_fallback=market_stats.used_fallback,
    )
