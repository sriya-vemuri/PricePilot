import math
from dataclasses import dataclass

from app.core.categories import CATEGORY_BOUNDS
from app.models.enums import BaselineStatus, Category, PricingMode
from app.services.pricing.constants import (
    RETAIL_MARKET_ABOVE_MULT,
    RETAIL_MARKET_BELOW_MULT,
    SERVICE_MARKET_ABOVE_MULT,
    SERVICE_MARKET_BELOW_MULT,
    MIN_MARKET_PRICES,
)


@dataclass(frozen=True)
class PlausibilityResult:
    baseline_status: BaselineStatus
    baseline_conflict: bool
    baseline_conflict_reason: str | None


def check_baseline_plausibility(
    *,
    baseline: float,
    filtered_low: float | None,
    filtered_high: float | None,
    filtered_count: int,
    category: Category,
    pricing_mode: PricingMode,
) -> PlausibilityResult:
    cat_min, cat_max = CATEGORY_BOUNDS.get(category, CATEGORY_BOUNDS[Category.OTHER])

    if baseline < cat_min:
        return PlausibilityResult(
            baseline_status=BaselineStatus.IMPLAUSIBLE,
            baseline_conflict=True,
            baseline_conflict_reason=(
                f"Baseline of ${baseline:.2f} is below the minimum realistic price "
                f"for this category (${cat_min:.2f})."
            ),
        )

    if baseline > cat_max:
        return PlausibilityResult(
            baseline_status=BaselineStatus.IMPLAUSIBLE,
            baseline_conflict=True,
            baseline_conflict_reason=(
                f"Baseline of ${baseline:.2f} exceeds the maximum realistic price "
                f"for this category (${cat_max:,.2f})."
            ),
        )

    if filtered_count >= MIN_MARKET_PRICES and filtered_high is not None:
        above_mult = (
            SERVICE_MARKET_ABOVE_MULT
            if pricing_mode == PricingMode.SERVICE
            else RETAIL_MARKET_ABOVE_MULT
        )
        below_mult = (
            SERVICE_MARKET_BELOW_MULT
            if pricing_mode == PricingMode.SERVICE
            else RETAIL_MARKET_BELOW_MULT
        )

        if baseline > filtered_high * above_mult:
            return PlausibilityResult(
                baseline_status=BaselineStatus.IMPLAUSIBLE,
                baseline_conflict=True,
                baseline_conflict_reason=(
                    f"Baseline of ${baseline:.2f} is more than {above_mult:g}× above the "
                    f"validated market high of ${filtered_high:.2f} — this cost-plus formula "
                    f"is not realistic for this market."
                ),
            )

        if filtered_low is not None and baseline < filtered_low * below_mult:
            return PlausibilityResult(
                baseline_status=BaselineStatus.IMPLAUSIBLE,
                baseline_conflict=True,
                baseline_conflict_reason=(
                    f"Baseline of ${baseline:.2f} is far below the validated market low of "
                    f"${filtered_low:.2f} — the stated cost is implausibly low for this product type."
                ),
            )

    return PlausibilityResult(
        baseline_status=BaselineStatus.PLAUSIBLE,
        baseline_conflict=False,
        baseline_conflict_reason=None,
    )


def category_log_midpoint(category: Category) -> float:
    """Geometric midpoint of the category sanity range."""
    cat_min, cat_max = CATEGORY_BOUNDS.get(category, CATEGORY_BOUNDS[Category.OTHER])
    return math.exp((math.log(cat_min) + math.log(cat_max)) / 2.0)
