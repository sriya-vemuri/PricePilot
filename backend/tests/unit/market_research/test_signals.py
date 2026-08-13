from app.models.enums import DemandLevel, MarketTrend
from app.services.market_research.signal_detector import build_summary, detect_demand, detect_trend


class TestTrendDetector:
    def test_booming_is_surging(self):
        assert detect_trend("The category is booming this year.") == MarketTrend.SURGING

    def test_growing(self):
        assert detect_trend("Unit sales are growing across retailers.") == MarketTrend.GROWING

    def test_declining(self):
        assert detect_trend("The segment is declining after last year.") == MarketTrend.DECLINING

    def test_mixed_positive_negative_is_stable(self):
        text = "Demand is growing in cities but declining in rural markets."
        assert detect_trend(text) == MarketTrend.STABLE

    def test_weak_or_empty_is_stable(self):
        assert detect_trend("") == MarketTrend.STABLE
        assert detect_trend("No clear directional language here.") == MarketTrend.STABLE

    def test_increasingly_does_not_match_increasing(self):
        assert detect_trend("The category is increasingly regulated.") == MarketTrend.STABLE


class TestDemandDetector:
    def test_very_high_demand(self):
        assert detect_demand("There is very high demand for this SKU.") == DemandLevel.VERY_HIGH

    def test_high_demand(self):
        assert detect_demand("Retailers report high demand this quarter.") == DemandLevel.HIGH

    def test_very_low_demand_not_low(self):
        assert detect_demand("There is very low demand in this niche.") == DemandLevel.VERY_LOW

    def test_low_demand(self):
        assert detect_demand("Stores see low demand outside holidays.") == DemandLevel.LOW

    def test_mixed_or_weak_is_moderate(self):
        assert detect_demand("") == DemandLevel.MODERATE
        assert detect_demand("high demand in cities but low demand elsewhere") == DemandLevel.MODERATE

    def test_slow_shipping_is_not_low_demand(self):
        assert detect_demand("Customers complained about slow shipping.") == DemandLevel.MODERATE


class TestSummaryBuilder:
    def test_joins_non_empty_parts(self):
        summary = build_summary("Around $20.", "Growing.", "High demand.")
        assert "Pricing: Around $20." in summary
        assert "Trend: Growing." in summary
        assert "Demand: High demand." in summary

    def test_skips_empty_parts(self):
        assert build_summary("Around $20.", None, "") == "Pricing: Around $20."
        assert build_summary(None, None, None) == ""
