from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.clients.tavily import (
    TavilyAuthenticationError,
    TavilyClient,
    TavilyHTTPError,
    TavilyNotConfiguredError,
    TavilyRateLimitError,
    TavilyResponseError,
    TavilyTimeoutError,
    retry_delay,
)
from app.config import Settings

API_KEY = "super-secret-key-12345"
QUERY = "Vitamin C Serum price US"


def make_settings(**overrides: Any) -> Settings:
    defaults = {
        "tavily_api_key": API_KEY,
        "tavily_timeout_seconds": 5.0,
        "tavily_max_retries": 3,
        "supabase_url": "https://example.supabase.co",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def success_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "answer": "Typical retail price is around $24.",
        "results": [
            {
                "content": "Buy now for $24.99 in stock.",
                "url": "https://example.com/product",
                "title": "Example Product",
            },
            {
                "content": "Listed at $26.00.",
                "url": "https://shop.example.com/item",
                "title": "Shop Item",
            },
        ],
    }
    payload.update(overrides)
    return payload


class MockTransport:
    def __init__(self, handler):
        self.handler = handler
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request, len(self.requests))


def build_client(
    settings: Settings,
    handler,
    *,
    sleeper=None,
) -> TavilyClient:
    transport = MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = TavilyClient(settings, http_client=http_client, sleeper=sleeper or _noop_sleep)
    client._transport = transport  # test helper
    return client


async def _noop_sleep(_delay: float) -> None:
    return None


@pytest.mark.anyio
class TestTavilyConfiguration:
    async def test_missing_api_key_raises_not_configured(self):
        client = build_client(
            make_settings(tavily_api_key=None),
            lambda request, call: httpx.Response(200, json=success_payload()),
        )
        with pytest.raises(TavilyNotConfiguredError, match="TAVILY_API_KEY"):
            await client.search(QUERY)

    async def test_blank_api_key_raises_not_configured(self):
        client = build_client(
            make_settings(tavily_api_key="   "),
            lambda request, call: httpx.Response(200, json=success_payload()),
        )
        with pytest.raises(TavilyNotConfiguredError):
            await client.search(QUERY)


@pytest.mark.anyio
class TestTavilySuccess:
    async def test_success_with_answer_and_multiple_results(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json=success_payload()),
        )
        result = await client.search(QUERY)

        assert result.answer == "Typical retail price is around $24."
        assert len(result.results) == 2
        assert result.results[0].content == "Buy now for $24.99 in stock."
        assert result.results[0].url == "https://example.com/product"
        assert result.results[0].title == "Example Product"

    async def test_success_with_answer_only(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(
                200,
                json={"answer": "Only an answer.", "results": []},
            ),
        )
        result = await client.search(QUERY)
        assert result.answer == "Only an answer."
        assert result.results == []

    async def test_success_with_empty_results(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json={"answer": None, "results": []}),
        )
        result = await client.search(QUERY)
        assert result.answer is None
        assert result.results == []

    async def test_optional_title_and_url_handling(self):
        payload = {
            "answer": None,
            "results": [
                {"content": "Price $19.99"},
                {"content": "Price $21.00", "url": "https://example.com/a"},
                {"content": "   "},
            ],
        }
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json=payload),
        )
        result = await client.search(QUERY)
        assert len(result.results) == 2
        assert result.results[0].url is None
        assert result.results[0].title is None
        assert result.results[1].url == "https://example.com/a"

    async def test_include_domains_included_when_provided(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json=success_payload()),
        )
        await client.search(QUERY, include_domains=["amazon.com", "target.com"])
        request = client._transport.requests[0]
        body = json.loads(request.content.decode())
        assert body["include_domains"] == ["amazon.com", "target.com"]
        assert "api_key" not in body
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"

    async def test_include_domains_omitted_when_absent(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json=success_payload()),
        )
        await client.search(QUERY)
        body = json.loads(client._transport.requests[0].content.decode())
        assert "include_domains" not in body
        assert "api_key" not in body

    async def test_request_body_contains_only_search_parameters(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json=success_payload()),
        )
        await client.search(QUERY)
        request = client._transport.requests[0]
        body = json.loads(request.content.decode())
        assert body == {
            "query": QUERY,
            "search_depth": "advanced",
            "max_results": 8,
            "include_answer": True,
        }
        assert "api_key" not in body
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"


@pytest.mark.anyio
class TestTavilyAuthentication:
    @pytest.mark.parametrize("status_code", [401, 403])
    async def test_authentication_errors(self, status_code: int):
        calls = {"count": 0}

        def handler(request, call):
            calls["count"] += 1
            return httpx.Response(status_code, json={"error": "auth failed"})

        client = build_client(make_settings(), handler)
        with pytest.raises(TavilyAuthenticationError, match=str(status_code)):
            await client.search(QUERY)
        assert calls["count"] == 1
        request = client._transport.requests[0]
        assert request.headers["Authorization"] == f"Bearer {API_KEY}"
        body = json.loads(request.content.decode())
        assert "api_key" not in body


@pytest.mark.anyio
class TestTavilyRateLimit:
    async def test_429_then_success_retries(self):
        responses = [
            httpx.Response(429, json={"error": "rate limit"}),
            httpx.Response(200, json=success_payload()),
        ]

        def handler(request, call):
            return responses[min(call - 1, len(responses) - 1)]

        sleeps: list[float] = []

        async def sleeper(delay: float) -> None:
            sleeps.append(delay)

        client = build_client(make_settings(tavily_max_retries=3), handler, sleeper=sleeper)
        result = await client.search(QUERY)
        assert result.answer.startswith("Typical retail price")
        assert len(client._transport.requests) == 2
        assert sleeps == [retry_delay(0)]

    async def test_repeated_429_raises_rate_limit_error(self):
        def handler(request, call):
            return httpx.Response(429, json={"error": "rate limit"})

        client = build_client(make_settings(tavily_max_retries=2), handler)
        with pytest.raises(TavilyRateLimitError):
            await client.search(QUERY)
        assert len(client._transport.requests) == 3


