from decimal import Decimal

import pytest

from app.models.enums import CompetitorAvgStatus, PricingBasis, RecommendationMode
from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestMarketCount:
    @pytest.mark.parametrize("count", [0, 1, 2])
    def test_insufficient_prices_use_fallback(self, count):
        prices = uniform_prices(120, count)
        result = generate_pricing(
            make_input(
                comparable_prices=prices,
                raw_prices_found=count,
            )
        )
        assert result.used_fallback is True
        assert result.competitor_avg_status == CompetitorAvgStatus.UNAVAILABLE_INSUFFICIENT_DATA
        assert result.recommendation_mode == RecommendationMode.BASELINE_LED
        assert result.recommended_price == pytest.approx(result.baseline_price, abs=0.01)

    def test_exactly_three_prices_enables_market_blend(self):
        prices = uniform_prices(120, 3)
        result = generate_pricing(
            make_input(comparable_prices=prices, raw_prices_found=3)
        )
        assert result.used_fallback is False
        assert result.competitor_avg_status == CompetitorAvgStatus.AVAILABLE
        assert result.recommended_price != result.baseline_price

    def test_five_prices_market_aligned_basis(self):
        prices = uniform_prices(120, 5, spread=0.08)
        result = generate_pricing(
            make_input(comparable_prices=prices, raw_prices_found=5)
        )
        assert result.pricing_basis == PricingBasis.MARKET_ALIGNED

    def test_eleven_prices_market_driven_basis(self):
        prices = uniform_prices(120, 11, spread=0.06)
        result = generate_pricing(
            make_input(comparable_prices=prices, raw_prices_found=11)
        )
        assert result.pricing_basis == PricingBasis.MARKET_DRIVEN

    def test_filtered_count_from_comparable_prices_only(self):
        prices = uniform_prices(120, 5)
        result = generate_pricing(
            make_input(
                comparable_prices=prices,
                raw_prices_found=20,
            )
        )
        assert result.pricing_basis == PricingBasis.MARKET_ALIGNED
