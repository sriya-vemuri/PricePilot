from decimal import Decimal

from app.models.enums import RecommendationMode
from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestImplausibleBaseline:
    def test_three_market_prices_uses_market_led(self):
        prices = uniform_prices(30, 5)
        result = generate_pricing(
            make_input(
                cost=Decimal("100"),
                target_margin=Decimal("30"),
                comparable_prices=prices,
                raw_prices_found=5,
            )
        )
        assert result.recommendation_mode == RecommendationMode.MARKET_LED
        assert result.recommended_price < result.baseline_price

    def test_insufficient_market_data_uses_feasibility_override(self):
        result = generate_pricing(
            make_input(
                cost=Decimal("300"),
                target_margin=Decimal("95"),
                comparable_prices=[],
            )
        )
        assert result.recommendation_mode == RecommendationMode.FEASIBILITY_OVERRIDE
        assert result.recommended_price != result.baseline_price
