import math

import pytest

from app.core.categories import get_pricing_mode
from app.core.stats import clamp, coefficient_of_variation, median, percentile
from app.models.enums import Category, PricingMode


def test_clamp_within_range() -> None:
    assert clamp(5, 0, 10) == 5


def test_clamp_below_min() -> None:
    assert clamp(-2, 0, 10) == 0


def test_clamp_above_max() -> None:
    assert clamp(99, 0, 10) == 10


def test_clamp_equal_to_bounds() -> None:
    assert clamp(0, 0, 10) == 0
    assert clamp(10, 0, 10) == 10


def test_median_odd_values() -> None:
    assert median([1, 3, 2]) == 2


def test_median_even_values() -> None:
    assert median([1, 2, 3, 4]) == 2.5
    assert median([4, 1, 3, 2]) == 2.5


def test_median_one_value() -> None:
    assert median([5]) == 5


def test_percentile_quartiles() -> None:
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile(values, 0) == 10.0
    assert percentile(values, 100) == 40.0
    assert percentile(values, 50) == pytest.approx(25.0)
    assert percentile(values, 25) == pytest.approx(17.5)


def test_percentile_single_value() -> None:
    assert percentile([8.0], 25) == 8.0
    assert percentile([8.0], 75) == 8.0


def test_coefficient_of_variation() -> None:
    values = [1.0, 2.0, 3.0]
    mean = 2.0
    variance = ((1 - 2) ** 2 + (2 - 2) ** 2 + (3 - 2) ** 2) / 3
    expected = math.sqrt(variance) / mean
    result = coefficient_of_variation(values)
    assert result is not None
    assert result == pytest.approx(expected)


def test_coefficient_of_variation_fewer_than_two_values() -> None:
    assert coefficient_of_variation([]) is None
    assert coefficient_of_variation([10.0]) is None
    assert coefficient_of_variation(None) is None


def test_coefficient_of_variation_zero_mean() -> None:
    assert coefficient_of_variation([-1.0, 1.0]) is None


def test_get_pricing_mode_services_is_service() -> None:
    assert get_pricing_mode(Category.SERVICES) == PricingMode.SERVICE


def test_get_pricing_mode_retail_categories() -> None:
    retail_categories = [
        Category.ELECTRONICS,
        Category.SOFTWARE,
        Category.CLOTHING,
        Category.FOOD_BEVERAGE,
        Category.HEALTH_BEAUTY,
        Category.HOME_GARDEN,
        Category.AUTOMOTIVE,
        Category.OTHER,
    ]
    for category in retail_categories:
        assert get_pricing_mode(category) == PricingMode.RETAIL
