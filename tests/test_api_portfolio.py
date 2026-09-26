"""Tests for ticker, portfolio and portfolio history."""
import asyncio
import logging
from unittest.mock import patch

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from custom_components.bitpanda.const import API_BASE_URL, EUR_CURRENCY_ID


async def test_get_ticker_returns_price_and_currency():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/tickers/uuid-btc",
            json={
                "data": {
                    "asset_id": "uuid-btc",
                    "price": "73188.51648958",
                    "currency_id": EUR_CURRENCY_ID,
                }
            },
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_ticker("uuid-btc")
    assert result["price"] == "73188.51648958"
    assert result["currency_id"] == EUR_CURRENCY_ID
    assert result["asset_id"] == "uuid-btc"


async def test_get_portfolio_passes_equivalent_currency():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/portfolio?equivalent_currency_id=uuid-usd",
            json={"data": [{"asset_id": "a"}]},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_portfolio(
                equivalent_currency_id="uuid-usd"
            )
    assert result == [{"asset_id": "a"}]
    # Subset matching only proves the currency id was present, not that
    # nothing else rode along with it.
    assert mocker.mock_calls[0][1].query_string == "equivalent_currency_id=uuid-usd"


async def test_get_portfolio_history_uses_timeframe():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/portfolio-history?timeframe=WEEK",
            json={
                "data": {
                    "datapoints": [{"time": "t", "value": {"value": "1"}}],
                    "return_percentage": 6.24,
                }
            },
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_portfolio_history(timeframe="WEEK")
    assert result["return_percentage"] == 6.24
    assert len(result["datapoints"]) == 1
    # Subset matching only proves timeframe=WEEK was present, not that no
    # other parameter (e.g. a stray equivalent_currency_id) rode along.
    assert mocker.mock_calls[0][1].query_string == "timeframe=WEEK"


async def test_get_portfolio_sends_no_params_when_no_currency():
    """`params or None` keeps an empty dict out of the request."""
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/portfolio",
            json={"data": [{"asset_id": "a"}]},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_portfolio()
    assert result == [{"asset_id": "a"}]
    # Subset matching means a mock registered with no query would also accept
    # a request carrying extra parameters, so `result` alone can't prove the
    # request was param-free — assert on what was actually sent.
    assert mocker.mock_calls[0][1].query_string == ""


async def test_get_portfolio_history_defaults_to_day():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/portfolio-history?timeframe=DAY",
            json={"data": {"datapoints": [], "return_percentage": -0.64}},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_portfolio_history()
    assert result["return_percentage"] == -0.64
    # Same subset-matching gap as the no-currency portfolio test: prove the
    # default is exactly `timeframe=DAY` alone, nothing extra.
    assert mocker.mock_calls[0][1].query_string == "timeframe=DAY"


async def test_malformed_json_becomes_an_api_error():
    with mock_aiohttp_client() as mocker:
        # AiohttpClientMockResponse takes no `body=`/`content_type=` kwargs;
        # `text=` sets the raw response body and this mocker's `.json()`
        # decodes it unconditionally, so a malformed string still reaches the
        # api.py json() call and fails to parse there.
        mocker.get(f"{API_BASE_URL}/portfolio", text="not json{")
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaApiError):
                await client.async_get_portfolio()


async def test_request_failures_are_logged_at_debug_only(caplog):
    """The coordinators already report an outage once. A line per failed
    request at ERROR meant hundreds of lines an hour during an outage, and a
    delisted asset's ticker 404 every 60 seconds for good.
    """
    caplog.set_level(logging.DEBUG, logger="custom_components.bitpanda.api")
    secret = "totally-secret-key"
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/tickers/http", status=500)
        mocker.get(
            f"{API_BASE_URL}/tickers/conn", exc=aiohttp.ClientConnectionError()
        )
        mocker.get(f"{API_BASE_URL}/tickers/slow", exc=asyncio.TimeoutError())
        mocker.get(f"{API_BASE_URL}/tickers/json", text="not json{")
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient(secret, session)
            for asset_id in ("http", "conn", "slow", "json"):
                with pytest.raises(BitpandaApiError):
                    await client.async_get_ticker(asset_id)

    records = [r for r in caplog.records if r.name == "custom_components.bitpanda.api"]
    assert len(records) == 4
    assert {r.levelno for r in records} == {logging.DEBUG}
    assert all(r.exc_info is None for r in records)
    assert secret not in caplog.text


