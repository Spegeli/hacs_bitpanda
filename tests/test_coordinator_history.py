"""Tests for the portfolio history coordinator."""
import asyncio

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.bitpanda.api import BitpandaApiClient
from custom_components.bitpanda.const import API_BASE_URL, PORTFOLIO_TIMEFRAMES
from custom_components.bitpanda.coordinator import collect_returns


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
    assert result == {tf: float(i) for i, tf in enumerate(PORTFOLIO_TIMEFRAMES)}


async def test_collect_returns_skips_a_failing_timeframe():
    """One bad window must not lose the other four."""
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
    assert "YEAR" not in result
    assert len(result) == len(PORTFOLIO_TIMEFRAMES) - 1


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
            with pytest.raises(UpdateFailed):
                await collect_returns(client, None)


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
    assert "DAY" not in result
    assert len(result) == len(PORTFOLIO_TIMEFRAMES) - 1


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
    assert result == {}
