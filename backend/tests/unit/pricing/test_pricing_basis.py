from app.models.enums import PricingBasis
from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestPricingBasis:
    def test_under_five_is_baseline_driven(self):
        prices = uniform_prices(120, 4)
        result = generate_pricing(make_input(comparable_prices=prices, raw_prices_found=4))
        assert result.pricing_basis == PricingBasis.BASELINE_DRIVEN

    def test_five_to_ten_is_market_aligned(self):
        prices = uniform_prices(120, 7)
        result = generate_pricing(make_input(comparable_prices=prices, raw_prices_found=7))
        assert result.pricing_basis == PricingBasis.MARKET_ALIGNED

    def test_eleven_plus_is_market_driven(self):
        prices = uniform_prices(120, 12)
        result = generate_pricing(make_input(comparable_prices=prices, raw_prices_found=12))
        assert result.pricing_basis == PricingBasis.MARKET_DRIVEN
