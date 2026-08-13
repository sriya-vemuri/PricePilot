from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.clients.tavily import (
    TavilyError,
    TavilyNotConfiguredError,
    TavilyResult,
    TavilySearchResult,
)
from app.services.market_research.query_builder import build_stage_queries, build_trend_query, build_demand_query
from app.models.enums import Category, PricingMode

SearchHandler = Callable[[str, list[str] | None], TavilySearchResult]


class FakeTavilyClient:
    """Test double for TavilyClient.search."""

    def __init__(
        self,
        handler: SearchHandler | None = None,
        *,
        responses: dict[str, TavilySearchResult | Exception] | None = None,
    ) -> None:
        self.handler = handler
        self.responses = responses or {}
        self.calls: list[tuple[str, list[str] | None]] = []

    async def search(
        self,
        query: str,
        include_domains: list[str] | None = None,
    ) -> TavilySearchResult:
        self.calls.append((query, include_domains))
        if self.handler is not None:
            return self.handler(query, include_domains)
        outcome = self.responses.get(query, TavilySearchResult())
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def price_result(*prices: float, answer: str | None = None) -> TavilySearchResult:
    content = " ".join(f"Buy now ${price:.2f} in stock." for price in prices)
    results = [TavilyResult(content=content)] if content else []
    return TavilySearchResult(answer=answer, results=results)


def trend_result(text: str = "The market is growing steadily.") -> TavilySearchResult:
    return TavilySearchResult(answer=text)


def demand_result(text: str = "There is high demand for this product.") -> TavilySearchResult:
    return TavilySearchResult(answer=text)


def build_default_signal_responses(
    product_name: str,
    category: Category,
    target_market: str,
) -> dict[str, TavilySearchResult]:
    trend = build_trend_query(product_name, category, target_market)
    demand = build_demand_query(product_name, category, target_market)
    return {
        trend.text: trend_result(),
        demand.text: demand_result(),
    }


def stage_query_texts(
    product_name: str,
    category: Category,
    target_market: str,
    pricing_mode: PricingMode,
    stage: int,
) -> list[str]:
    return [
        query.text
        for query in build_stage_queries(
            product_name,
            category,
            target_market,
            pricing_mode,
            stage=stage,
        )
    ]


def call_kinds(calls: list[tuple[str, list[str] | None]]) -> dict[str, Any]:
    return {
        "queries": [query for query, _ in calls],
        "domains": [domains for _, domains in calls],
    }
