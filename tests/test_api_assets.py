"""Tests for asset and currency retrieval."""
import asyncio

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from custom_components.bitpanda.const import API_BASE_URL

from tests.conftest import load_fixture


async def test_get_currencies_returns_all_twelve():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/currencies",
            json={"data": load_fixture("currencies.json")},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_currencies()
    assert len(result) == 12
    assert any(c["symbol"] == "EUR" for c in result)


async def test_get_assets_by_symbol():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets?page_size=100&symbol=BTC",
            json={
                "data": [{"id": "uuid-btc", "symbol": "BTC", "type": "cryptocoin"}],
                "has_next_page": False,
            },
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_assets(symbol="BTC")
    assert result[0]["id"] == "uuid-btc"


async def test_get_assets_follows_pagination():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets?cursor=CUR&page_size=100",
            json={"data": [{"id": "b", "symbol": "B"}], "has_next_page": False},
        )
        mocker.get(
            f"{API_BASE_URL}/assets?page_size=100",
            json={
                "data": [{"id": "a", "symbol": "A"}],
                "next_cursor": "CUR",
                "has_next_page": True,
            },
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_assets()
    assert [a["id"] for a in result] == ["a", "b"]


@pytest.mark.timeout(5)
async def test_paginate_stops_when_cursor_does_not_advance():
    """The server emits cursors it then ignores, re-serving the same page.

    `asyncio.wait_for` alone cannot bound this: the mock never awaits a real
    unresolved Future (no socket I/O), so a stuck loop never yields to the
    event loop and cooperative cancellation never gets delivered. Only
    pytest-timeout's signal-based (preemptive) timeout actually interrupts
    it, hence the marker.
    """
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets?cursor=STUCK&page_size=100",
            json={"data": [{"id": "a"}], "next_cursor": "STUCK",
                  "has_next_page": True},
        )
        mocker.get(
            f"{API_BASE_URL}/assets?page_size=100",
            json={"data": [{"id": "a"}], "next_cursor": "STUCK",
                  "has_next_page": True},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await asyncio.wait_for(client.async_get_assets(), timeout=5)
            assert mocker.call_count == 2
    assert [a["id"] for a in result] == ["a"]


async def test_401_raises_auth_error():
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/currencies", status=401)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaAuthError):
                await client.async_get_currencies()


async def test_429_raises_rate_limit_error():
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/currencies", status=429)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaRateLimitError):
                await client.async_get_currencies()
