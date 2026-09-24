"""Tests for ticker, portfolio and portfolio history."""
import asyncio

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import BitpandaApiClient, BitpandaApiError
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


async def test_null_data_becomes_an_empty_result():
    """dict.get's default does not apply to a present-but-null key."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json={"data": None})
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            assert await client.async_get_portfolio() == []
