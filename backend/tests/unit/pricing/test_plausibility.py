from decimal import Decimal

from app.models.enums import BaselineStatus, RecommendationMode
from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestPlausibility:
    def test_plausible_category_baseline(self):
        prices = uniform_prices(140, 5)
        result = generate_pricing(
            make_input(
                cost=Decimal("100"),
                target_margin=Decimal("30"),
                comparable_prices=prices,
                raw_prices_found=5,
            )
        )
        assert result.baseline_status == BaselineStatus.PLAUSIBLE
        assert result.baseline_conflict is False

    def test_category_implausibly_high(self):
        result = generate_pricing(
            make_input(
                cost=Decimal("300"),
                target_margin=Decimal("95"),
                comparable_prices=[],
            )
        )
        assert result.baseline_status == BaselineStatus.IMPLAUSIBLE
        assert result.baseline_conflict is True
        assert "exceeds the maximum" in (result.baseline_conflict_reason or "")

    def test_category_implausibly_low(self):
        result = generate_pricing(
            make_input(
                cost=Decimal("0.10"),
                target_margin=Decimal("0"),
                comparable_prices=[],
            )
        )
        assert result.baseline_status == BaselineStatus.IMPLAUSIBLE
        assert result.baseline_conflict is True

    def test_market_conflict_high(self):
        prices = uniform_prices(30, 5)
        result = generate_pricing(
            make_input(
                cost=Decimal("100"),
                target_margin=Decimal("30"),
                comparable_prices=prices,
                raw_prices_found=5,
            )
        )
        assert result.baseline_status == BaselineStatus.IMPLAUSIBLE
        assert "above the validated market high" in (result.baseline_conflict_reason or "")

    def test_market_conflict_low(self):
        prices = uniform_prices(500, 5)
        result = generate_pricing(
            make_input(
                cost=Decimal("50"),
                target_margin=Decimal("0"),
                comparable_prices=prices,
                raw_prices_found=5,
            )
        )
        assert result.baseline_status == BaselineStatus.IMPLAUSIBLE
        assert "below the validated market low" in (result.baseline_conflict_reason or "")
