import math
from collections.abc import Sequence


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Constrain `value` to the inclusive range [min_value, max_value]."""
    return max(min_value, min(max_value, value))


def median(values: Sequence[float]) -> float:
    """Return the median of `values`.

    For an even-length sequence, averages the two middle values after sorting.
    """
    if not values:
        raise ValueError("median() requires at least one value")

    sorted_values = sorted(values)
    count = len(sorted_values)
    midpoint = count // 2

    if count % 2 == 1:
        return float(sorted_values[midpoint])

    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2.0


def percentile(values: Sequence[float], p: float) -> float:
    """Return the linear-interpolated percentile of `values`.

    `p` is in [0, 100]. Uses the C=1 method (NumPy default): rank is
    (n - 1) * p / 100, with linear interpolation between adjacent values.
    """
    if not values:
        raise ValueError("percentile() requires at least one value")
    if p < 0 or p > 100:
        raise ValueError("percentile p must be between 0 and 100")

    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])

    rank = (len(sorted_values) - 1) * (p / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(sorted_values[int(rank)])

    weight = rank - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def coefficient_of_variation(values: Sequence[float] | None) -> float | None:
    """Population coefficient of variation (stdev / mean).

    Returns None when there are fewer than two values or when the mean is zero.
    Internal calculation is not rounded.
    """
    if values is None or len(values) < 2:
        return None

    count = len(values)
    mean = sum(values) / count
    if mean == 0:
        return None

    variance = sum((item - mean) ** 2 for item in values) / count
    stdev = variance ** 0.5
    return stdev / mean
