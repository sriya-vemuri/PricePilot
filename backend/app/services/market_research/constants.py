"""Centralized market-research constants.

Domain lists and filter multipliers live here so query building and
price filtering share a single source of truth.
"""

from app.models.enums import Category

# Retailer domains used only for retail product-price searches.
# Trend/demand queries never use these restrictions.
RETAILER_DOMAINS_BY_CATEGORY: dict[Category, tuple[str, ...]] = {
    Category.HEALTH_BEAUTY: (
        "sephora.com",
        "ulta.com",
        "amazon.com",
        "walmart.com",
        "target.com",
        "dermstore.com",
    ),
    Category.CLOTHING: (
        "amazon.com",
        "walmart.com",
        "target.com",
        "macys.com",
        "nordstrom.com",
    ),
    Category.ELECTRONICS: (
        "amazon.com",
        "bestbuy.com",
        "walmart.com",
        "target.com",
        "newegg.com",
    ),
    Category.FOOD_BEVERAGE: (
        "amazon.com",
        "walmart.com",
        "target.com",
        "instacart.com",
        "kroger.com",
    ),
    Category.HOME_GARDEN: (
        "amazon.com",
        "homedepot.com",
        "lowes.com",
        "wayfair.com",
        "walmart.com",
    ),
    Category.AUTOMOTIVE: (
        "amazon.com",
        "autozone.com",
        "walmart.com",
        "target.com",
    ),
    Category.SOFTWARE: (
        "amazon.com",
        "bestbuy.com",
        "walmart.com",
        "target.com",
    ),
    Category.OTHER: (
        "amazon.com",
        "walmart.com",
        "target.com",
        "ebay.com",
    ),
}

# Retailer names already covered by Stage 1 query templates.
# Stage 2 must use remaining category retailers, not duplicate these.
STAGE1_RETAILER_NAMES: frozenset[str] = frozenset(
    {"amazon", "walmart", "target", "sephora", "ulta"}
)

# Absolute extraction caps (not category sanity bounds).
RETAIL_ABS_MAX_PRICE = 50_000.0
SERVICE_ABS_MAX_PRICE = 100_000.0
SERVICE_SMALL_PRICE_THRESHOLD = 10.0

# Low-ticket retail categories get a baseline-relative ceiling.
# health_beauty uses a wider multiple because prestige SKUs vary more.
# clothing / food_beverage / other use a tighter multiple.
LOW_TICKET_CATEGORIES: frozenset[Category] = frozenset(
    {
        Category.CLOTHING,
        Category.FOOD_BEVERAGE,
        Category.HEALTH_BEAUTY,
        Category.OTHER,
    }
)
LOW_TICKET_BASELINE_CAP: dict[Category, float] = {
    Category.HEALTH_BEAUTY: 10.0,
    Category.CLOTHING: 5.0,
    Category.FOOD_BEVERAGE: 5.0,
    Category.OTHER: 5.0,
}

# Coarse median-relative filter. Services tolerate more natural spread.
RETAIL_COARSE_MULTIPLIER = 3.0
SERVICE_COARSE_MULTIPLIER = 5.0

# IQR fence multipliers. Applied only when the sample is large enough
# that dropping points will not collapse a 3–5 price set.
RETAIL_IQR_MULTIPLIER = 1.5
SERVICE_IQR_MULTIPLIER = 3.0
IQR_MIN_SAMPLE_SIZE = 6

MIN_RELIABLE_PRICES = 3
CONTEXT_WINDOW = 250

# Maximum concurrent Tavily searches during market research.
MAX_TAVILY_CONCURRENCY = 5
