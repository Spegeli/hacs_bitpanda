"""Tests for asset and currency retrieval."""
import asyncio

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
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
async def test_paginate_raises_when_cursor_does_not_advance():
    """The server emits cursors it then ignores, re-serving the same page.

    Stopping there quietly would hand back page 1 as if it were the whole
    listing -- exactly how lifetime reward totals were once published at a
    fraction of their true value -- so a cursor that was already sent raises
    instead, after the second request.

    `asyncio.wait_for` alone cannot bound a regression here: the mock never
    awaits a real unresolved Future (no socket I/O), so a stuck loop never
    yields to the event loop and cooperative cancellation never gets
    delivered. Only pytest-timeout's signal-based (preemptive) timeout
    actually interrupts it, hence the marker.
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
            with pytest.raises(BitpandaApiError, match="/assets"):
                await asyncio.wait_for(client.async_get_assets(), timeout=5)
            assert mocker.call_count == 2


# --- async_list_assets ---------------------------------------------------
#
# Builds the category pickers of the "Add price tracker" subentry flow. The
# mock's own URL matching is a subset match (every param in the registration
# must be present in the request, but extra params on the request still
# match) -- see AiohttpClientMockResponse.match_request -- so an accidental
# extra parameter would pass unnoticed there. The exact query string is
# asserted directly from mocker.mock_calls instead.


async def test_list_assets_sends_exactly_type_group_and_page_size():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets",
            json={"data": [], "has_next_page": False},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            await client.async_list_assets("commodity", "metal")

    assert mocker.call_count == 1
    _, url, _, _ = mocker.mock_calls[0]
    assert dict(url.query) == {
        "type": "commodity",
        "group": "metal",
        "page_size": "100",
    }


async def test_list_assets_without_a_group_omits_the_group_param():
    """crypto's filter is (\"cryptocoin\", None): every cryptocoin sub-group
    (coin, token, leveraged_token, security_token) belongs to the category,
    so nothing narrows by group.
    """
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets",
            json={"data": [], "has_next_page": False},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            await client.async_list_assets("cryptocoin", None)

    _, url, _, _ = mocker.mock_calls[0]
    assert dict(url.query) == {"type": "cryptocoin", "page_size": "100"}


async def test_list_assets_paginates():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets?cursor=CUR&page_size=100&type=index",
            json={"data": [{"id": "b"}], "has_next_page": False},
        )
        mocker.get(
            f"{API_BASE_URL}/assets?page_size=100&type=index",
            json={
                "data": [{"id": "a"}],
                "next_cursor": "CUR",
                "has_next_page": True,
            },
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_list_assets("index", None)
    assert [a["id"] for a in result] == ["a", "b"]


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
