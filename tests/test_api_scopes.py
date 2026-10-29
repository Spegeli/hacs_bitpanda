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

# Bitcoin's asset ID: the Trade (Read) probe asks for its ticker.
_BITCOIN = "b86c034b-efe3-11eb-b56f-0691764446a7"
_TICKER = f"{API_BASE_URL}/tickers/{_BITCOIN}"


def test_scope_constants_stay_in_sync():
    """REQUIRED_SCOPES (const.py) and _SCOPE_PROBES (api.py) list the same
    scopes by hand in two places. A drift between them would surface as a
    KeyError at setup time -- _SCOPE_PROBES[scope] in async_missing_scopes --
    rather than fail a test. The missing-permissions error's placeholders are
    named after REQUIRED_SCOPES; tests/test_strings.py checks every text uses
    exactly those.
    """
    assert set(REQUIRED_SCOPES) == set(_SCOPE_PROBES)


def test_every_required_scope_has_its_probe():
    """Since 2026-10-28 Bitpanda gives prices (/tickers) only to a key with
    Trade (Read): the integration needs four permissions, and the setup
    probes each -- Trade (Read) with Bitcoin's ticker, the very request the
    integration needs it for."""
    assert set(_SCOPE_PROBES) == set(REQUIRED_SCOPES) == {
        "balance", "transaction", "earn", "trading"
    }
    assert _SCOPE_PROBES["trading"] == (f"/tickers/{_BITCOIN}", None)


async def test_a_key_without_trade_read_lacks_trading():
    """A key made as 2.1.0 told: Balances, Transaction and Earn (Read), no
    Trade (Read). The ticker answers it 401, everything else 200 -- /assets
    too, which on 2026-10-29 answered every key, even none, at times."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json={"data": []})
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", json={"data": []})
        mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", json={"data": []})
        mocker.get(f"{API_BASE_URL}/assets?page_size=1", json={"data": []})
        mocker.get(_TICKER, status=401)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_missing_scopes()

    assert result == ["trading"]


async def test_all_scopes_present_returns_empty_list():
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json={"data": []})
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", json={"data": []})
        mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", json={"data": []})
        mocker.get(_TICKER, json={"data": {"asset_id": _BITCOIN, "price": "71976.27"}})
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_missing_scopes()

    assert result == []
    # Subset matching would accept a request carrying extra parameters, so
    # prove exactly what was sent for each probe, in probe order.
    assert mocker.mock_calls[0][1].query_string == ""
    assert mocker.mock_calls[1][1].query_string == "page_size=1"
    assert mocker.mock_calls[2][1].query_string == "page_size=1"
    assert str(mocker.mock_calls[3][1]) == _TICKER
    assert mocker.mock_calls[3][1].query_string == ""


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


async def test_a_ticker_probe_failing_otherwise_tells_nothing_about_the_scope():
    """Trade (Read) is probed with one asset's ticker. Should that ticker
    answer 404 -- the asset gone, the path moved -- or 500, the probe tells
    nothing about the key: the error propagates (setup then says it could
    not connect) instead of the scope counting as granted or missing."""
    for status in (404, 500):
        with mock_aiohttp_client() as mocker:
            mocker.get(f"{API_BASE_URL}/portfolio", json={"data": []})
            mocker.get(f"{API_BASE_URL}/operations?page_size=1", json={"data": []})
            mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", json={"data": []})
            mocker.get(_TICKER, status=status)
            async with mocker.create_session(asyncio.get_running_loop()) as session:
                client = BitpandaApiClient("key", session)
                with pytest.raises(BitpandaApiError) as excinfo:
                    await client.async_missing_scopes()

        assert type(excinfo.value) is BitpandaApiError, status
        assert (excinfo.value.path, excinfo.value.status) == (f"/tickers/{_BITCOIN}", status)


async def test_missing_transaction_and_earn_scopes():
    """A Guthaben-only key: /portfolio works, /operations and /earn/configs don't."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", json={"data": []})
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", status=401)
        mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", status=401)
        mocker.get(_TICKER, json={"data": {"asset_id": _BITCOIN, "price": "71976.27"}})
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_missing_scopes()

    # Order follows REQUIRED_SCOPES ("balance", "transaction", "earn",
    # "trading"), not
    # the order the probes were registered above.
    assert result == ["transaction", "earn"]


async def test_all_scopes_missing_returns_all_four():
    """A wrong key and a key with none of the required scopes look identical."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", status=401)
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", status=401)
        mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", status=401)
        mocker.get(_TICKER, status=401)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_missing_scopes()

    assert result == ["balance", "transaction", "earn", "trading"]


async def test_a_made_up_key_lacks_every_scope_while_assets_answers_everyone():
    """On 2026-10-29 /assets answered a made-up key 200 at times: a probe
    there showed Trade (Read) as granted for a key that does not exist. The
    ticker still refuses it, so every scope is missing -- which setup reads
    as a wrong key."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/portfolio", status=401)
        mocker.get(f"{API_BASE_URL}/operations?page_size=1", status=401)
        mocker.get(f"{API_BASE_URL}/earn/configs?page_size=1", status=401)
        mocker.get(f"{API_BASE_URL}/assets?page_size=1", json={"data": []})
        mocker.get(_TICKER, status=401)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("made-up", session)
            result = await client.async_missing_scopes()

    assert result == ["balance", "transaction", "earn", "trading"]


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
