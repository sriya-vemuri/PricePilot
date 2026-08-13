from decimal import Decimal

from app.models.enums import DemandLevel, MarketTrend, PricingMode, RecommendationMode, Strategy
from app.services.pricing.competitor_avg import MarketStats
from app.services.pricing.recommendation import RecommendationContext


def _demand_label(demand_level: DemandLevel) -> str:
    labels = {
        DemandLevel.VERY_LOW: "very low demand",
        DemandLevel.LOW: "low demand",
        DemandLevel.MODERATE: "moderate demand",
        DemandLevel.HIGH: "high demand",
        DemandLevel.VERY_HIGH: "very high demand",
    }
    return labels.get(demand_level, "moderate demand")


def _trend_label(market_trend: MarketTrend) -> str:
    labels = {
        MarketTrend.SURGING: "surging market",
        MarketTrend.GROWING: "growing market",
        MarketTrend.STABLE: "stable market",
        MarketTrend.DECLINING: "declining market",
    }
    return labels.get(market_trend, "stable market")


def _variance_label(price_variance: float | None) -> str:
    if price_variance is None:
        return "unknown variance"
    if price_variance <= 0.10:
        return "low variance"
    if price_variance <= 0.25:
        return "moderate variance"
    return "high variance"


def _signal_agreement_label(demand_level: DemandLevel, market_trend: MarketTrend) -> str:
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
        return "strong signal agreement"
    if strong_demand or strong_trend:
        return "partial signal agreement"
    return "limited signal agreement"


def build_confidence_explanation(
    *,
    confidence_score: int,
    market_stats: MarketStats,
    raw_prices_found: int,
    demand_level: DemandLevel,
    market_trend: MarketTrend,
    used_fallback: bool,
    sanity_triggered: bool,
    baseline_implausible: bool,
    pricing_mode: PricingMode,
) -> str:
    level = "High" if confidence_score >= 65 else "Medium" if confidence_score >= 42 else "Low"
    filtered_count = market_stats.filtered_count
    rejected = max(raw_prices_found - filtered_count, 0)
    data_label = "provider price" if pricing_mode == PricingMode.SERVICE else "comparable price"
    rejected_note = f", {rejected} price{'s' if rejected != 1 else ''} rejected" if rejected > 0 else ""

    if baseline_implausible:
        if filtered_count >= 3:
            return (
                f"{level} confidence ({confidence_score}): The user-provided baseline was evaluated and "
                f"found implausible for this market. Recommendation is based on {filtered_count} validated "
                f"{data_label}s{rejected_note} rather than the raw cost-plus formula."
            )
        return (
            f"{level} confidence ({confidence_score}): The user-provided baseline was evaluated and found "
            f"implausible for this market. Insufficient validated market data available — recommendation uses "
            f"a category-feasible estimate. Review cost and margin inputs."
        )

    if used_fallback or filtered_count < 3:
        return (
            f"{level} confidence ({confidence_score}): {filtered_count} {data_label}"
            f"{'s' if filtered_count != 1 else ''} found — below threshold. Market signals indicate "
            f"{_demand_label(demand_level)} and a {_trend_label(market_trend)}, but insufficient evidence "
            f"to justify adjustment. Recommendation is baseline-driven."
        )

    if sanity_triggered:
        return (
            f"{level} confidence ({confidence_score}): {filtered_count} {data_label}"
            f"{'s' if filtered_count != 1 else ''}{rejected_note} found, but market evidence was flagged as "
            f"inconsistent with expected pricing context. Demand and trend were not used as pricing drivers. "
            f"Recommendation conservatively adjusted toward baseline."
        )

    return (
        f"{level} confidence ({confidence_score}) based on {filtered_count} {data_label}"
        f"{'s' if filtered_count != 1 else ''}{rejected_note}, "
        f"{_variance_label(market_stats.price_variance)}, and "
        f"{_signal_agreement_label(demand_level, market_trend)}."
    )


