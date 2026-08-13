"""Market-research orchestration using Tavily and pure research modules."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.clients.tavily import (
    TavilyClient,
    TavilyError,
    TavilyHTTPError,
    TavilyNotConfiguredError,
    TavilyRateLimitError,
    TavilySearchResult,
    TavilyTimeoutError,
)
from app.config import Settings, get_settings
from app.core.categories import get_pricing_mode
from app.models.enums import Category, DemandLevel, MarketTrend, PricingMode, RetrievalMode
from app.models.responses import DataTrust
from app.repositories.errors import DatabaseError
from app.repositories.schemas import MarketCacheRecord, MarketCacheUpsert
from app.services.market_research.cache_key import build_cache_key
from app.services.market_research.constants import MAX_TAVILY_CONCURRENCY
from app.services.market_research.models import (
    WARNING_DEMAND_UNAVAILABLE,
    WARNING_INSUFFICIENT_MARKET_DATA,
    WARNING_STAGE3_LOW_TRUST,
    WARNING_TAVILY_PARTIAL_FAILURE,
    WARNING_TAVILY_UNAVAILABLE,
    WARNING_TREND_UNAVAILABLE,
    ExtractedPrice,
    FilteredMarketResult,
    MarketQuery,
    MarketResearchResult,
)
from app.services.market_research.price_extractor import deduplicate_prices, extract_prices
from app.services.market_research.price_filter import filter_comparable_prices
from app.services.market_research.query_builder import (
    build_demand_query,
    build_stage_queries,
    build_trend_query,
    stage_trust,
)
from app.services.market_research.signal_detector import build_summary, detect_demand, detect_trend

logger = logging.getLogger(__name__)

# Warnings that remain meaningful on a later cache hit.
# Transient per-query failures (tavily_partial_failure) are not reused.
_DURABLE_CACHE_WARNINGS = frozenset(
    {
        WARNING_STAGE3_LOW_TRUST,
        WARNING_INSUFFICIENT_MARKET_DATA,
        WARNING_TREND_UNAVAILABLE,
        WARNING_DEMAND_UNAVAILABLE,
    }
)


class MarketCacheStore(Protocol):
    def get_fresh(self, cache_key: str, now: datetime | None = None) -> MarketCacheRecord | None: ...

    def upsert(self, payload: MarketCacheUpsert) -> MarketCacheRecord: ...


@dataclass
class _QueryRun:
    query: MarketQuery
    success: bool
    result: TavilySearchResult | None = None
    error: TavilyError | None = None


@dataclass
class _PricingStageSnapshot:
    stage: int
    extracted: list[ExtractedPrice] = field(default_factory=list)
    filtered: FilteredMarketResult | None = None
    primary_query: MarketQuery | None = None
    pricing_answer: str | None = None


@dataclass
class _LiveResearch:
    result: MarketResearchResult
    candidate_prices: list[float]
    cacheable: bool


class MarketResearchService:
    """Orchestrate Tavily searches and pure market-research processing."""

    def __init__(
        self,
        tavily_client: TavilyClient,
        *,
        cache_repo: MarketCacheStore | None = None,
        settings: Settings | None = None,
        max_concurrency: int = MAX_TAVILY_CONCURRENCY,
    ) -> None:
        self._tavily = tavily_client
        self._cache = cache_repo
        self._settings = settings
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def research(
        self,
        product_name: str,
        category: Category,
        target_market: str,
        baseline_price: float | None,
    ) -> MarketResearchResult:
        pricing_mode = get_pricing_mode(category)
        cache_key = build_cache_key(product_name, category, target_market, pricing_mode)

        cached = self._read_cache(cache_key)
        if cached is not None:
            return self._result_from_cache(
                cached,
                baseline_price=baseline_price,
                category=category,
                pricing_mode=pricing_mode,
            )

        live = await self._research_from_tavily(
            product_name,
            category,
            target_market,
            baseline_price,
            pricing_mode,
        )
        if live.cacheable:
            self._write_cache(
                cache_key=cache_key,
                product_name=product_name,
                category=category,
                target_market=target_market,
                pricing_mode=pricing_mode,
                candidate_prices=live.candidate_prices,
                result=live.result,
            )
        return live.result

    def _read_cache(self, cache_key: str) -> MarketCacheRecord | None:
        if self._cache is None:
            return None
        try:
            return self._cache.get_fresh(cache_key)
        except DatabaseError:
            logger.exception("Market cache lookup failed for key=%s; continuing with live Tavily research", cache_key)
            return None

    def _write_cache(
        self,
        *,
        cache_key: str,
        product_name: str,
        category: Category,
        target_market: str,
        pricing_mode: PricingMode,
        candidate_prices: list[float],
        result: MarketResearchResult,
    ) -> None:
        if self._cache is None:
            return
        settings = self._settings or get_settings()
        ttl_seconds = (
            settings.market_cache_reliable_ttl_seconds
            if result.has_reliable_data
            else settings.market_cache_low_quality_ttl_seconds
        )
        fetched_at = result.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        payload = MarketCacheUpsert(
            cache_key=cache_key,
            expires_at=fetched_at + timedelta(seconds=ttl_seconds),
            product_name=product_name,
            category=category,
            target_market=target_market,
            pricing_mode=pricing_mode,
            candidate_prices=candidate_prices,
            competitor_price_1=result.competitor_price_1,
            competitor_price_2=result.competitor_price_2,
            competitor_price_3=result.competitor_price_3,
            comparable_prices=result.comparable_prices,
            filtered_range_low=result.filtered_range_low,
            filtered_range_high=result.filtered_range_high,
            raw_prices_found=result.raw_prices_found,
            filtered_prices_count=result.filtered_prices_count,
            outliers_removed=result.outliers_removed,
            has_reliable_data=result.has_reliable_data,
            retrieval_mode=result.retrieval_mode,
            market_trend=result.market_trend,
            demand_level=result.demand_level,
            summary=result.summary,
            tavily_query=result.tavily_query,
            fetched_at=fetched_at,
            data_trust=result.data_trust,
            warnings=_durable_warnings(result.warnings),
        )
        try:
            self._cache.upsert(payload)
        except DatabaseError:
            # Cache persistence is optional. A write failure must not discard
            # successful Tavily research. Logged only — not a user-facing warning.
            logger.exception("Market cache write failed for key=%s", cache_key)

    def _result_from_cache(
        self,
        record: MarketCacheRecord,
        *,
        baseline_price: float | None,
        category: Category,
        pricing_mode: PricingMode,
    ) -> MarketResearchResult:
        """Rebuild a result from cache, re-filtering candidate prices with the current baseline.

        Recalculated from candidate_prices + current baseline:
            comparable_prices, competitor triple, ranges, counts, outliers, has_reliable_data
        Reused from cache (baseline-independent):
            market_trend, demand_level, summary, tavily_query, fetched_at,
            retrieval_mode, data_trust
        """
        filtered = filter_comparable_prices(
            record.candidate_prices,
            baseline_price=baseline_price,
            category=category,
            pricing_mode=pricing_mode,
        )
        warnings = [
            warning
            for warning in record.warnings
            if warning in _DURABLE_CACHE_WARNINGS and warning != WARNING_INSUFFICIENT_MARKET_DATA
        ]
        if record.retrieval_mode == RetrievalMode.STAGE3_SUCCESS:
            warnings.append(WARNING_STAGE3_LOW_TRUST)
        if not filtered.has_reliable_data:
            warnings.append(WARNING_INSUFFICIENT_MARKET_DATA)

        return MarketResearchResult(
            pricing_mode=pricing_mode,
            competitor_price_1=filtered.competitor_price_1,
            competitor_price_2=filtered.competitor_price_2,
            competitor_price_3=filtered.competitor_price_3,
            comparable_prices=filtered.comparable_prices,
            filtered_range_low=filtered.filtered_range_low,
            filtered_range_high=filtered.filtered_range_high,
            raw_prices_found=filtered.raw_prices_found,
            filtered_prices_count=filtered.filtered_prices_count,
            outliers_removed=filtered.outliers_removed,
            has_reliable_data=filtered.has_reliable_data,
            retrieval_mode=record.retrieval_mode,
            market_trend=record.market_trend,
            demand_level=record.demand_level,
            summary=record.summary,
            tavily_query=record.tavily_query,
            fetched_at=record.fetched_at,
            data_trust=record.data_trust,
            warnings=_unique_warnings(warnings),
            cache_hit=True,
        )

    async def _research_from_tavily(
        self,
        product_name: str,
        category: Category,
        target_market: str,
        baseline_price: float | None,
        pricing_mode: PricingMode,
    ) -> _LiveResearch:
        warnings: list[str] = []

        stage1_pricing_queries = build_stage_queries(
            product_name,
            category,
            target_market,
            pricing_mode,
            stage=1,
        )
        trend_query = build_trend_query(product_name, category, target_market)
        demand_query = build_demand_query(product_name, category, target_market)

        stage1_runs = await self._run_queries([*stage1_pricing_queries, trend_query, demand_query])
        pricing_runs = [run for run in stage1_runs if run.query.query_kind == "pricing"]
        trend_run = next(run for run in stage1_runs if run.query.query_kind == "trend")
        demand_run = next(run for run in stage1_runs if run.query.query_kind == "demand")

        self._collect_query_warnings(stage1_runs, warnings)

        if self._is_complete_transient_outage(stage1_runs):
            return _LiveResearch(
                result=self._build_degraded_result(
                    pricing_mode=pricing_mode,
                    adopted_query=stage1_pricing_queries[0],
                    warnings=_unique_warnings([WARNING_TAVILY_UNAVAILABLE, WARNING_INSUFFICIENT_MARKET_DATA]),
                ),
                candidate_prices=[],
                cacheable=False,
            )

        market_trend, trend_text, trend_warning = self._resolve_trend(trend_run)
        if trend_warning:
            warnings.append(trend_warning)

        demand_level, demand_text, demand_warning = self._resolve_demand(demand_run)
        if demand_warning:
            warnings.append(demand_warning)

        stage1_snapshot = self._build_pricing_snapshot(
            stage=1,
            pricing_runs=pricing_runs,
            category=category,
            pricing_mode=pricing_mode,
            baseline_price=baseline_price,
        )

        retrieval_mode = RetrievalMode.PRIMARY
        data_trust: DataTrust = stage_trust(1)
        adopted_snapshot = stage1_snapshot

        if not stage1_snapshot.filtered or not stage1_snapshot.filtered.has_reliable_data:
            stage2_pricing_queries = build_stage_queries(
                product_name,
                category,
                target_market,
                pricing_mode,
                stage=2,
            )
            stage2_runs = await self._run_queries(stage2_pricing_queries)
            self._collect_query_warnings(stage2_runs, warnings)

            stage2_snapshot = self._build_pricing_snapshot(
                stage=2,
                pricing_runs=stage2_runs,
                prior_extracted=stage1_snapshot.extracted,
                category=category,
                pricing_mode=pricing_mode,
                baseline_price=baseline_price,
            )

            if self._improved(stage2_snapshot, stage1_snapshot):
                adopted_snapshot = stage2_snapshot
                if stage2_snapshot.filtered and stage2_snapshot.filtered.has_reliable_data:
                    retrieval_mode = RetrievalMode.STAGE2_SUCCESS
                    data_trust = stage_trust(2)
                else:
                    retrieval_mode = RetrievalMode.STAGE2_INSUFFICIENT
                    data_trust = stage_trust(2)

            if not adopted_snapshot.filtered or not adopted_snapshot.filtered.has_reliable_data:
                stage3_pricing_queries = build_stage_queries(
                    product_name,
                    category,
                    target_market,
                    pricing_mode,
                    stage=3,
                )
                stage3_runs = await self._run_queries(stage3_pricing_queries)
                self._collect_query_warnings(stage3_runs, warnings)

                stage3_snapshot = self._build_pricing_snapshot(
                    stage=3,
                    pricing_runs=stage3_runs,
                    prior_extracted=adopted_snapshot.extracted,
                    category=category,
                    pricing_mode=pricing_mode,
                    baseline_price=baseline_price,
                )

                if self._improved(stage3_snapshot, adopted_snapshot):
                    adopted_snapshot = stage3_snapshot
                    if stage3_snapshot.filtered and stage3_snapshot.filtered.has_reliable_data:
                        retrieval_mode = RetrievalMode.STAGE3_SUCCESS
                        data_trust = stage_trust(3)
                        warnings.append(WARNING_STAGE3_LOW_TRUST)
                    else:
                        retrieval_mode = RetrievalMode.EXHAUSTED
                        data_trust = stage_trust(3)
                else:
                    if adopted_snapshot.stage == 2:
                        retrieval_mode = RetrievalMode.STAGE2_INSUFFICIENT
                        data_trust = stage_trust(2)
                    else:
                        retrieval_mode = RetrievalMode.EXHAUSTED
                        data_trust = "low"

        filtered = adopted_snapshot.filtered
        if filtered is None:
            filtered = self._filter_extracted(
                [],
                baseline_price=baseline_price,
                category=category,
                pricing_mode=pricing_mode,
            )

        if not filtered.has_reliable_data:
            warnings.append(WARNING_INSUFFICIENT_MARKET_DATA)

        summary = build_summary(
            adopted_snapshot.pricing_answer,
            trend_text if trend_run.success else None,
            demand_text if demand_run.success else None,
        )

        adopted_query = adopted_snapshot.primary_query or stage1_pricing_queries[0]
        result = MarketResearchResult(
            pricing_mode=pricing_mode,
            competitor_price_1=filtered.competitor_price_1,
            competitor_price_2=filtered.competitor_price_2,
            competitor_price_3=filtered.competitor_price_3,
            comparable_prices=filtered.comparable_prices,
            filtered_range_low=filtered.filtered_range_low,
            filtered_range_high=filtered.filtered_range_high,
            raw_prices_found=filtered.raw_prices_found,
            filtered_prices_count=filtered.filtered_prices_count,
            outliers_removed=filtered.outliers_removed,
            has_reliable_data=filtered.has_reliable_data,
            retrieval_mode=retrieval_mode,
            market_trend=market_trend,
            demand_level=demand_level,
            summary=summary,
            tavily_query=adopted_query.text,
            fetched_at=datetime.now(UTC),
            data_trust=data_trust,
            warnings=_unique_warnings(warnings),
            cache_hit=False,
        )
        return _LiveResearch(
            result=result,
            candidate_prices=_candidate_prices(adopted_snapshot.extracted),
            cacheable=True,
        )

    async def _run_queries(self, queries: list[MarketQuery]) -> list[_QueryRun]:
        return list(await asyncio.gather(*(self._run_query(query) for query in queries)))

    async def _run_query(self, query: MarketQuery) -> _QueryRun:
        async with self._semaphore:
            try:
                domains = list(query.include_domains) if query.include_domains else None
                result = await self._tavily.search(query.text, domains)
                return _QueryRun(query=query, success=True, result=result)
            except TavilyNotConfiguredError:
                raise
            except TavilyError as exc:
                logger.warning(
                    "Tavily query failed (%s, stage=%s): %s",
                    query.query_kind,
                    query.stage,
                    exc.__class__.__name__,
                )
                return _QueryRun(query=query, success=False, error=exc)

    def _build_pricing_snapshot(
        self,
        *,
        stage: int,
        pricing_runs: list[_QueryRun],
        category: Category,
        pricing_mode: PricingMode,
        baseline_price: float | None,
        prior_extracted: list[ExtractedPrice] | None = None,
    ) -> _PricingStageSnapshot:
        extracted = list(prior_extracted or [])
        primary_query: MarketQuery | None = None
        pricing_answer: str | None = None

        for run in pricing_runs:
            if not run.success or run.result is None:
                continue
            if primary_query is None:
                primary_query = run.query
                pricing_answer = run.result.answer
            extracted.extend(
                extract_prices(
                    _collect_search_text(run.result),
                    category=category,
                    pricing_mode=pricing_mode,
                )
            )

        filtered = self._filter_extracted(
            extracted,
            baseline_price=baseline_price,
            category=category,
            pricing_mode=pricing_mode,
        )
        return _PricingStageSnapshot(
            stage=stage,
            extracted=extracted,
            filtered=filtered,
            primary_query=primary_query or (pricing_runs[0].query if pricing_runs else None),
            pricing_answer=pricing_answer,
        )

    def _filter_extracted(
        self,
        extracted: list[ExtractedPrice],
        *,
        baseline_price: float | None,
        category: Category,
        pricing_mode: PricingMode,
    ) -> FilteredMarketResult:
        deduped = deduplicate_prices(extracted)
        return filter_comparable_prices(
            deduped,
            baseline_price=baseline_price,
            category=category,
            pricing_mode=pricing_mode,
        )

    def _resolve_trend(
        self,
        trend_run: _QueryRun,
    ) -> tuple[MarketTrend, str | None, str | None]:
        if trend_run.success and trend_run.result is not None:
            text = _collect_search_text(trend_run.result)
            return detect_trend(text), trend_run.result.answer or text, None
        return MarketTrend.STABLE, None, WARNING_TREND_UNAVAILABLE

    def _resolve_demand(
        self,
        demand_run: _QueryRun,
    ) -> tuple[DemandLevel, str | None, str | None]:
        if demand_run.success and demand_run.result is not None:
            text = _collect_search_text(demand_run.result)
            return detect_demand(text), demand_run.result.answer or text, None
        return DemandLevel.MODERATE, None, WARNING_DEMAND_UNAVAILABLE

    def _collect_query_warnings(self, runs: list[_QueryRun], warnings: list[str]) -> None:
        if any(not run.success for run in runs):
            warnings.append(WARNING_TAVILY_PARTIAL_FAILURE)

    def _is_complete_transient_outage(self, runs: list[_QueryRun]) -> bool:
        if not runs or any(run.success for run in runs):
            return False
        return all(run.error is not None and _is_transient_error(run.error) for run in runs)

    def _improved(self, candidate: _PricingStageSnapshot, baseline: _PricingStageSnapshot) -> bool:
        candidate_count = candidate.filtered.filtered_prices_count if candidate.filtered else 0
        baseline_count = baseline.filtered.filtered_prices_count if baseline.filtered else 0
        return candidate_count > baseline_count

    def _build_degraded_result(
        self,
        *,
        pricing_mode: PricingMode,
        adopted_query: MarketQuery,
        warnings: list[str],
    ) -> MarketResearchResult:
        return MarketResearchResult(
            pricing_mode=pricing_mode,
            competitor_price_1=None,
            competitor_price_2=None,
            competitor_price_3=None,
            comparable_prices=[],
            filtered_range_low=None,
            filtered_range_high=None,
            raw_prices_found=0,
            filtered_prices_count=0,
            outliers_removed=0,
            has_reliable_data=False,
            retrieval_mode=RetrievalMode.EXHAUSTED,
            market_trend=MarketTrend.STABLE,
            demand_level=DemandLevel.MODERATE,
            summary="",
            tavily_query=adopted_query.text,
            fetched_at=datetime.now(UTC),
            data_trust="low",
            warnings=warnings,
            cache_hit=False,
        )


def _candidate_prices(extracted: list[ExtractedPrice]) -> list[float]:
    """Unique extracted prices before baseline-aware filtering."""
    return sorted({item.price for item in deduplicate_prices(extracted)})


def _durable_warnings(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if warning in _DURABLE_CACHE_WARNINGS]


def _collect_search_text(result: TavilySearchResult) -> str:
    parts: list[str] = []
    if result.answer:
        parts.append(result.answer)
    for item in result.results:
        if item.content:
            parts.append(item.content)
    return " ".join(parts)


def _is_transient_error(error: TavilyError) -> bool:
    if isinstance(error, (TavilyRateLimitError, TavilyTimeoutError)):
        return True
    return isinstance(error, TavilyHTTPError) and error.retryable


def _unique_warnings(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for warning in warnings:
        if warning not in seen:
            seen.add(warning)
            unique.append(warning)
    return unique
