from app.models.enums import Category, PricingMode
from app.services.market_research.query_builder import (
    build_demand_query,
    build_stage_queries,
    build_trend_query,
    retailer_domains_for,
    stage_trust,
)


PRODUCT = "Vitamin C Serum"


def _pricing_texts(stage: int, **kwargs) -> list[str]:
    queries = build_stage_queries(
        kwargs.get("product_name", PRODUCT),
        kwargs.get("category", Category.ELECTRONICS),
        kwargs.get("target_market", "United States"),
        kwargs.get("pricing_mode", PricingMode.RETAIL),
        stage=stage,
    )
    return [query.text for query in queries]


class TestQueryBuilder:
    def test_product_name_in_every_pricing_query(self):
        for stage in (1, 2, 3):
            for mode, category in (
                (PricingMode.RETAIL, Category.ELECTRONICS),
                (PricingMode.SERVICE, Category.SERVICES),
            ):
                queries = build_stage_queries(
                    PRODUCT,
                    category,
                    "United States",
                    mode,
                    stage=stage,
                )
                assert queries
                for query in queries:
                    assert PRODUCT in query.text

    def test_target_market_united_states_uses_us(self):
        texts = " ".join(_pricing_texts(1, category=Category.ELECTRONICS))
        assert "US" in texts or "United States" in texts

    def test_target_market_united_kingdom_not_hardcoded_us(self):
        queries = build_stage_queries(
            PRODUCT,
            Category.ELECTRONICS,
            "United Kingdom",
            PricingMode.RETAIL,
            stage=1,
        )
        joined = " ".join(query.text for query in queries)
        assert "United Kingdom" in joined or "UK" in joined
        assert " US" not in f" {joined} "
        assert "United States" not in joined

    def test_electronics_uses_expected_retailer_domains(self):
        domains = retailer_domains_for(Category.ELECTRONICS)
        assert domains == (
            "amazon.com",
            "bestbuy.com",
            "walmart.com",
            "target.com",
            "newegg.com",
        )
        queries = build_stage_queries(
            PRODUCT,
            Category.ELECTRONICS,
            "United States",
            PricingMode.RETAIL,
            stage=1,
        )
        for query in queries:
            assert query.include_domains == domains

    def test_health_beauty_uses_expected_domains(self):
        domains = retailer_domains_for(Category.HEALTH_BEAUTY)
        assert "sephora.com" in domains
        assert "ulta.com" in domains
        assert "dermstore.com" in domains

    def test_services_do_not_use_retailer_domains(self):
        for stage in (1, 2, 3):
            queries = build_stage_queries(
                "Facial",
                Category.SERVICES,
                "United States",
                PricingMode.SERVICE,
                stage=stage,
            )
            for query in queries:
                assert query.include_domains == ()

    def test_trend_and_demand_queries_have_no_domain_restrictions(self):
        trend = build_trend_query(PRODUCT, Category.ELECTRONICS, "United Kingdom")
        demand = build_demand_query(PRODUCT, Category.ELECTRONICS, "United Kingdom")
        assert trend.include_domains == ()
        assert demand.include_domains == ()
        assert trend.query_kind == "trend"
        assert demand.query_kind == "demand"
        assert "United Kingdom" in trend.text
        assert "United Kingdom" in demand.text
        assert PRODUCT in trend.text
        assert PRODUCT in demand.text

    def test_stage3_still_contains_product_name(self):
        texts = _pricing_texts(3, category=Category.HEALTH_BEAUTY)
        assert texts
        for text in texts:
            assert PRODUCT in text
            assert text.strip() != "health beauty price US"

    def test_beauty_stage2_does_not_duplicate_stage1_sephora_ulta(self):
        stage1 = build_stage_queries(
            PRODUCT,
            Category.HEALTH_BEAUTY,
            "United States",
            PricingMode.RETAIL,
            stage=1,
        )
        stage2 = build_stage_queries(
            PRODUCT,
            Category.HEALTH_BEAUTY,
            "United States",
            PricingMode.RETAIL,
            stage=2,
        )
        stage1_beauty = {
            query.text.lower()
            for query in stage1
            if "sephora" in query.text.lower() or "ulta" in query.text.lower()
        }
        stage2_texts = {query.text.lower() for query in stage2}
        assert stage2_texts
        assert not stage2_texts.issubset(stage1_beauty)
        assert not all("sephora" in text or "ulta" in text for text in stage2_texts)

    def test_stage3_trust_is_low(self):
        queries = build_stage_queries(
            PRODUCT,
            Category.ELECTRONICS,
            "United States",
            PricingMode.RETAIL,
            stage=3,
        )
        assert all(query.trust == "low" for query in queries)
        assert stage_trust(1) == "high"
        assert stage_trust(2) == "medium"
        assert stage_trust(3) == "low"
