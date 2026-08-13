from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestSafety:
    def test_recommended_price_positive(self):
        result = generate_pricing(make_input(comparable_prices=uniform_prices(120, 5), raw_prices_found=5))
        assert result.recommended_price > 0

    def test_price_range_not_inverted(self):
        result = generate_pricing(make_input(comparable_prices=uniform_prices(120, 5), raw_prices_found=5))
        assert result.price_range_low <= result.price_range_high

    def test_recommended_within_range(self):
        result = generate_pricing(make_input(comparable_prices=uniform_prices(120, 5), raw_prices_found=5))
        assert result.price_range_low <= result.recommended_price <= result.price_range_high
