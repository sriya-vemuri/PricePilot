"""Async HTTP client for Tavily search.

This module is intentionally limited to HTTP communication with Tavily.
Query building, price extraction, filtering, and orchestration belong
elsewhere.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.config import Settings

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_SEARCH_DEPTH = "advanced"
TAVILY_MAX_RESULTS = 8
RETRY_BASE_DELAY_SECONDS = 0.25
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class TavilyError(Exception):
    """Base class for Tavily client errors."""


class TavilyNotConfiguredError(TavilyError):
    """Raised when a Tavily request is attempted without an API key."""


class TavilyAuthenticationError(TavilyError):
    """Raised for 401/403 responses from Tavily."""


class TavilyRateLimitError(TavilyError):
    """Raised when Tavily rate limits persist after retries."""


class TavilyHTTPError(TavilyError):
    """Raised for non-retryable or exhausted HTTP failures."""

    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class TavilyTimeoutError(TavilyError):
    """Raised when Tavily requests time out after retries."""


class TavilyResponseError(TavilyError):
    """Raised when Tavily returns a malformed response payload."""


class TavilyResult(BaseModel):
    content: str
    url: str | None = None
    title: str | None = None


class TavilySearchResult(BaseModel):
    answer: str | None = None
    results: list[TavilyResult] = Field(default_factory=list)


SleepFn = Callable[[float], Awaitable[None]]


class TavilyClient:
    """Async Tavily search client."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
        sleeper: SleepFn | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient()
        self._sleep = sleeper or asyncio.sleep

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "TavilyClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def search(
        self,
        query: str,
        include_domains: list[str] | None = None,
    ) -> TavilySearchResult:
        """Execute a Tavily search and return a validated internal result."""
        api_key = self._require_api_key()
        payload = self._build_request_body(query, include_domains)
        max_retries = max(0, self._settings.tavily_max_retries)
        last_error: TavilyError | None = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                delay = retry_delay(attempt - 1)
                logger.warning(
                    "Retrying Tavily search after failure (attempt %s/%s, delay=%.2fs, query=%r)",
                    attempt + 1,
                    max_retries + 1,
                    delay,
                    query,
                )
                await self._sleep(delay)

            try:
                return await self._perform_search(payload, api_key=api_key, query=query)
            except TavilyAuthenticationError:
                raise
            except (TavilyRateLimitError, TavilyTimeoutError, TavilyHTTPError) as exc:
                retryable = isinstance(exc, (TavilyRateLimitError, TavilyTimeoutError)) or (
                    isinstance(exc, TavilyHTTPError) and exc.retryable
                )
                if not retryable or attempt >= max_retries:
                    raise
                last_error = exc
                logger.warning(
                    "Transient Tavily failure (attempt %s/%s, query=%r): %s",
                    attempt + 1,
                    max_retries + 1,
                    query,
                    exc,
                )

        if last_error is not None:
            raise last_error
        raise TavilyHTTPError("Tavily search failed after retries")

    async def _perform_search(
        self,
        payload: dict[str, Any],
        *,
        api_key: str,
        query: str,
    ) -> TavilySearchResult:
        timeout = httpx.Timeout(self._settings.tavily_timeout_seconds)
        try:
            response = await self._client.post(
                TAVILY_SEARCH_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            logger.warning("Tavily request timed out for query=%r", query)
            raise TavilyTimeoutError("Tavily request timed out") from exc
        except httpx.TransportError as exc:
            logger.warning("Tavily network error for query=%r: %s", query, exc.__class__.__name__)
            raise TavilyHTTPError(
                "Tavily network error",
                retryable=True,
            ) from exc

        return self._handle_response(response, query=query)

    def _handle_response(self, response: httpx.Response, *, query: str) -> TavilySearchResult:
        status = response.status_code

        if status == 200:
            try:
                payload = response.json()
            except ValueError as exc:
                logger.warning("Tavily returned non-JSON payload for query=%r", query)
                raise TavilyResponseError("Tavily response is not valid JSON") from exc
            return parse_tavily_response(payload)

        if status in {401, 403}:
            logger.error("Tavily authentication failed with status %s for query=%r", status, query)
            raise TavilyAuthenticationError(f"Tavily authentication failed with status {status}")

        if status == 429:
            logger.warning("Tavily rate limit hit for query=%r", query)
            raise TavilyRateLimitError("Tavily rate limit exceeded")

        if status in RETRYABLE_STATUS_CODES:
            logger.warning("Tavily server error %s for query=%r", status, query)
            raise TavilyHTTPError(
                f"Tavily server error with status {status}",
                status_code=status,
                retryable=True,
            )

        logger.error("Tavily HTTP error %s for query=%r", status, query)
        raise TavilyHTTPError(
            f"Tavily request failed with status {status}",
            status_code=status,
            retryable=False,
        )

    def _require_api_key(self) -> str:
        api_key = (self._settings.tavily_api_key or "").strip()
        if not api_key:
            raise TavilyNotConfiguredError(
                "TAVILY_API_KEY is not configured. Set it before calling Tavily."
            )
        return api_key

    @staticmethod
    def _build_request_body(
        query: str,
        include_domains: list[str] | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "query": query,
            "search_depth": TAVILY_SEARCH_DEPTH,
            "max_results": TAVILY_MAX_RESULTS,
            "include_answer": True,
        }
        if include_domains:
            body["include_domains"] = include_domains
        return body


def retry_delay(retry_index: int) -> float:
    """Exponential backoff delay for retry attempt `retry_index` (0-based)."""
    return RETRY_BASE_DELAY_SECONDS * (2**retry_index)


def parse_tavily_response(payload: object) -> TavilySearchResult:
    """Validate and normalize a Tavily JSON payload."""
    if not isinstance(payload, dict):
        raise TavilyResponseError("Tavily response must be a JSON object")

    answer = payload.get("answer")
    if answer is not None and not isinstance(answer, str):
        raise TavilyResponseError("Tavily answer must be a string or null")

    raw_results = payload.get("results", [])
    if raw_results is None:
        raw_results = []
    if not isinstance(raw_results, list):
        raise TavilyResponseError("Tavily results must be a list")

    parsed_results: list[TavilyResult] = []
    for index, item in enumerate(raw_results):
        if not isinstance(item, dict):
            raise TavilyResponseError(f"Tavily result at index {index} must be an object")

        content = item.get("content")
        if content is None:
            continue
        if not isinstance(content, str):
            raise TavilyResponseError(f"Tavily result content at index {index} must be a string")

        content = content.strip()
        if not content:
            continue

        url = item.get("url")
        title = item.get("title")
        if url is not None and not isinstance(url, str):
            raise TavilyResponseError(f"Tavily result url at index {index} must be a string or null")
        if title is not None and not isinstance(title, str):
            raise TavilyResponseError(f"Tavily result title at index {index} must be a string or null")

        parsed_results.append(
            TavilyResult(
                content=content,
                url=url,
                title=title,
            )
        )

    return TavilySearchResult(answer=answer, results=parsed_results)