def build_reasoning_summary(
    *,
    cost: Decimal,
    target_margin: Decimal,
    baseline: float,
    strategy: Strategy,
    pricing_mode: PricingMode,
    market_stats: MarketStats,
    demand_level: DemandLevel,
    market_trend: MarketTrend,
    recommendation: RecommendationContext,
    baseline_implausible: bool,
    baseline_conflict_reason: str | None,
    used_fallback: bool,
) -> str:
    margin_pct = float(target_margin)
    filtered_count = market_stats.filtered_count
    filtered_low = market_stats.filtered_low
    filtered_high = market_stats.filtered_high
    filtered_avg = market_stats.competitor_avg_price
    is_service = pricing_mode == PricingMode.SERVICE
    evidence_label = "market cost data point" if is_service else "comparable price"
    range_label = "provider cost range" if is_service else "competitor range"

    lines = [
        (
            f"Base cost: ${cost} | Target margin: {margin_pct:g}% | Implied baseline: "
            f"${baseline:.2f} (formula: ${cost} ÷ (1 − {margin_pct:g}%))."
        ),
        f"Recommendation mode: {recommendation.recommendation_mode.value.replace('_', ' ')}.",
    ]

    if baseline_implausible:
        lines.append(
            "The baseline price implied by the provided cost and margin appears unrealistic for this market "
            f"and is not a reliable pricing approach. {baseline_conflict_reason or ''}".strip()
        )
        if filtered_count >= 3 and filtered_low is not None and filtered_high is not None:
            avg_display = f" avg ${filtered_avg:.2f}," if filtered_avg else ""
            lines.append(
                f"A market-feasible range is more appropriate. Based on {filtered_count} validated "
                f"{evidence_label}s (range: ${filtered_low:.2f}–${filtered_high:.2f},{avg_display}) "
                f"the recommendation is anchored to market evidence rather than the raw baseline formula."
            )
        elif recommendation.recommendation_mode == RecommendationMode.FEASIBILITY_OVERRIDE:
            lines.append(
                "Insufficient validated market data is available to provide a market-based alternative. "
                "A feasible planning range has been estimated using category-level bounds."
            )
        lines.append(f"Final recommended price: ${recommendation.recommended_price:.2f}.")
        return " ".join(line for line in lines if line)

    if used_fallback or filtered_count < 3:
        lines.append(
            f"{filtered_count} {evidence_label}{'s' if filtered_count != 1 else ''} found — below the "
            f"3-source threshold. No {range_label} available."
        )
        lines.append(
            "Recommendation is based entirely on baseline cost and target margin. "
            "No demand or trend adjustments applied."
        )
        lines.append(
            f"Market signals ({_demand_label(demand_level)}, {_trend_label(market_trend)}) noted as "
            f"directional context only — not used as pricing drivers due to insufficient evidence."
        )
        lines.append(f"Final recommended price: ${recommendation.recommended_price:.2f}.")
        return " ".join(line for line in lines if line)

    if recommendation.sanity_triggered:
        avg_display = f" avg ${filtered_avg:.2f}," if filtered_avg else ""
        lines.append(
            f"{filtered_count} {evidence_label}s found (range: ${filtered_low:.2f}–${filtered_high:.2f},"
            f"{avg_display}), but the resulting price calculation was inconsistent with expected pricing context."
        )
        lines.append(
            "Market evidence was treated as low reliability. Demand and trend were not used as pricing drivers. "
            "Recommendation was adjusted conservatively toward the cost-based baseline."
        )
        lines.append(f"Final recommended price: ${recommendation.recommended_price:.2f}.")
        return " ".join(line for line in lines if line)

    if is_service:
        avg_display = f" typical cost ${filtered_avg:.2f}," if filtered_avg else ""
        lines.append(
            f"Estimated market treatment costs: ${filtered_low:.2f}–${filtered_high:.2f} "
            f"({avg_display}{filtered_count} provider cost data points)."
        )
    else:
        avg_display = f" avg ${filtered_avg:.2f}," if filtered_avg else ""
        lines.append(
            f"Filtered comparable market range: ${filtered_low:.2f}–${filtered_high:.2f} "
            f"({avg_display}{filtered_count} prices)."
        )

    if recommendation.demand_adjustment_applied:
        demand_notes = {
            DemandLevel.VERY_HIGH: "Demand is very high — upward adjustment applied.",
            DemandLevel.HIGH: "Demand is high — moderate upward adjustment applied.",
            DemandLevel.MODERATE: "Demand is moderate — no demand adjustment.",
            DemandLevel.LOW: "Demand is low — downward adjustment applied.",
            DemandLevel.VERY_LOW: "Demand is very low — conservative downward adjustment applied.",
        }
        lines.append(demand_notes.get(demand_level, "Demand signal: moderate — no adjustment."))

    if recommendation.trend_adjustment_applied:
        trend_notes = {
            MarketTrend.SURGING: "Market is surging — upward trend pressure incorporated.",
            MarketTrend.GROWING: "Market is growing — supports holding or modestly raising price.",
            MarketTrend.STABLE: "Market is stable — trend has neutral effect.",
            MarketTrend.DECLINING: "Market is declining — conservative adjustment applied.",
        }
        lines.append(trend_notes.get(market_trend, "Market trend: stable."))

    if strategy == Strategy.AGGRESSIVE:
        lines.append(
            "Aggressive strategy: price anchored toward the lower end of the market range to maximize volume."
            if not is_service
            else "Value strategy: recommendation anchored toward the lower end of the provider cost range."
        )
    elif strategy == Strategy.PREMIUM:
        lines.append(
            "Premium strategy: price anchored toward the upper end of the market range."
            if not is_service
            else "Premium strategy: recommendation anchored toward the upper end of the provider cost range."
        )
    else:
        lines.append(
            "Balanced strategy: price anchored near the midpoint of the market range."
            if not is_service
            else "Balanced strategy: recommendation anchored near the midpoint of the provider cost range."
        )

    lines.append(f"Final recommended price: ${recommendation.recommended_price:.2f}.")
    return " ".join(line for line in lines if line)
