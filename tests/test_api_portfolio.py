"""Tests for ticker, portfolio and portfolio history."""
import aiohttp
from aioresponses import aioresponses

from custom_components.bitpanda.api import BitpandaApiClient
from custom_components.bitpanda.const import API_BASE_URL, EUR_CURRENCY_ID


async def test_get_ticker_returns_price_and_currency():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/tickers/uuid-btc",
                payload={
                    "data": {
                        "asset_id": "uuid-btc",
                        "price": "73188.51648958",
                        "currency_id": EUR_CURRENCY_ID,
                    }
                },
            )
            result = await client.async_get_ticker("uuid-btc")
    assert result["price"] == "73188.51648958"
    assert result["currency_id"] == EUR_CURRENCY_ID
    assert result["asset_id"] == "uuid-btc"


async def test_get_portfolio_passes_equivalent_currency():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/portfolio?equivalent_currency_id=uuid-usd",
                payload={"data": [{"asset_id": "a"}]},
            )
            result = await client.async_get_portfolio(
                equivalent_currency_id="uuid-usd"
            )
    assert result == [{"asset_id": "a"}]


async def test_get_portfolio_history_uses_timeframe():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/portfolio-history?timeframe=WEEK",
                payload={
                    "data": {
                        "datapoints": [{"time": "t", "value": {"value": "1"}}],
                        "return_percentage": 6.24,
                    }
                },
            )
            result = await client.async_get_portfolio_history(timeframe="WEEK")
    assert result["return_percentage"] == 6.24
    assert len(result["datapoints"]) == 1


async def test_get_portfolio_sends_no_params_when_no_currency():
    """`params or None` keeps an empty dict out of the request."""
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/portfolio",
                payload={"data": [{"asset_id": "a"}]},
            )
            result = await client.async_get_portfolio()
    assert result == [{"asset_id": "a"}]


async def test_get_portfolio_history_defaults_to_day():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/portfolio-history?timeframe=DAY",
                payload={"data": {"datapoints": [], "return_percentage": -0.64}},
            )
            result = await client.async_get_portfolio_history()
    assert result["return_percentage"] == -0.64
