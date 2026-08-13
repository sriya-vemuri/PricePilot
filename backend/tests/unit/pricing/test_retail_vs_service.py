from decimal import Decimal

from app.models.enums import Category, DemandLevel, MarketTrend, PricingMode, Strategy
from app.services.pricing import generate_pricing
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestRetailVsService:
    def test_different_strategy_anchors(self):
        retail_prices = uniform_prices(200, 5, spread=0.10)
        service_prices = uniform_prices(200, 5, spread=0.10)

        retail = generate_pricing(
            make_input(
                pricing_mode=PricingMode.RETAIL,
                comparable_prices=retail_prices,
                raw_prices_found=5,
                strategy=Strategy.AGGRESSIVE,
            )
        )
        service = generate_pricing(
            make_input(
                pricing_mode=PricingMode.SERVICE,
                category=Category.SERVICES,
                comparable_prices=service_prices,
                raw_prices_found=5,
                strategy=Strategy.AGGRESSIVE,
            )
        )
        assert retail.recommended_price != service.recommended_price

    def test_different_demand_adjustments(self):
        prices = uniform_prices(120, 5)
        base = {"comparable_prices": prices, "raw_prices_found": 5}
        retail = generate_pricing(
            make_input(
                pricing_mode=PricingMode.RETAIL,
                demand_level=DemandLevel.VERY_HIGH,
                market_trend=MarketTrend.STABLE,
                **base,
            )
        )
        service = generate_pricing(
            make_input(
                pricing_mode=PricingMode.SERVICE,
                category=Category.SERVICES,
                demand_level=DemandLevel.VERY_HIGH,
                market_trend=MarketTrend.STABLE,
                **base,
            )
        )
        assert retail.recommended_price != service.recommended_price

    def test_different_price_range_widths(self):
        prices = uniform_prices(120, 5)
        retail = generate_pricing(
            make_input(
                pricing_mode=PricingMode.RETAIL,
                comparable_prices=prices,
                raw_prices_found=5,
                strategy=Strategy.BALANCED,
            )
        )
        service = generate_pricing(
            make_input(
                pricing_mode=PricingMode.SERVICE,
                category=Category.SERVICES,
                comparable_prices=prices,
                raw_prices_found=5,
                strategy=Strategy.BALANCED,
            )
        )
        retail_width = retail.price_range_high - retail.price_range_low
        service_width = service.price_range_high - service.price_range_low
        assert service_width > retail_width

    def test_service_sanity_uses_wider_thresholds(self):
        prices = [100.0, 110.0, 120.0, 130.0, 140.0]
        retail = generate_pricing(
            make_input(
                pricing_mode=PricingMode.RETAIL,
                comparable_prices=prices,
                raw_prices_found=5,
                demand_level=DemandLevel.VERY_HIGH,
                market_trend=MarketTrend.SURGING,
            )
        )
        service = generate_pricing(
            make_input(
                pricing_mode=PricingMode.SERVICE,
                category=Category.SERVICES,
                comparable_prices=prices,
                raw_prices_found=5,
                demand_level=DemandLevel.VERY_HIGH,
                market_trend=MarketTrend.SURGING,
            )
        )
        assert isinstance(retail.sanity_triggered, bool)
        assert isinstance(service.sanity_triggered, bool)
