"""Tests for the portfolio history coordinator."""
import aiohttp
import pytest
from aioresponses import aioresponses
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.bitpanda.api import BitpandaApiClient
from custom_components.bitpanda.const import API_BASE_URL, PORTFOLIO_TIMEFRAMES
from custom_components.bitpanda.coordinator import collect_returns


async def test_collect_returns_one_entry_per_timeframe():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            for index, timeframe in enumerate(PORTFOLIO_TIMEFRAMES):
                m.get(
                    f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                    payload={"data": {"datapoints": [],
                                      "return_percentage": float(index)}},
                )
            result = await collect_returns(client, None)
    assert result == {tf: float(i) for i, tf in enumerate(PORTFOLIO_TIMEFRAMES)}


async def test_collect_returns_skips_a_failing_timeframe():
    """One bad window must not lose the other four."""
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            for timeframe in PORTFOLIO_TIMEFRAMES:
                if timeframe == "YEAR":
                    m.get(
                        f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                        status=500,
                    )
                else:
                    m.get(
                        f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                        payload={"data": {"return_percentage": 1.0}},
                    )
            result = await collect_returns(client, None)
    assert "YEAR" not in result
    assert len(result) == len(PORTFOLIO_TIMEFRAMES) - 1


async def test_collect_returns_raises_when_every_timeframe_fails():
    """A dead endpoint must not look like an empty result."""
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            for timeframe in PORTFOLIO_TIMEFRAMES:
                m.get(
                    f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                    status=500,
                )
            with pytest.raises(UpdateFailed):
                await collect_returns(client, None)


async def test_collect_returns_drops_a_boolean_percentage():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            for timeframe in PORTFOLIO_TIMEFRAMES:
                payload = {"data": {"return_percentage":
                                    True if timeframe == "DAY" else 1.5}}
                m.get(
                    f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                    payload=payload,
                )
            result = await collect_returns(client, None)
    assert "DAY" not in result
    assert len(result) == len(PORTFOLIO_TIMEFRAMES) - 1


async def test_collect_returns_is_quiet_when_history_is_genuinely_empty():
    """All five answer, none carries a usable value. Not an outage."""
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            for timeframe in PORTFOLIO_TIMEFRAMES:
                m.get(
                    f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                    payload={"data": {"datapoints": [],
                                      "return_percentage": None}},
                )
            result = await collect_returns(client, None)
    assert result == {}
