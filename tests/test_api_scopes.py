"""Tests for async_missing_scopes, the setup-time scope probe.

Bitpanda answers a wrong key and a key missing a scope with the identical
401 body, so a single probe cannot tell them apart. `async_missing_scopes`
sends one request per required scope and reports which ones came back 401.
"""
import asyncio

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaRateLimitError,
    _SCOPE_PROBES,
)
from custom_components.bitpanda.const import API_BASE_URL, REQUIRED_SCOPES


def test_scope_constants_stay_in_sync():
    """REQUIRED_SCOPES (const.py) and _SCOPE_PROBES (api.py) list the same
    scopes by hand in two places. A drift between them would surface as a
    KeyError at setup time -- _SCOPE_PROBES[scope] in async_missing_scopes --
    rather than fail a test. The missing-permissions error's placeholders are
    named after REQUIRED_SCOPES; tests/test_strings.py checks every text uses
    exactly those.
    """
    assert set(REQUIRED_SCOPES) == set(_SCOPE_PROBES)


async def test_all_scopes_present_returns_empty_list():
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json={"data": []})
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", json={"data": []})
        mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", json={"data": []})
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_missing_scopes()

    assert result == []
    # Subset matching would accept a request carrying extra parameters, so
    # prove exactly what was sent for each probe, in probe order.
    assert mocker.mock_calls[0][1].query_string == ""
    assert mocker.mock_calls[1][1].query_string == "page_size=1"
    assert mocker.mock_calls[2][1].query_string == "page_size=1"


async def test_a_probe_answered_unreadably_is_no_granted_scope():
    """A probe whose answer cannot be read tells nothing about its scope:
    the error propagates -- setup then says it could not connect -- instead
    of the scope counting as granted."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json=["not", "an", "object"])
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaApiError) as excinfo:
                await client.async_missing_scopes()

    assert (excinfo.value.kind, excinfo.value.path) == ("unreadable", "/portfolio")


async def test_missing_transaction_and_earn_scopes():
    """A Guthaben-only key: /portfolio works, /operations and /earn/configs don't."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json={"data": []})
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", status=401)
        mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", status=401)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_missing_scopes()

    # Order follows REQUIRED_SCOPES ("balance", "transaction", "earn"), not
    # the order the probes were registered above.
    assert result == ["transaction", "earn"]


async def test_all_scopes_missing_returns_all_three():
    """A wrong key and a key with none of the required scopes look identical."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", status=401)
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", status=401)
        mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", status=401)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_missing_scopes()

    assert result == ["balance", "transaction", "earn"]


async def test_rate_limit_propagates_instead_of_counting_as_missing():
    """A 429 is not a missing scope: it must raise, not appear in the list."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json={"data": []})
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", status=429)
        # /earn/configs is deliberately left unregistered: a correct
        # implementation stops at the rate limit and never reaches it.
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaRateLimitError):
                await client.async_missing_scopes()
