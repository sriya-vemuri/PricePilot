"""Pure query builders for PricePilot market research.

`target_market` is interpolated into every query. There is no FX or
full localization system — only consistent market labeling.
"""

from app.core.categories import get_pricing_mode
from app.models.enums import Category, PricingMode
from app.models.responses import DataTrust
from app.services.market_research.constants import (
    RETAILER_DOMAINS_BY_CATEGORY,
    STAGE1_RETAILER_NAMES,
)
from app.services.market_research.models import MarketQuery

_MARKET_SHORT_ALIASES: dict[str, str] = {
    "united states": "US",
    "usa": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "us": "US",
    "united kingdom": "UK",
    "great britain": "UK",
    "uk": "UK",
}


def stage_trust(stage: int) -> DataTrust:
    if stage <= 1:
        return "high"
    if stage == 2:
        return "medium"
    return "low"


def market_query_terms(target_market: str) -> tuple[str, str]:
    """Return `(full_label, short_label)` for query interpolation."""
    full = " ".join((target_market or "").split())
    if not full:
        full = "United States"
    short = _MARKET_SHORT_ALIASES.get(full.lower(), full)
    return full, short


def retailer_domains_for(category: Category) -> tuple[str, ...]:
    return RETAILER_DOMAINS_BY_CATEGORY.get(
        category,
        RETAILER_DOMAINS_BY_CATEGORY[Category.OTHER],
    )


def _pricing_domains(category: Category, pricing_mode: PricingMode) -> tuple[str, ...]:
    if pricing_mode == PricingMode.SERVICE:
        return ()
    return retailer_domains_for(category)


def _pricing_query(text: str, stage: int, domains: tuple[str, ...]) -> MarketQuery:
    return MarketQuery(
        text=text,
        stage=stage,
        trust=stage_trust(stage),
        query_kind="pricing",
        include_domains=domains,
    )


def _signal_query(text: str, query_kind: str) -> MarketQuery:
    return MarketQuery(
        text=text,
        stage=1,
        trust="high",
        query_kind=query_kind,  # type: ignore[arg-type]
        include_domains=(),
    )


def build_stage_queries(
    product_name: str,
    category: Category,
    target_market: str,
    pricing_mode: PricingMode | None = None,
    *,
    stage: int,
) -> list[MarketQuery]:
    mode = pricing_mode or get_pricing_mode(category)
    if stage == 1:
        return _stage1_queries(product_name, category, target_market, mode)
    if stage == 2:
        return _stage2_queries(product_name, category, target_market, mode)
    if stage == 3:
        return _stage3_queries(product_name, category, target_market, mode)
    raise ValueError(f"Unsupported market-research stage: {stage}")


def build_trend_query(
    product_name: str,
    category: Category,
    target_market: str,
) -> MarketQuery:
    full, _short = market_query_terms(target_market)
    cat = category.value.replace("_", " ")
    return _signal_query(f"{product_name} {cat} {full} market trend", "trend")


def build_demand_query(
    product_name: str,
    category: Category,
    target_market: str,
) -> MarketQuery:
    full, _short = market_query_terms(target_market)
    cat = category.value.replace("_", " ")
    return _signal_query(f"{product_name} {cat} consumer demand {full}", "demand")


def _stage1_queries(
    product_name: str,
    category: Category,
    target_market: str,
    pricing_mode: PricingMode,
) -> list[MarketQuery]:
    full, short = market_query_terms(target_market)
    domains = _pricing_domains(category, pricing_mode)

    if pricing_mode == PricingMode.SERVICE:
        texts = [
            f"{product_name} cost {short}",
            f"{product_name} average cost {full}",
            f"{product_name} treatment price {short}",
            f"{product_name} cost range {short}",
            f"{product_name} pricing {full}",
        ]
        return [_pricing_query(text, 1, domains) for text in texts]

    texts = [
        f"{product_name} price {short}" + (" USD" if short == "US" else ""),
        f"{product_name} retail price {full}",
        f"{product_name} Amazon price {short}",
        f"{product_name} Walmart price {short}",
        f"{product_name} Target price {short}",
    ]
    if category == Category.HEALTH_BEAUTY:
        texts.append(f"{product_name} Sephora price {short}")
        texts.append(f"{product_name} Ulta price {short}")
    return [_pricing_query(text, 1, domains) for text in texts]


def _stage2_queries(
    product_name: str,
    category: Category,
    target_market: str,
    pricing_mode: PricingMode,
) -> list[MarketQuery]:
    full, short = market_query_terms(target_market)
    domains = _pricing_domains(category, pricing_mode)

    if pricing_mode == PricingMode.SERVICE:
        texts = [
            f"{product_name} provider cost {short}",
            f"{product_name} fee {full}",
            f"{product_name} price per session {short}",
        ]
        return [_pricing_query(text, 2, domains) for text in texts]

    extra_retailers = [
        domain.split(".")[0]
        for domain in retailer_domains_for(category)
        if domain.split(".")[0] not in STAGE1_RETAILER_NAMES
    ]
    texts = [f"{product_name} {name} price {short}" for name in extra_retailers[:3]]

    if category == Category.HEALTH_BEAUTY:
        texts.append(f"{product_name} drugstore price {short}")
    elif not texts:
        texts.append(f"{product_name} online retail price {short}")

    return [_pricing_query(text, 2, domains) for text in texts]


def _stage3_queries(
    product_name: str,
    category: Category,
    target_market: str,
    pricing_mode: PricingMode,
) -> list[MarketQuery]:
    """Broader fallback queries that still name the specific product."""
    full, short = market_query_terms(target_market)
    domains = _pricing_domains(category, pricing_mode)
    cat = category.value.replace("_", " ")

    if pricing_mode == PricingMode.SERVICE:
        texts = [
            f"{product_name} {cat} cost {short}",
            f"{product_name} {cat} average price {full}",
            f"{product_name} starting price {short}",
        ]
    else:
        texts = [
            f"{product_name} {cat} price {short}",
            f"{product_name} typical price {full}",
            f"{product_name} starting price {short}",
        ]
    return [_pricing_query(text, 3, domains) for text in texts]
