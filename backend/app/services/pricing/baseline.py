from decimal import Decimal


def round_money(value: float) -> float:
    """Round a monetary value to two decimal places."""
    return round(value, 2)


def calc_baseline(cost: Decimal, target_margin: Decimal) -> float:
    """Calculate cost-plus baseline price.

    target_margin = 0 means baseline equals cost exactly.
    No minimum margin is applied.
    """
    cost_value = float(cost)
    margin_pct = float(target_margin)

    if margin_pct == 0:
        return round_money(cost_value)

    margin_rate = margin_pct / 100.0
    return round_money(cost_value / (1.0 - margin_rate))
