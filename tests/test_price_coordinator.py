"""Tests for the keyless ticker coordinator and the ECB coordinator."""
from datetime import timedelta
import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.ecb import EcbError, EcbRates
from custom_components.bitpanda.price_coordinator import (
    EcbCoordinator,
    TickerCoordinator,
    convert_price,
    price_interval,
)

BTC = "b86c034b-efe3-11eb-b56f-0691764446a7"
SOL = "b86da33d-efe3-11eb-b56f-0691764446a7"
_TRACKED = {BTC: "Bitcoin (BTC)", SOL: "Solana (SOL)"}


# --- price_interval -----------------------------------------------------------


def test_interval_is_sixty_seconds_up_to_thirty_assets():
    assert price_interval(0) == timedelta(seconds=60)
    assert price_interval(30) == timedelta(seconds=60)


def test_interval_stretches_above_thirty_assets():
    assert price_interval(31) > timedelta(seconds=60)
    assert price_interval(60) == timedelta(seconds=120)


def test_interval_keeps_every_count_inside_the_budget():
    for count in (1, 30, 31, 100, 900, 5000):
        per_hour = count * 3600 / price_interval(count).total_seconds()
        assert per_hour <= 1800 + 1e-6


# --- convert_price ---------------------------------------------------------------


def test_convert_price_without_rate_is_the_eur_price():
    assert convert_price("73188.51648958", None) == 73188.51648958


def test_convert_price_applies_the_rate_and_rounds():
    assert convert_price("0.10000000", 3.0) == 0.3
    assert convert_price("100.00000000", 1.1367) == 113.67


def test_convert_price_of_garbage_is_none():
    assert convert_price("n/a", None) is None
    assert convert_price(None, 1.1) is None


# --- TickerCoordinator -------------------------------------------------------------


class _Client:
    def __init__(self, prices=None, failing=(), rate_limited=False):
        self.prices = prices or {}
        self.failing = set(failing)
        self.rate_limited = rate_limited
        self.calls: list[str] = []

    async def async_get_ticker(self, asset_id):
        self.calls.append(asset_id)
        if self.rate_limited:
            raise BitpandaRateLimitError(f"Rate limited on /tickers/{asset_id}")
        if asset_id in self.failing:
            raise BitpandaApiError(f"HTTP 404 from /tickers/{asset_id}")
        return {"price": self.prices.get(asset_id, "n/a")}


def _coordinator(client, tracked=None) -> TickerCoordinator:
    return TickerCoordinator(None, None, client, _TRACKED if tracked is None else tracked)


async def test_tickers_return_eur_prices():
    client = _Client({BTC: "73188.51648958", SOL: "150.00000000"})
    assert await _coordinator(client)._async_update_data() == {
        BTC: 73188.51648958,
        SOL: 150.0,
    }


async def test_nothing_tracked_makes_no_request():
    client = _Client()
    assert await _coordinator(client, tracked={})._async_update_data() == {}
    assert client.calls == []


async def test_a_failing_asset_is_left_out_and_warned_about_once(caplog):
    client = _Client({SOL: "150.00000000"}, failing={BTC})
    coordinator = _coordinator(client)
    with caplog.at_level(logging.WARNING):
        first = await coordinator._async_update_data()
        await coordinator._async_update_data()
    assert first == {SOL: 150.0}
    assert caplog.text.count("Bitcoin (BTC)") == 1


async def test_an_unreadable_price_counts_as_a_failure():
    client = _Client({SOL: "150.00000000"})  # BTC answers "n/a"
    assert await _coordinator(client)._async_update_data() == {SOL: 150.0}


async def test_a_recovered_asset_is_warned_about_again_when_it_fails_again(caplog):
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"}, failing={BTC})
    coordinator = _coordinator(client)
    with caplog.at_level(logging.WARNING):
        await coordinator._async_update_data()
        client.failing = set()
        await coordinator._async_update_data()
        client.failing = {BTC}
        await coordinator._async_update_data()
    assert caplog.text.count("Bitcoin (BTC)") == 2


async def test_every_asset_failing_fails_the_update():
    coordinator = _coordinator(_Client(failing={BTC, SOL}))
    with pytest.raises(UpdateFailed, match="No prices"):
        await coordinator._async_update_data()


async def test_a_rate_limit_doubles_the_interval_and_is_logged_once(caplog):
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"}, rate_limited=True)
    coordinator = _coordinator(client)
    base = coordinator.update_interval
    with caplog.at_level(logging.WARNING):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.update_interval == base * 2
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.update_interval == base * 4
    assert caplog.text.count("rate-limited") == 1
    # The first 429 stops the round: no further requests after it.
    assert client.calls == [BTC, BTC]

    client.rate_limited = False
    await coordinator._async_update_data()
    assert coordinator.update_interval == base


async def test_a_rate_limit_backoff_is_capped():
    coordinator = _coordinator(_Client(rate_limited=True))
    base = coordinator.update_interval
    for _ in range(10):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    assert coordinator.update_interval == base * 16


def test_a_slow_interval_is_announced_at_construction(caplog):
    tracked = {f"asset-{i}": f"Asset {i}" for i in range(1000)}
    with caplog.at_level(logging.WARNING):
        coordinator = TickerCoordinator(None, None, _Client(), tracked)
    assert coordinator.update_interval == price_interval(1000)
    assert "1000 price trackers" in caplog.text


# --- EcbCoordinator ------------------------------------------------------------------

_RATES = EcbRates(date="2026-09-24", rates={"USD": 1.1367})


async def test_ecb_retries_sooner_while_no_rates_were_ever_loaded():
    coordinator = EcbCoordinator(None, None, object())
    with patch(
        "custom_components.bitpanda.price_coordinator.async_fetch_ecb_rates",
        AsyncMock(side_effect=[EcbError("Timeout fetching the ECB rates"), _RATES]),
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.update_interval == timedelta(minutes=15)
        await coordinator._async_update_data()
    assert coordinator.update_interval == timedelta(hours=6)


async def test_ecb_coordinator_keeps_the_last_rates_when_a_fetch_fails(hass):
    coordinator = EcbCoordinator(hass, None, object())
    with patch(
        "custom_components.bitpanda.price_coordinator.async_fetch_ecb_rates",
        AsyncMock(side_effect=[_RATES, EcbError("Timeout fetching the ECB rates")]),
    ):
        await coordinator.async_refresh()
        assert coordinator.data == _RATES
        await coordinator.async_refresh()
    assert coordinator.last_update_success is False
    assert coordinator.data == _RATES