@pytest.mark.parametrize(
    ("response", "error", "kind", "status"),
    [
        ({"status": 500}, BitpandaApiError, "http_status", 500),
        ({"status": 302}, BitpandaApiError, "http_status", 302),
        ({"status": 401}, BitpandaAuthError, "http_status", 401),
        ({"status": 429}, BitpandaRateLimitError, "http_status", 429),
        ({"exc": aiohttp.ClientConnectionError("details")}, BitpandaApiError, "connection", None),
        ({"exc": asyncio.TimeoutError()}, BitpandaApiError, "timeout", None),
        ({"text": "not json{"}, BitpandaApiError, "unreadable", None),
    ],
    ids=["http", "redirect", "unauthorized", "rate_limited", "connection", "timeout", "unreadable"],
)
async def test_a_failed_request_says_what_failed_without_words(response, error, kind, status):
    """Beside its English message for the log, every failure carries what
    failed in a form a translation can use: its kind, the request path and
    an HTTP status -- no words, and never the key."""
    secret = "totally-secret-key"
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", **response)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient(secret, session)
            with pytest.raises(error) as excinfo:
                await client.async_get_portfolio()
    assert (excinfo.value.kind, excinfo.value.path, excinfo.value.status) == (
        kind, "/portfolio", status
    )
    assert secret not in repr(vars(excinfo.value))


async def test_a_redirect_is_an_error():
    """The API never redirects: a 3xx fails with a fixed message instead of
    passing off whatever body came with it."""
    secret = "totally-secret-key"
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/portfolio",
            status=302,
            headers={"Location": "https://elsewhere.example/collect"},
            json={"data": [{"asset_id": "a"}]},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient(secret, session)
            with pytest.raises(BitpandaApiError) as raised:
                await client.async_get_portfolio()
    assert str(raised.value) == "Unexpected redirect from /portfolio"
    assert secret not in str(raised.value)


async def _error_of(request) -> str | None:
    try:
        await request
    except BitpandaApiError as err:
        return str(err)
    return None


async def test_the_key_never_follows_a_redirect_to_another_host(socket_enabled):
    """When a redirect leaves the origin, aiohttp drops an Authorization
    header but forwards x-api-key to the new host -- so the client must not
    follow redirects at all. Two local servers stand in for Bitpanda and for
    the host a redirect points to."""
    secret = "totally-secret-key"
    received: list[str | None] = []

    async def collect(request: web.Request) -> web.Response:
        received.append(request.headers.get("x-api-key"))
        return web.json_response({"data": []})

    elsewhere = web.Application()
    elsewhere.router.add_get("/collect", collect)
    async with TestServer(elsewhere) as elsewhere_server:

        async def redirect(request: web.Request) -> web.Response:
            raise web.HTTPFound(str(elsewhere_server.make_url("/collect")))

        bitpanda = web.Application()
        bitpanda.router.add_get("/v1/portfolio", redirect)
        async with TestServer(bitpanda) as bitpanda_server, aiohttp.ClientSession() as session:
            client = BitpandaApiClient(secret, session)
            with patch(
                "custom_components.bitpanda.api.API_BASE_URL",
                str(bitpanda_server.make_url("/v1")),
            ):
                error = await _error_of(client.async_get_portfolio())

    assert received == []
    assert error == "Unexpected redirect from /portfolio"


async def test_a_page_that_is_no_json_is_an_unreadable_answer(socket_enabled):
    """A 200 answer that is no JSON -- a maintenance or captive-portal page
    served as text/html -- is an answer that could not be read, not a failed
    HTTP status: aiohttp refuses its content type with ContentTypeError, an
    HTTP-status error class that carries the 200. A real server, because
    the test mocker's json() never checks the content type."""
    secret = "totally-secret-key"

    async def maintenance(request: web.Request) -> web.Response:
        return web.Response(text="<html>Down for maintenance</html>", content_type="text/html")

    bitpanda = web.Application()
    bitpanda.router.add_get("/v1/portfolio", maintenance)
    async with TestServer(bitpanda) as server, aiohttp.ClientSession() as session:
        client = BitpandaApiClient(secret, session)
        with patch("custom_components.bitpanda.api.API_BASE_URL", str(server.make_url("/v1"))):
            with pytest.raises(BitpandaApiError) as excinfo:
                await client.async_get_portfolio()

    assert (excinfo.value.kind, excinfo.value.path, excinfo.value.status) == (
        "unreadable", "/portfolio", None
    )
    assert str(excinfo.value) == "Could not decode response from /portfolio"
    assert excinfo.value.__cause__ is None
    assert secret not in repr(vars(excinfo.value))


async def test_null_data_becomes_an_empty_result():
    """dict.get's default does not apply to a present-but-null key."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json={"data": None})
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            assert await client.async_get_portfolio() == []
