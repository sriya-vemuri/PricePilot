from app.models.enums import Strategy
from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestStrategies:
    def test_aggressive_less_than_balanced_less_than_premium(self):
        prices = uniform_prices(120, 5, spread=0.10)
        base_kwargs = {"comparable_prices": prices, "raw_prices_found": 5}

        aggressive = generate_pricing(make_input(strategy=Strategy.AGGRESSIVE, **base_kwargs))
        balanced = generate_pricing(make_input(strategy=Strategy.BALANCED, **base_kwargs))
        premium = generate_pricing(make_input(strategy=Strategy.PREMIUM, **base_kwargs))

        assert aggressive.recommended_price < balanced.recommended_price < premium.recommended_price
