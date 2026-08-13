from decimal import Decimal

import pytest

from app.core.stats import median
from app.models.responses import PricingInput
from app.services.pricing import generate_pricing
from app.services.pricing.competitor_avg import derive_market_stats
from app.models.enums import PricingMode
from tests.unit.pricing.conftest import make_input


class TestRegression:
    def test_margin_zero_never_becomes_30_percent(self):
        result = generate_pricing(make_input(target_margin=Decimal("0")))
        assert result.baseline_price == 100.0
        assert result.baseline_price != pytest.approx(142.86, abs=0.01)

    def test_valid_count_from_len_comparable_prices(self):
        prices = [100.0, 110.0, 120.0]
        stats = derive_market_stats(prices, baseline=142.86, pricing_mode=PricingMode.RETAIL)
        assert stats.filtered_count == 3

    def test_even_length_median_is_correct(self):
        assert median([100.0, 120.0, 140.0, 160.0]) == 130.0

    def test_pricing_input_has_no_filtered_prices_count_field(self):
        assert "filtered_prices_count" not in PricingInput.model_fields

    def test_no_negative_outlier_ratio_when_raw_below_filtered(self):
        result = generate_pricing(
            make_input(
                comparable_prices=[100.0, 110.0, 120.0],
                raw_prices_found=2,
            )
        )
        assert result.confidence_score >= 18
