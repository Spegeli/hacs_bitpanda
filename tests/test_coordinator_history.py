"""Tests for the portfolio history coordinator."""
import aiohttp
from aioresponses import aioresponses

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
