"""Tests for the adaptive price interval and ticker conversion."""
import logging
from datetime import timedelta

from custom_components.bitpanda.api import BitpandaApiError
from custom_components.bitpanda.const import EUR_CURRENCY_ID
from custom_components.bitpanda.coordinator import (
    Holding,
    PortfolioData,
    PriceCoordinator,
    convert_price,
    price_interval,
)

_USD_ID = "b88b8879-efe3-11eb-b56f-0691764446a7"


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


def test_convert_price_rounds_to_the_eight_decimals_the_api_quotes():
    """No float noise such as 0.30000000000000004 in a published price."""
    assert convert_price("0.10000000", 3.0) == 0.3
    assert convert_price("0.00000032", 1.13755257) == 0.00000036


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
    """Duck-typed stand-in exposing what PriceCoordinator reads."""

    def __init__(self, data, last_update_success=True):
        self.data = data
        self.last_update_success = last_update_success


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


def _coordinator(held, *, client, rate=None, currency_id=EUR_CURRENCY_ID,
                 portfolio_ok=True):
    portfolio = _FakePortfolioCoordinator(
        PortfolioData(holdings=held, rate=rate), last_update_success=portfolio_ok
    )
    return PriceCoordinator(
        hass=None, entry=None, client=client, portfolio=portfolio,
        currency_id=currency_id,
    )


async def test_zero_balance_holding_falls_through_to_a_ticker_call():
    """A holding sold down to exactly zero must still get a price.

    `a1 not in held` would be False here since the key is present, so the
    old "presence only" check skipped both pricing paths silently. It must
    end up in `needed` and be priced from the ticker instead.
    """
    client = _FakeClient(tickers={"a1": {"price": "123.45"}})
    coordinator = _coordinator({"a1": _holding(balance=0.0, value=0.0)}, client=client)
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
    client = _FakeClient(fail=True)
    coordinator = _coordinator({"a1": _holding(balance=2.0, value=200.0)}, client=client)
    coordinator.set_tracked(["a1", "a2"])

    prices = await coordinator._async_update_data()

    assert prices == {"a1": 100.0}
    assert "ticker requests failed" in caplog.text


# --- Which held assets may be priced from the portfolio ------------------------
#
# The portfolio values a holding in cents. Dividing that by the balance gives
# a unit price whose rounding error is up to half a cent over the value: about
# 0.01 % at 50, whole percent below 1, and a price of exactly 0 for dust
# valued at 0.00. Only a fresh value of at least 50 is used; anything else is
# priced from the ticker.


async def test_dust_holding_valued_at_zero_is_priced_from_the_ticker():
    client = _FakeClient(tickers={"btc": {"price": "73188.51648958"}})
    coordinator = _coordinator({"btc": _holding(balance=0.00000004, value=0.0)},
                               client=client)
    coordinator.set_tracked(["btc"])

    assert await coordinator._async_update_data() == {"btc": 73188.51648958}
    assert client.calls == ["btc"]


async def test_small_holding_is_priced_from_the_ticker():
    """The test account's SPC: 9.41652 units valued at 0.04 would price at
    0.004248, anywhere in [0.003717, 0.004779) in truth.
    """
    client = _FakeClient(tickers={"spc": {"price": "0.00423500"}})
    coordinator = _coordinator({"spc": _holding(balance=9.41652, value=0.04)},
                               client=client)
    coordinator.set_tracked(["spc"])

    assert await coordinator._async_update_data() == {"spc": 0.004235}
    assert client.calls == ["spc"]


async def test_holding_worth_at_least_fifty_is_priced_from_the_portfolio():
    client = _FakeClient()
    coordinator = _coordinator(
        {"btc": _holding(balance=0.0114, value=850.0),
         "xau": _holding(balance=0.5, value=50.0)},
        client=client,
    )
    coordinator.set_tracked(["btc", "xau"])

    prices = await coordinator._async_update_data()

    assert prices == {"btc": round(850.0 / 0.0114, 8), "xau": 100.0}
    assert client.calls == []


async def test_holding_without_a_value_is_priced_from_the_ticker():
    client = _FakeClient(tickers={"eth": {"price": "2500.00000000"}})
    coordinator = _coordinator({"eth": _holding(balance=1.0, value=None)}, client=client)
    coordinator.set_tracked(["eth"])

    assert await coordinator._async_update_data() == {"eth": 2500.0}
    assert client.calls == ["eth"]


async def test_held_asset_is_priced_from_the_ticker_while_the_portfolio_fails():
    """After a failed portfolio refresh `data` still holds the last good
    response. Prices derived from it would look fresh while the wallet
    sensors already show unavailable -- and after a portfolio auth failure
    Home Assistant stops polling it, so they would freeze until reauth.
    """
    client = _FakeClient(tickers={"btc": {"price": "73188.51648958"}})
    coordinator = _coordinator({"btc": _holding(balance=0.0114, value=850.0)},
                               client=client, portfolio_ok=False)
    coordinator.set_tracked(["btc"])

    assert await coordinator._async_update_data() == {"btc": 73188.51648958}
    assert client.calls == ["btc"]


# --- Non-EUR display currency: never an EUR number under another unit -------


async def test_ticker_price_is_converted_and_rounded_for_a_non_eur_currency():
    client = _FakeClient(tickers={"btc": {"price": "73188.51648958"}})
    coordinator = _coordinator({}, client=client, rate=1.13755257, currency_id=_USD_ID)
    coordinator.set_tracked(["btc"])

    assert await coordinator._async_update_data() == {
        "btc": round(73188.51648958 * 1.13755257, 8)
    }


async def test_no_price_without_a_rate_for_a_non_eur_currency():
    """/tickers answers in EUR only. Without a rate that number would be
    published under the display currency's unit -- wrong by the exchange
    rate, silently. No price (the sensor reads unknown and its `conversion`
    attribute explains why) and no pointless ticker request instead.
    """
    client = _FakeClient(tickers={"btc": {"price": "73188.51648958"}})
    coordinator = _coordinator({}, client=client, rate=None, currency_id=_USD_ID)
    coordinator.set_tracked(["btc"])

    assert await coordinator._async_update_data() == {}
    assert client.calls == []


async def test_eur_prices_need_no_rate():
    client = _FakeClient(tickers={"btc": {"price": "73188.51648958"}})
    coordinator = _coordinator({}, client=client, rate=None)
    coordinator.set_tracked(["btc"])

    assert await coordinator._async_update_data() == {"btc": 73188.51648958}
