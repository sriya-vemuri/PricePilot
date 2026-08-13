from decimal import Decimal

import pytest

from app.models.enums import BaselineStatus, PricingMode, Strategy
from app.services.pricing.baseline import calc_baseline
from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestBaseline:
    def test_margin_30(self):
        assert calc_baseline(Decimal("100"), Decimal("30")) == pytest.approx(142.86, abs=0.01)

    def test_margin_zero_equals_cost(self):
        assert calc_baseline(Decimal("100"), Decimal("0")) == 100.0

    def test_margin_95_high_baseline(self):
        baseline = calc_baseline(Decimal("100"), Decimal("95"))
        assert baseline == 2000.0

    def test_generate_pricing_baseline_field(self):
        result = generate_pricing(make_input(target_margin=Decimal("30")))
        assert result.baseline_price == pytest.approx(142.86, abs=0.01)

    def test_margin_zero_recommendation_is_cost_without_market(self):
        result = generate_pricing(make_input(target_margin=Decimal("0")))
        assert result.baseline_price == 100.0
        assert result.recommended_price == 100.0
