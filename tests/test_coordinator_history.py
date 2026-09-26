"""Tests for the portfolio history coordinator."""
import asyncio

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.bitpanda.api import BitpandaApiClient, BitpandaAuthError
from custom_components.bitpanda.const import API_BASE_URL, PORTFOLIO_TIMEFRAMES
from custom_components.bitpanda.portfolio_coordinator import (
    HistoryCoordinator,
    collect_returns,
)
from custom_components.bitpanda.portfolio_model import PortfolioReturns


async def test_collect_returns_one_entry_per_timeframe():
    with mock_aiohttp_client() as mocker:
        for index, timeframe in enumerate(PORTFOLIO_TIMEFRAMES):
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json={"data": {"datapoints": [],
                                "return_percentage": float(index)}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert result == PortfolioReturns(
        values={tf: float(i) for i, tf in enumerate(PORTFOLIO_TIMEFRAMES)}, failed=frozenset()
    )


async def test_collect_returns_skips_a_failing_timeframe():
    """One bad window must not lose the other four -- and is told apart from
    a timeframe answered without a figure: its own request failed."""
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            if timeframe == "YEAR":
                mocker.get(
                    f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                    status=500,
                )
            else:
                mocker.get(
                    f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                    json={"data": {"return_percentage": 1.0}},
                )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert "YEAR" not in result.values
    assert len(result.values) == len(PORTFOLIO_TIMEFRAMES) - 1
    assert result.failed == {"YEAR"}


async def test_collect_returns_raises_when_every_timeframe_fails():
    """A dead endpoint must not look like an empty result."""
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                status=500,
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(UpdateFailed) as excinfo:
                await collect_returns(client, None)
    assert (excinfo.value.translation_domain, excinfo.value.translation_key) == (
        "bitpanda", "history_unavailable"
    )


async def test_collect_returns_drops_a_boolean_percentage():
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            payload = {"data": {"return_percentage":
                                True if timeframe == "DAY" else 1.5}}
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json=payload,
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert "DAY" not in result.values
    assert len(result.values) == len(PORTFOLIO_TIMEFRAMES) - 1
    # Answered, just without a usable figure: not a failed request.
    assert result.failed == frozenset()


async def test_collect_returns_parses_a_numeric_string_percentage():
    """The API now sends return_percentage as a JSON string; numbers must
    still work too, so each timeframe here uses a different value shape."""
    values = {
        "DAY": "0.73",
        "WEEK": " 7.22 ",
        "MONTH": 1.5,
        "SIX_MONTH": 2,
        "YEAR": "3.14",
    }
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json={"data": {"return_percentage": values[timeframe]}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert result.values == {
        "DAY": 0.73,
        "WEEK": 7.22,
        "MONTH": 1.5,
        "SIX_MONTH": 2.0,
        "YEAR": 3.14,
    }


async def test_collect_returns_drops_unparsable_or_non_finite_percentage_strings():
    """A string must parse to a finite number or the timeframe is dropped,
    same as today's rule for every other unusable value."""
    values = {
        "DAY": "n/a",
        "WEEK": "nan",
        "MONTH": "inf",
        "SIX_MONTH": 1.0,
        "YEAR": 1.0,
    }
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json={"data": {"return_percentage": values[timeframe]}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert result == PortfolioReturns(
        values={"SIX_MONTH": 1.0, "YEAR": 1.0}, failed=frozenset()
    )


class _Returns:
    """Fake API client answering each timeframe with its own value."""

    def __init__(self, values):
        self._values = values

    async def async_get_portfolio_history(self, *, timeframe, equivalent_currency_id=None):
        return {"return_percentage": self._values[timeframe]}


async def test_collect_returns_drops_non_finite_numbers():
    """A JSON number goes through the same finite check as a numeric string:
    Python's json module reads the literals Infinity and NaN as floats."""
    values = {
        "DAY": float("inf"),
        "WEEK": float("-inf"),
        "MONTH": float("nan"),
        "SIX_MONTH": 1.0,
        "YEAR": 2,
    }
    assert await collect_returns(_Returns(values), None) == PortfolioReturns(
        values={"SIX_MONTH": 1.0, "YEAR": 2.0}, failed=frozenset()
    )


async def test_collect_returns_is_quiet_when_history_is_genuinely_empty():
    """All five answer, none carries a usable value. Not an outage."""
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json={"data": {"datapoints": [],
                                "return_percentage": None}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert result == PortfolioReturns(values={}, failed=frozenset())


async def test_collect_returns_reraises_auth_error_instead_of_counting_it():
    """An auth error must propagate immediately, not be treated as one of
    five failed timeframes -- otherwise a 401 on every timeframe reads as
    "No portfolio history could be fetched" (UpdateFailed) instead of the
    BitpandaAuthError the coordinator needs to start reauth.

    Only the first timeframe is registered, with a 401. If the
    implementation kept looping past it instead of re-raising, the next
    request would hit an unregistered URL and this test would fail for a
    different reason, which is exactly the point of leaving it unregistered
    (see test_api_scopes.py for the same technique).
    """
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/portfolio-history?"
            f"timeframe={PORTFOLIO_TIMEFRAMES[0]}",
            status=401,
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaAuthError):
                await collect_returns(client, None)


# ---------------------------------------------------------------------------
# HistoryCoordinator._async_update_data
#
# DataUpdateCoordinator.__init__ only stores `hass`, so hass=None/entry=None
# is enough to drive _async_update_data() directly.
# ---------------------------------------------------------------------------


class _FakeClient:
    """Fake API client whose async_get_portfolio_history always fails alike."""

    def __init__(self, error):
        self._error = error

    async def async_get_portfolio_history(
        self, *, timeframe, equivalent_currency_id=None
    ):
        raise self._error


async def test_history_coordinator_raises_config_entry_auth_failed_on_401():
    client = _FakeClient(BitpandaAuthError("Unauthorized for /portfolio-history"))
    coordinator = HistoryCoordinator(
        hass=None, entry=None, client=client, currency_id=None
    )

    with pytest.raises(ConfigEntryAuthFailed) as excinfo:
        await coordinator._async_update_data()
    assert (excinfo.value.translation_domain, excinfo.value.translation_key) == (
        "bitpanda", "api_key_rejected"
    )
