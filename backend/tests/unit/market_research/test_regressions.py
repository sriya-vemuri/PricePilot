import inspect

from app.models.enums import Category, PricingMode
from app.services.market_research.price_extractor import deduplicate_prices, extract_prices
from app.services.market_research.price_filter import filter_comparable_prices
from app.services.market_research.query_builder import build_stage_queries, stage_trust
from app.services.pricing import engine as pricing_engine
from app.services.pricing import competitor_avg, recommendation


class TestRegressions:
    def test_duplicate_snippets_do_not_inflate_valid_count(self):
        text = "Buy now $29.99. Add to cart $29.99. In stock $29.99."
        extracted = extract_prices(
            text,
            category=Category.ELECTRONICS,
            pricing_mode=PricingMode.RETAIL,
        )
        deduped = deduplicate_prices(extracted)
        result = filter_comparable_prices(
            deduped,
            baseline_price=25.0,
            category=Category.ELECTRONICS,
            pricing_mode=PricingMode.RETAIL,
        )
        assert result.raw_prices_found == 1
        assert result.filtered_prices_count == 1

    def test_stage3_trust_is_low(self):
        queries = build_stage_queries(
            "Widget",
            Category.ELECTRONICS,
            "United States",
            PricingMode.RETAIL,
            stage=3,
        )
        assert stage_trust(3) == "low"
        assert all(query.trust == "low" for query in queries)

    def test_no_negative_outlier_counts(self):
        result = filter_comparable_prices(
            [10.0, 12.0, 11.0],
            baseline_price=10.0,
            category=Category.ELECTRONICS,
            pricing_mode=PricingMode.RETAIL,
        )
        assert result.outliers_removed >= 0
        assert result.filtered_prices_count == len(result.comparable_prices)

    def test_even_median_is_correct(self):
        result = filter_comparable_prices(
            [10.0, 20.0, 30.0, 40.0],
            baseline_price=25.0,
            category=Category.ELECTRONICS,
            pricing_mode=PricingMode.RETAIL,
        )
        assert result.competitor_price_2 == 25.0

    def test_pricing_engine_does_not_perform_iqr_filtering(self):
        source = (
            inspect.getsource(pricing_engine)
            + inspect.getsource(competitor_avg)
            + inspect.getsource(recommendation)
        )
        lowered = source.lower()
        assert "iqr" not in lowered
        assert "quartile" not in lowered
        assert "percentile(" not in source