@pytest.mark.anyio
class TestTavilyServerFailures:
    @pytest.mark.parametrize("status_code", [500, 502, 503, 504])
    async def test_server_error_then_success(self, status_code: int):
        responses = [
            httpx.Response(status_code, json={"error": "server"}),
            httpx.Response(200, json=success_payload()),
        ]

        def handler(request, call):
            return responses[min(call - 1, len(responses) - 1)]

        client = build_client(make_settings(tavily_max_retries=3), handler)
        result = await client.search(QUERY)
        assert len(result.results) == 2
        assert len(client._transport.requests) == 2

    async def test_retries_exhausted_raises_http_error(self):
        def handler(request, call):
            return httpx.Response(503, json={"error": "unavailable"})

        client = build_client(make_settings(tavily_max_retries=2), handler)
        with pytest.raises(TavilyHTTPError, match="503") as exc_info:
            await client.search(QUERY)
        assert exc_info.value.retryable is True
        assert len(client._transport.requests) == 3


@pytest.mark.anyio
class TestTavilyOtherHttpErrors:
    async def test_400_does_not_retry(self):
        calls = {"count": 0}

        def handler(request, call):
            calls["count"] += 1
            return httpx.Response(400, json={"error": "bad request"})

        client = build_client(make_settings(tavily_max_retries=3), handler)
        with pytest.raises(TavilyHTTPError, match="400") as exc_info:
            await client.search(QUERY)
        assert exc_info.value.retryable is False
        assert calls["count"] == 1


@pytest.mark.anyio
class TestTavilyTimeout:
    async def test_timeout_then_success(self):
        class TimeoutThenSuccessTransport(httpx.AsyncBaseTransport):
            def __init__(self):
                self.calls = 0

            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                self.calls += 1
                if self.calls == 1:
                    raise httpx.ReadTimeout("timed out")
                return httpx.Response(200, json=success_payload())

        transport = TimeoutThenSuccessTransport()
        http_client = httpx.AsyncClient(transport=transport)
        client = TavilyClient(make_settings(tavily_max_retries=2), http_client=http_client, sleeper=_noop_sleep)
        result = await client.search(QUERY)
        assert result.answer is not None
        assert transport.calls == 2

    async def test_repeated_timeout_raises_timeout_error(self):
        class AlwaysTimeoutTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                raise httpx.ReadTimeout("timed out")

        http_client = httpx.AsyncClient(transport=AlwaysTimeoutTransport())
        client = TavilyClient(make_settings(tavily_max_retries=2), http_client=http_client, sleeper=_noop_sleep)
        with pytest.raises(TavilyTimeoutError):
            await client.search(QUERY)


@pytest.mark.anyio
class TestTavilyResponseValidation:
    async def test_non_object_json_raises_response_error(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json=["not", "an", "object"]),
        )
        with pytest.raises(TavilyResponseError, match="JSON object"):
            await client.search(QUERY)

    async def test_results_not_list_raises_response_error(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json={"answer": "ok", "results": "nope"}),
        )
        with pytest.raises(TavilyResponseError, match="results must be a list"):
            await client.search(QUERY)

    async def test_invalid_result_object_raises_response_error(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(
                200,
                json={"answer": None, "results": [{"content": 123}]},
            ),
        )
        with pytest.raises(TavilyResponseError, match="content"):
            await client.search(QUERY)

    async def test_valid_empty_response_remains_valid(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(200, json={"answer": None, "results": []}),
        )
        result = await client.search(QUERY)
        assert result.answer is None
        assert result.results == []


@pytest.mark.anyio
class TestTavilySecurityAndRetrySafety:
    async def test_exception_does_not_expose_api_key(self):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(401, json={"error": "bad key"}),
        )
        with pytest.raises(TavilyAuthenticationError) as exc_info:
            await client.search(QUERY)
        assert API_KEY not in str(exc_info.value)
        assert "Authorization" not in str(exc_info.value)
        assert "Bearer" not in str(exc_info.value)

    async def test_request_logs_do_not_include_api_key_in_exception(self, caplog):
        client = build_client(
            make_settings(),
            lambda request, call: httpx.Response(400, json={"error": "bad request"}),
        )
        with pytest.raises(TavilyHTTPError) as exc_info:
            await client.search(QUERY)
        assert API_KEY not in str(exc_info.value)
        assert "Authorization" not in str(exc_info.value)
        assert API_KEY not in caplog.text
        assert "Authorization" not in caplog.text

    async def test_max_retry_count_respected(self):
        def handler(request, call):
            return httpx.Response(503, json={"error": "down"})

        client = build_client(make_settings(tavily_max_retries=3), handler)
        with pytest.raises(TavilyHTTPError):
            await client.search(QUERY)
        assert len(client._transport.requests) == 4

    async def test_permanent_errors_are_not_retried(self):
        def handler(request, call):
            return httpx.Response(404, json={"error": "missing"})

        client = build_client(make_settings(tavily_max_retries=3), handler)
        with pytest.raises(TavilyHTTPError) as exc_info:
            await client.search(QUERY)
        assert exc_info.value.retryable is False
        assert len(client._transport.requests) == 1

    async def test_retry_delay_is_exponential(self):
        assert retry_delay(0) == 0.25
        assert retry_delay(1) == 0.5
        assert retry_delay(2) == 1.0
