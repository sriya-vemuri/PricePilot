from decimal import Decimal

from app.models.enums import DemandLevel, MarketTrend
from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestDemandTrend:
    def test_very_high_surging_increases_price(self):
        prices = uniform_prices(120, 5)
        base = {
            "comparable_prices": prices,
            "raw_prices_found": 5,
        }
        neutral = generate_pricing(
            make_input(
                demand_level=DemandLevel.MODERATE,
                market_trend=MarketTrend.STABLE,
                **base,
            )
        )
        boosted = generate_pricing(
            make_input(
                demand_level=DemandLevel.VERY_HIGH,
                market_trend=MarketTrend.SURGING,
                **base,
            )
        )
        assert boosted.recommended_price > neutral.recommended_price

    def test_very_low_declining_decreases_price(self):
        prices = uniform_prices(120, 5)
        base = {
            "comparable_prices": prices,
            "raw_prices_found": 5,
        }
        neutral = generate_pricing(
            make_input(
                demand_level=DemandLevel.MODERATE,
                market_trend=MarketTrend.STABLE,
                **base,
            )
        )
        reduced = generate_pricing(
            make_input(
                demand_level=DemandLevel.VERY_LOW,
                market_trend=MarketTrend.DECLINING,
                **base,
            )
        )
        assert reduced.recommended_price < neutral.recommended_price

    def test_fewer_than_three_prices_signals_do_not_modify_baseline(self):
        prices = uniform_prices(120, 2)
        base = {
            "comparable_prices": prices,
            "raw_prices_found": 2,
        }
        neutral = generate_pricing(
            make_input(
                demand_level=DemandLevel.MODERATE,
                market_trend=MarketTrend.STABLE,
                **base,
            )
        )
        extreme = generate_pricing(
            make_input(
                demand_level=DemandLevel.VERY_HIGH,
                market_trend=MarketTrend.SURGING,
                **base,
            )
        )
        assert extreme.recommended_price == neutral.recommended_price
        assert "not used as pricing drivers" in extreme.reasoning_summary.lower()
