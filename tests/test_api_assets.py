"""Tests for asset and currency retrieval."""
import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from custom_components.bitpanda.const import API_BASE_URL

from tests.conftest import load_fixture


async def test_get_currencies_returns_all_twelve():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/currencies",
                payload={"data": load_fixture("currencies.json")},
            )
            result = await client.async_get_currencies()
    assert len(result) == 12
    assert any(c["symbol"] == "EUR" for c in result)


async def test_get_assets_by_symbol():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/assets?page_size=100&symbol=BTC",
                payload={
                    "data": [{"id": "uuid-btc", "symbol": "BTC", "type": "cryptocoin"}],
                    "has_next_page": False,
                },
            )
            result = await client.async_get_assets(symbol="BTC")
    assert result[0]["id"] == "uuid-btc"


async def test_get_assets_follows_pagination():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/assets?page_size=100",
                payload={
                    "data": [{"id": "a", "symbol": "A"}],
                    "next_cursor": "CUR",
                    "has_next_page": True,
                },
            )
            m.get(
                f"{API_BASE_URL}/assets?cursor=CUR&page_size=100",
                payload={"data": [{"id": "b", "symbol": "B"}], "has_next_page": False},
            )
            result = await client.async_get_assets()
    assert [a["id"] for a in result] == ["a", "b"]


async def test_401_raises_auth_error():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(f"{API_BASE_URL}/currencies", status=401)
            with pytest.raises(BitpandaAuthError):
                await client.async_get_currencies()


async def test_429_raises_rate_limit_error():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(f"{API_BASE_URL}/currencies", status=429)
            with pytest.raises(BitpandaRateLimitError):
                await client.async_get_currencies()
