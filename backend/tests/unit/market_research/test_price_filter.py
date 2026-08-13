from app.models.enums import Category, PricingMode
from app.services.market_research.price_filter import filter_comparable_prices


def _filter(prices, **kwargs):
    return filter_comparable_prices(
        prices,
        baseline_price=kwargs.get("baseline_price", 100.0),
        category=kwargs.get("category", Category.ELECTRONICS),
        pricing_mode=kwargs.get("pricing_mode", PricingMode.RETAIL),
    )


class TestFiltering:
    def test_empty_input(self):
        result = _filter([])
        assert result.comparable_prices == []
        assert result.filtered_prices_count == 0
        assert result.raw_prices_found == 0
        assert result.outliers_removed == 0
        assert result.has_reliable_data is False
        assert result.competitor_price_1 is None

    def test_one_price(self):
        result = _filter([120.0])
        assert result.comparable_prices == [120.0]
        assert result.filtered_prices_count == 1
        assert result.has_reliable_data is False

    def test_two_prices(self):
        result = _filter([100.0, 140.0])
        assert result.filtered_prices_count == 2
        assert result.has_reliable_data is False

    def test_exactly_three(self):
        result = _filter([100.0, 120.0, 140.0])
        assert result.filtered_prices_count == 3
        assert result.has_reliable_data is True
        assert result.competitor_price_1 == 100.0
        assert result.competitor_price_2 == 120.0
        assert result.competitor_price_3 == 140.0

    def test_identical_prices_do_not_inflate_count(self):
        result = _filter([29.99, 29.99, 29.99])
        assert result.comparable_prices == [29.99]
        assert result.filtered_prices_count == 1
        assert result.has_reliable_data is False

    def test_huge_outlier_removed(self):
        result = _filter([100.0, 110.0, 120.0, 130.0, 140.0, 5000.0])
        assert 5000.0 not in result.comparable_prices
        assert result.outliers_removed >= 1
        assert result.filtered_prices_count == len(result.comparable_prices)

    def test_low_ticket_baseline_cap(self):
        result = _filter(
            [20.0, 22.0, 24.0, 400.0],
            baseline_price=30.0,
            category=Category.CLOTHING,
            pricing_mode=PricingMode.RETAIL,
        )
        assert 400.0 not in result.comparable_prices

    def test_health_beauty_allows_wider_baseline_multiple(self):
        prices = [180.0, 200.0, 220.0]
        clothing = _filter(
            prices,
            baseline_price=30.0,
            category=Category.CLOTHING,
            pricing_mode=PricingMode.RETAIL,
        )
        beauty = _filter(
            prices,
            baseline_price=30.0,
            category=Category.HEALTH_BEAUTY,
            pricing_mode=PricingMode.RETAIL,
        )
        assert clothing.comparable_prices == []
        assert 200.0 in beauty.comparable_prices

    def test_baseline_cap_skipped_when_baseline_missing(self):
        result = _filter(
            [380.0, 400.0, 420.0],
            baseline_price=None,
            category=Category.CLOTHING,
            pricing_mode=PricingMode.RETAIL,
        )
        assert result.comparable_prices == [380.0, 400.0, 420.0]

    def test_retail_vs_service_coarse_filtering(self):
        prices = [100.0, 110.0, 120.0, 500.0]
        retail = _filter(prices, pricing_mode=PricingMode.RETAIL, category=Category.ELECTRONICS)
        service = _filter(
            prices,
            pricing_mode=PricingMode.SERVICE,
            category=Category.SERVICES,
            baseline_price=None,
        )
        assert 500.0 not in retail.comparable_prices
        assert 500.0 in service.comparable_prices

    def test_iqr_filtering_large_sample(self):
        prices = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0, 400.0]
        result = _filter(prices)
        assert 400.0 not in result.comparable_prices
        assert result.filtered_prices_count >= 3

    def test_filtered_count_always_equals_len(self):
        for prices in ([], [10.0], [10.0, 20.0], [10.0, 20.0, 30.0], [8.0, 9.0, 10.0, 11.0, 12.0, 200.0]):
            result = _filter(prices)
            assert result.filtered_prices_count == len(result.comparable_prices)

    def test_outliers_removed_never_negative(self):
        result = _filter([50.0, 55.0, 60.0])
        assert result.outliers_removed >= 0


class TestMedianAndCompetitors:
    def test_even_size_comparable_set_uses_correct_median(self):
        result = _filter([100.0, 110.0, 130.0, 140.0])
        assert result.has_reliable_data is True
        assert result.competitor_price_2 == 120.0

    def test_fewer_than_three_competitors_are_none(self):
        result = _filter([100.0, 140.0])
        assert result.competitor_price_1 is None
        assert result.competitor_price_2 is None
        assert result.competitor_price_3 is None

    def test_three_plus_is_min_median_max(self):
        result = _filter([80.0, 100.0, 150.0])
        assert result.competitor_price_1 == 80.0
        assert result.competitor_price_2 == 100.0
        assert result.competitor_price_3 == 150.0
