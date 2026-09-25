"""Tests for the bitpanda.refresh service's cooldown.

Every accepted call costs one or two portfolio requests plus one ticker
request per tracked asset the portfolio cannot price. A fixed 10 second
cooldown let an automation run that six times a minute -- far above the
adaptive polling rate the price interval keeps inside the hourly budget. The
cooldown now follows the price coordinator's current interval, and never
drops below 10 seconds.

The clock is the module's own `monotonic` name, patched there alone: patching
`time.monotonic` itself would also move the event loop's clock.
"""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from custom_components.bitpanda import _async_register_refresh_service
from custom_components.bitpanda.const import DOMAIN


class _Coordinator:
    def __init__(self, interval: timedelta) -> None:
        self.update_interval = interval
        self.async_request_refresh = AsyncMock()


class _Clock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def _register(hass, price_interval: timedelta):
    prices = _Coordinator(price_interval)
    portfolio = _Coordinator(timedelta(minutes=5))
    hass.data.setdefault(DOMAIN, {})["entry1"] = {
        "portfolio_coordinator": portfolio,
        "price_coordinator": prices,
    }
    _async_register_refresh_service(hass)
    return portfolio, prices


async def _call(hass) -> None:
    await hass.services.async_call(DOMAIN, "refresh", blocking=True)


async def test_refresh_is_throttled_to_the_price_interval(hass):
    portfolio, prices = _register(hass, timedelta(seconds=60))
    clock = _Clock(1000.0)

    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 15  # past the old fixed 10 s, inside the 60 s interval
        await _call(hass)
        clock.now += 46  # 61 s after the first accepted call
        await _call(hass)

    assert prices.async_request_refresh.await_count == 2
    assert portfolio.async_request_refresh.await_count == 2


async def test_refresh_cooldown_follows_a_stretched_price_interval(hass):
    """Above 30 unheld trackers the price interval stretches; the service
    must not undo that by refreshing at the base rate.
    """
    _, prices = _register(hass, timedelta(seconds=120))
    clock = _Clock(1000.0)

    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 61
        await _call(hass)
        clock.now += 60  # 121 s after the first accepted call
        await _call(hass)

    assert prices.async_request_refresh.await_count == 2


async def test_refresh_cooldown_never_drops_below_ten_seconds(hass):
    _, prices = _register(hass, timedelta(seconds=5))
    clock = _Clock(1000.0)

    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 6
        await _call(hass)
        clock.now += 5  # 11 s after the first accepted call
        await _call(hass)

    assert prices.async_request_refresh.await_count == 2


async def test_first_refresh_is_accepted_right_after_boot(hass):
    """The monotonic clock can start near zero. The first call must not be
    measured against a pretend earlier call at time 0.
    """
    _, prices = _register(hass, timedelta(seconds=60))

    with patch("custom_components.bitpanda.monotonic", _Clock(5.0)):
        await _call(hass)

    assert prices.async_request_refresh.await_count == 1
