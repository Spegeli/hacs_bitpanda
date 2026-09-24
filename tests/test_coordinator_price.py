"""Tests for the adaptive price interval and ticker conversion."""
import logging
from datetime import timedelta

from custom_components.bitpanda.api import BitpandaApiError
from custom_components.bitpanda.coordinator import (
    Holding,
    PortfolioData,
    PriceCoordinator,
    convert_price,
    price_interval,
)


def test_interval_stays_at_base_for_small_sets():
    assert price_interval(0) == timedelta(seconds=60)
    assert price_interval(10) == timedelta(seconds=60)
    assert price_interval(30) == timedelta(seconds=60)


def test_interval_lengthens_past_the_budget():
    """1800 price requests/hour is the share reserved for tickers."""
    assert price_interval(60) > timedelta(seconds=60)


def test_interval_keeps_every_size_inside_the_budget():
    for count in (1, 10, 30, 50, 100, 500):
        interval = price_interval(count)
        per_hour = count * (3600 / interval.total_seconds())
        assert per_hour <= 1800 + 1


def test_interval_keeps_the_budget_even_for_absurd_counts():
    """The budget guarantee is unconditional — there is no cap to break it."""
    for count in (900, 901, 5000, 14054):
        interval = price_interval(count)
        per_hour = count * (3600 / interval.total_seconds())
        assert per_hour <= 1800 + 1


def test_interval_grows_past_the_old_thirty_minute_clamp():
    """An earlier version clamped here and silently blew the budget."""
    assert price_interval(5000) > timedelta(minutes=30)


def test_convert_price_returns_eur_unchanged_when_no_rate():
    assert convert_price("73188.51648958", None) == 73188.51648958


def test_convert_price_applies_rate():
    assert abs(convert_price("100.00000000", 1.13755257) - 113.755257) < 1e-9


def test_convert_price_returns_none_on_garbage():
    assert convert_price("not-a-number", None) is None


# ---------------------------------------------------------------------------
# PriceCoordinator._async_update_data
#
# DataUpdateCoordinator.__init__ only stores `hass` and reads it back through
# a Debouncer that is never triggered by a direct _async_update_data() call,
# so a real PriceCoordinator can be constructed with hass=None/entry=None and
# driven without a running Home Assistant instance. That keeps these as fast
# regression guards instead of skipping coordinator coverage entirely.
# ---------------------------------------------------------------------------


class _FakePortfolioCoordinator:
    """Duck-typed stand-in exposing the one attribute PriceCoordinator reads."""

    def __init__(self, data):
        self.data = data


class _FakeClient:
    """Fake API client with a controllable async_get_ticker."""

    def __init__(self, tickers=None, fail=False):
        self._tickers = tickers or {}
        self._fail = fail
        self.calls: list[str] = []

    async def async_get_ticker(self, asset_id):
        self.calls.append(asset_id)
        if self._fail:
            raise BitpandaApiError("simulated outage")
        return self._tickers[asset_id]


def _holding(balance, value):
    return Holding(asset_id="unused", balance=balance, available=balance,
                   staked=0.0, value=value)


async def test_zero_balance_holding_falls_through_to_a_ticker_call():
    """A holding sold down to exactly zero must still get a price.

    `a1 not in held` would be False here since the key is present, so the
    old "presence only" check skipped both pricing paths silently. It must
    end up in `needed` and be priced from the ticker instead.
    """
    held = {"a1": _holding(balance=0.0, value=0.0)}
    portfolio = _FakePortfolioCoordinator(PortfolioData(holdings=held, rate=None))
    client = _FakeClient(tickers={"a1": {"price": "123.45"}})
    coordinator = PriceCoordinator(
        hass=None, entry=None, client=client, portfolio=portfolio
    )
    coordinator.set_tracked(["a1"])

    prices = await coordinator._async_update_data()

    assert prices == {"a1": 123.45}
    assert client.calls == ["a1"]


async def test_total_ticker_outage_still_returns_held_prices(caplog):
    """Every ticker failing must not take down prices for assets held.

    Partial data (the held asset's portfolio-derived price) is returned
    rather than raising UpdateFailed, and the outage is logged at WARNING
    so it is visible without anyone having enabled DEBUG logging.
    """
    caplog.set_level(logging.WARNING, logger="custom_components.bitpanda.coordinator")
    held = {"a1": _holding(balance=2.0, value=20.0)}
    portfolio = _FakePortfolioCoordinator(PortfolioData(holdings=held, rate=None))
    client = _FakeClient(fail=True)
    coordinator = PriceCoordinator(
        hass=None, entry=None, client=client, portfolio=portfolio
    )
    coordinator.set_tracked(["a1", "a2"])

    prices = await coordinator._async_update_data()

    assert prices == {"a1": 10.0}
    assert "ticker requests failed" in caplog.text
