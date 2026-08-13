from app.models.enums import Category, PricingMode
from app.services.market_research.models import PriceSource
from app.services.market_research.price_extractor import deduplicate_prices, extract_prices


def _prices(text: str, **kwargs) -> list[float]:
    extracted = extract_prices(
        text,
        category=kwargs.get("category", Category.ELECTRONICS),
        pricing_mode=kwargs.get("pricing_mode", PricingMode.RETAIL),
    )
    return [item.price for item in extracted]


class TestPriceExtraction:
    def test_dollar_formats(self):
        text = "Buy now $12 and $ 12 plus $1,299 or $1,299.99 in stock."
        prices = _prices(text)
        assert 12.0 in prices
        assert 1299.0 in prices
        assert 1299.99 in prices

    def test_rejects_eur_gbp_inr_context(self):
        assert _prices("Listed at $49 EUR equivalent") == []
        assert _prices("Price $49 (£40 GBP)") == []
        assert _prices("Costs $49 INR ₹") == []
        assert _prices("About $49 CAD") == []
        assert _prices("Ticket $49 AUD") == []

    def test_rejects_market_size_and_tam(self):
        assert _prices("The TAM is $12 billion") == []
        assert _prices("Market size reached $5 million") == []
        assert _prices("Industry revenue of $1,299.99 last year") == []

    def test_rejects_identifiable_shipping_fees(self):
        assert _prices("Shipping fee $5.99") == []
        assert _prices("Add a delivery fee $8") == []

    def test_retailer_name_alone_is_not_product_page(self):
        extracted = extract_prices(
            "Amazon mentioned a $49 figure in an editorial recap.",
            category=Category.ELECTRONICS,
            pricing_mode=PricingMode.RETAIL,
        )
        assert extracted
        assert extracted[0].source == PriceSource.EDITORIAL

    def test_purchase_context_is_product_page(self):
        extracted = extract_prices(
            "Add to cart $49.00 — in stock.",
            category=Category.ELECTRONICS,
            pricing_mode=PricingMode.RETAIL,
        )
        assert extracted[0].source == PriceSource.PRODUCT_PAGE


class TestServiceExtraction:
    def test_very_small_unrelated_price_rejected(self):
        prices = _prices(
            "A blog mentioned $5 as a round number in passing.",
            category=Category.SERVICES,
            pricing_mode=PricingMode.SERVICE,
        )
        assert prices == []

    def test_valid_per_session_price_accepted(self):
        prices = _prices(
            "The clinic charges $5 per session.",
            category=Category.SERVICES,
            pricing_mode=PricingMode.SERVICE,
        )
        assert 5.0 in prices


class TestDeduplication:
    def test_repeated_price_becomes_one_observation(self):
        text = "In stock $29.99. Add to cart $29.99. Buy now $29.99."
        extracted = extract_prices(
            text,
            category=Category.ELECTRONICS,
            pricing_mode=PricingMode.RETAIL,
        )
        deduped = deduplicate_prices(extracted)
        assert [item.price for item in deduped] == [29.99]

    def test_cents_handled_correctly(self):
        extracted = extract_prices(
            "Buy now $10 and $10.00 and $10.0 in stock.",
            category=Category.ELECTRONICS,
            pricing_mode=PricingMode.RETAIL,
        )
        deduped = deduplicate_prices(extracted)
        assert [item.price for item in deduped] == [10.0]
