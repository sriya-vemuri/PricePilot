"""Pure USD price extraction from search-result text.

V1 deduplication decision: identical numeric prices (rounded to cents) are
kept as a single observation. The same $29.99 repeating across snippets is
treated as one data point, not N independent competitor prices. Different
sources for the same amount are not preserved separately — numeric uniqueness
is safer than inflating sample size.
"""

from __future__ import annotations

import re

from app.models.enums import Category, PricingMode
from app.services.market_research.constants import (
    CONTEXT_WINDOW,
    RETAIL_ABS_MAX_PRICE,
    SERVICE_ABS_MAX_PRICE,
    SERVICE_SMALL_PRICE_THRESHOLD,
)
from app.services.market_research.models import ExtractedPrice, PriceSource

PRICE_RE = re.compile(r"\$\s*(\d{1,6}(?:,\d{3})*(?:\.\d{1,2})?)")

NON_USD_CURRENCY_RE = re.compile(
    r"[€£¥₹₩₽]|"
    r"\b(?:EUR|GBP|INR|CNY|JPY|KRW|AUD|CAD)\b|"
    r"\b(?:C\$|A\$|CA\$|AU\$)\b|"
    r"\b(?:canadian|australian)\s+dollars?\b",
    re.IGNORECASE,
)

MARKET_SIZE_RE = re.compile(
    r"\b("
    r"market size|market value|industry revenue|global market|total revenue|"
    r"market cap|cagr|market forecast|market growth rate|market report|"
    r"tam|total addressable market|revenue|million|billion"
    r")\b",
    re.IGNORECASE,
)

FEE_PHRASE_RE = re.compile(
    r"\b(shipping fee|delivery fee|shipping cost|postage|s&h)\b",
    re.IGNORECASE,
)
FREE_SHIPPING_RE = re.compile(r"\bfree shipping\b", re.IGNORECASE)
SHIPPING_NEAR_PRICE_RE = re.compile(
    r"\b(?:shipping|delivery)\b.{0,20}\$|\$\s*\d[\d,]*(?:\.\d{1,2})?.{0,20}\b(?:shipping|delivery)\b",
    re.IGNORECASE,
)

PROMO_RE = re.compile(
    r"\b(coupon|discount|save|was price|originally|markdown)\b|"
    r"\bwas\s+\$",
    re.IGNORECASE,
)

MODEL_YEAR_RE = re.compile(
    r"\bmodel year\b|\b(?:19|20)\d{2}\s*model\b",
    re.IGNORECASE,
)

# Purchase context — retailer brand names alone are not enough.
PRODUCT_PAGE_RE = re.compile(
    r"\b("
    r"add to cart|add to bag|buy now|in stock|per unit|per item|per bottle|"
    r"per tube|product|price"
    r")\b",
    re.IGNORECASE,
)

SERVICE_CONTEXT_RE = re.compile(
    r"\b("
    r"per session|per treatment|per hour|hourly|consultation|clinic|"
    r"appointment|procedure|session|treatment|visit|provider|office|"
    r"practice|package"
    r")\b",
    re.IGNORECASE,
)

_SOURCE_RANK = {
    PriceSource.PRODUCT_PAGE: 2,
    PriceSource.SERVICE_CONTEXT: 2,
    PriceSource.EDITORIAL: 1,
}


def extract_prices(
    text: str,
    *,
    category: Category,
    pricing_mode: PricingMode,
) -> list[ExtractedPrice]:
    """Extract candidate USD prices from unstructured document text."""
    if not text:
        return []

    results: list[ExtractedPrice] = []
    for match in PRICE_RE.finditer(text):
        price = float(match.group(1).replace(",", ""))
        if price <= 0:
            continue
        if pricing_mode == PricingMode.SERVICE and price >= SERVICE_ABS_MAX_PRICE:
            continue
        if pricing_mode == PricingMode.RETAIL and price >= RETAIL_ABS_MAX_PRICE:
            continue

        ctx_start = max(0, match.start() - CONTEXT_WINDOW)
        ctx_end = min(len(text), match.end() + CONTEXT_WINDOW)
        ctx = text[ctx_start:ctx_end]

        if _should_reject_context(ctx, price=price, pricing_mode=pricing_mode):
            continue

        source = _classify_source(ctx, pricing_mode)
        if (
            pricing_mode == PricingMode.RETAIL
            and category == Category.HEALTH_BEAUTY
            and source != PriceSource.PRODUCT_PAGE
            and price >= 1000
        ):
            continue

        results.append(
            ExtractedPrice(
                price=round(price, 2),
                source=source,
                context=ctx.strip(),
            )
        )

    return results


def deduplicate_prices(prices: list[ExtractedPrice]) -> list[ExtractedPrice]:
    """Keep one observation per numeric price, rounded to cents.

    When duplicates exist, the stronger source label is retained.
    """
    unique: dict[float, ExtractedPrice] = {}
    for item in prices:
        key = round(item.price, 2)
        rounded = item.model_copy(update={"price": key})
        existing = unique.get(key)
        if existing is None or _SOURCE_RANK[rounded.source] > _SOURCE_RANK[existing.source]:
            unique[key] = rounded
    return list(unique.values())


def _should_reject_context(ctx: str, *, price: float, pricing_mode: PricingMode) -> bool:
    if NON_USD_CURRENCY_RE.search(ctx):
        return True
    if MARKET_SIZE_RE.search(ctx):
        return True
    if _is_shipping_or_delivery_fee(ctx):
        return True
    if PROMO_RE.search(ctx):
        return True
    if MODEL_YEAR_RE.search(ctx):
        return True

    if pricing_mode == PricingMode.SERVICE:
        has_service_context = bool(SERVICE_CONTEXT_RE.search(ctx))
        if price < SERVICE_SMALL_PRICE_THRESHOLD and not has_service_context:
            return True

    return False


def _is_shipping_or_delivery_fee(ctx: str) -> bool:
    if FEE_PHRASE_RE.search(ctx):
        return True
    stripped = FREE_SHIPPING_RE.sub(" ", ctx)
    return bool(SHIPPING_NEAR_PRICE_RE.search(stripped))


def _classify_source(ctx: str, pricing_mode: PricingMode) -> PriceSource:
    if pricing_mode == PricingMode.SERVICE:
        if SERVICE_CONTEXT_RE.search(ctx):
            return PriceSource.SERVICE_CONTEXT
        return PriceSource.EDITORIAL
    if PRODUCT_PAGE_RE.search(ctx):
        return PriceSource.PRODUCT_PAGE
    return PriceSource.EDITORIAL
