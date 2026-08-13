from app.services.pricing import generate_pricing
from app.services.pricing.confidence import calc_confidence
from app.services.pricing.competitor_avg import derive_market_stats
from app.models.enums import DemandLevel, MarketTrend, PricingMode
from tests.unit.pricing.conftest import make_input, uniform_prices


class TestConfidence:
    def test_no_market_data_gives_low_confidence(self):
        result = generate_pricing(make_input(comparable_prices=[], raw_prices_found=0))
        assert result.confidence_score <= 30

    def test_larger_clean_sample_gives_higher_confidence(self):
        small = generate_pricing(
            make_input(comparable_prices=uniform_prices(120, 3), raw_prices_found=3)
        )
        large = generate_pricing(
            make_input(comparable_prices=uniform_prices(120, 11, spread=0.05), raw_prices_found=11)
        )
        assert large.confidence_score > small.confidence_score

    def test_noisy_sample_gives_lower_confidence(self):
        tight = generate_pricing(
            make_input(comparable_prices=uniform_prices(120, 8, spread=0.02), raw_prices_found=8)
        )
        noisy = generate_pricing(
            make_input(
                comparable_prices=[80.0, 95.0, 120.0, 150.0, 180.0, 210.0, 240.0, 280.0],
                raw_prices_found=8,
            )
        )
        assert noisy.confidence_score < tight.confidence_score

    def test_never_exceeds_88(self):
        result = generate_pricing(
            make_input(
                comparable_prices=uniform_prices(120, 15, spread=0.02),
                raw_prices_found=15,
                demand_level=DemandLevel.VERY_HIGH,
                market_trend=MarketTrend.SURGING,
            )
        )
        assert result.confidence_score <= 88

    def test_raw_lower_than_filtered_does_not_break_confidence(self):
        market_stats = derive_market_stats([100.0, 110.0, 120.0], baseline=142.86, pricing_mode=PricingMode.RETAIL)
        score = calc_confidence(
            market_stats=market_stats,
            raw_prices_found=2,
            demand_level=DemandLevel.MODERATE,
            market_trend=MarketTrend.STABLE,
            recommended_price=115.0,
            used_fallback=False,
        )
        assert 18 <= score <= 88
