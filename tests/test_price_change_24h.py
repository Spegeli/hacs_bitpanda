"""The Price Tracker's 24 h change, read from a real recorder's statistics.

Every 5 minutes one query asks the 5-minute statistics of every price
sensor of the entry for its price of 24 hours before -- the value nearest
to that time within half an hour (day_ago.async_prices_24h_ago) --,
and the next price publishes it with the change since. Without such a
value, or after a failed query, both attributes are absent: never a
reference older than a day. The lookup turns any failure into missing
attributes, so only a real recorder shows that it works.

Statistics rows come from real compiles: a price set while the clock
stands still, then the recorder asked to compile the 5-minute period it
stood in (do_adhoc_statistics), without firing the clock -- which would
compile periods of its own.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.recorder import statistics
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
    do_adhoc_statistics,
)

from homeassistant.helpers import entity_registry as er

from custom_components.bitpanda.const import DOMAIN, PRICE_UPDATE_INTERVAL_BASE
from custom_components.bitpanda.naming import price_unique_id
from custom_components.bitpanda.day_ago import async_prices_24h_ago

from tests.conftest import load_fixture, price_group

_TICKER = "custom_components.bitpanda.api.BitpandaApiClient.async_get_ticker"
_QUERY = "homeassistant.components.recorder.statistics.statistics_during_period"
_BTC_PRICE = "sensor.bitpanda_bitcoin_btc_price_tracker_eur"
_SOL_PRICE = "sensor.bitpanda_solana_sol_price_tracker_eur"

BTC = next(a for a in load_fixture("assets-sample.json") if a["symbol"] == "BTC")
SOL = next(a for a in load_fixture("assets-sample.json") if a["symbol"] == "SOL")

# A day before _NOW, to the second: the time each lookup at _NOW looks for.
_DAY_BEFORE = datetime(2026, 10, 13, 12, 5, 30, tzinfo=timezone.utc)
_NOW = _DAY_BEFORE + timedelta(days=1)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Replaces the shared fixture of the same name for this module: the
    recorder must be set up before Home Assistant itself, and this order of
    arguments is what guarantees it."""
    return


@pytest.fixture
def prices():
    """The prices Bitpanda's ticker answers, by asset id; tests change them."""
    answers: dict[str, str] = {}
    ticker = AsyncMock(side_effect=lambda asset_id: {"price": answers[asset_id]})
    with patch(_TICKER, ticker):
        yield answers


async def _later(hass, freezer, delta: timedelta) -> None:
    """Home Assistant's clock moves on by `delta`, and what is due runs to
    its end. Background tasks included: the lookup waits for the
    recorder's executor, however long that takes on the machine at hand."""
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def _entry(*assets: dict) -> MockConfigEntry:
    """A Price Tracker of `assets` in EUR."""
    return MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker"}, options={"extra_currencies": []},
        subentries_data=[price_group("crypto", *assets)],
    )


async def _set_up(
    hass, freezer, at: datetime, *assets: dict, entry: MockConfigEntry | None = None
) -> MockConfigEntry:
    """A Price Tracker of `assets` -- or `entry`, added already -- set up at
    `at`, and its first lookup done: it waits a second for every sensor to
    join."""
    freezer.move_to(at)
    if entry is None:
        entry = _entry(*assets)
        entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _later(hass, freezer, timedelta(seconds=1))
    await async_wait_recording_done(hass)
    return entry


async def _price_stood(hass, freezer, entry, at: datetime) -> None:
    """The ticker's prices stood at `at`: the clock goes there -- without
    firing it --, the tickers are asked, and the recorder compiles the
    5-minute period `at` lies in. That period's row ends at its end."""
    freezer.move_to(at)
    await entry.runtime_data.tickers.async_refresh()
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)
    do_adhoc_statistics(hass, start=at.replace(minute=at.minute - at.minute % 5, second=0))
    await async_wait_recording_done(hass)


async def _a_day_later(hass, freezer) -> None:
    """The clock at _NOW: what is due runs -- the lookup among it --, and the
    next price publishes the result."""
    freezer.move_to(_NOW)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    await _later(hass, freezer, PRICE_UPDATE_INTERVAL_BASE)


async def test_the_24h_change_compares_with_the_price_the_statistics_hold_from_a_day_before(
    hass, freezer, prices
):
    prices[BTC["id"]] = "100.00000000"
    entry = await _set_up(hass, freezer, _DAY_BEFORE - timedelta(seconds=10), BTC)
    await _price_stood(hass, freezer, entry, _DAY_BEFORE)
    # Nothing was recorded a day before.
    assert "price_24h_ago" not in hass.states.get(_BTC_PRICE).attributes

    prices[BTC["id"]] = "110.00000000"
    await _a_day_later(hass, freezer)

    state = hass.states.get(_BTC_PRICE)
    assert float(state.state) == 110.0
    assert (state.attributes["price_24h_ago"], state.attributes["change_24h_pct"]) == (
        100.0, 10.0,
    )


async def test_a_gap_at_exactly_a_day_ago_takes_the_nearest_value_within_half_an_hour(
    hass, freezer, prices
):
    """Rows only about 20 minutes before (100) and 30 minutes after (120)
    the time a day ago, both within half an hour: the nearer one counts."""
    prices[BTC["id"]] = "100.00000000"
    entry = await _set_up(hass, freezer, _DAY_BEFORE - timedelta(minutes=20, seconds=30), BTC)
    await _price_stood(hass, freezer, entry, _DAY_BEFORE - timedelta(minutes=20))
    prices[BTC["id"]] = "120.00000000"
    await _price_stood(hass, freezer, entry, _DAY_BEFORE + timedelta(minutes=25))

    prices[BTC["id"]] = "130.00000000"
    await _a_day_later(hass, freezer)

    state = hass.states.get(_BTC_PRICE)
    assert (state.attributes["price_24h_ago"], state.attributes["change_24h_pct"]) == (
        100.0, 30.0,
    )


async def test_the_nearest_value_counts_when_it_lies_after_the_time_a_day_ago(
    hass, freezer, prices
):
    """Rows ending about 20 minutes before (100) and 10 minutes after (120)
    the time a day ago, both within half an hour: the nearer one counts,
    though it is the later one."""
    prices[BTC["id"]] = "100.00000000"
    entry = await _set_up(hass, freezer, _DAY_BEFORE - timedelta(minutes=25, seconds=30), BTC)
    await _price_stood(hass, freezer, entry, _DAY_BEFORE - timedelta(minutes=25))
    prices[BTC["id"]] = "120.00000000"
    await _price_stood(hass, freezer, entry, _DAY_BEFORE + timedelta(minutes=5))

    prices[BTC["id"]] = "132.00000000"
    await _a_day_later(hass, freezer)

    state = hass.states.get(_BTC_PRICE)
    assert (state.attributes["price_24h_ago"], state.attributes["change_24h_pct"]) == (
        120.0, 10.0,
    )


async def test_without_a_value_within_half_an_hour_the_24h_attributes_are_absent(
    hass, freezer, prices
):
    prices[BTC["id"]] = "100.00000000"
    entry = await _set_up(hass, freezer, _DAY_BEFORE - timedelta(hours=1, minutes=10), BTC)
    await _price_stood(hass, freezer, entry, _DAY_BEFORE - timedelta(hours=1, minutes=5))
    prices[BTC["id"]] = "120.00000000"
    await _price_stood(hass, freezer, entry, _DAY_BEFORE + timedelta(hours=1))

    prices[BTC["id"]] = "130.00000000"
    await _a_day_later(hass, freezer)

    state = hass.states.get(_BTC_PRICE)
    assert float(state.state) == 130.0
    assert "price_24h_ago" not in state.attributes
    assert "change_24h_pct" not in state.attributes


async def test_a_failed_lookup_leaves_no_stale_reference(hass, freezer, prices):
    prices[BTC["id"]] = "100.00000000"
    entry = await _set_up(hass, freezer, _DAY_BEFORE - timedelta(seconds=10), BTC)
    await _price_stood(hass, freezer, entry, _DAY_BEFORE)
    prices[BTC["id"]] = "110.00000000"
    await _a_day_later(hass, freezer)
    assert hass.states.get(_BTC_PRICE).attributes["price_24h_ago"] == 100.0

    with patch(_QUERY, side_effect=RuntimeError("database gone")):
        await _later(hass, freezer, timedelta(minutes=5))
    await _later(hass, freezer, PRICE_UPDATE_INTERVAL_BASE)

    state = hass.states.get(_BTC_PRICE)
    assert "price_24h_ago" not in state.attributes
    assert "change_24h_pct" not in state.attributes


async def test_one_query_serves_every_price_sensor_of_the_entry(hass, freezer, prices):
    """Two assets, one query per lookup, asking for both; the next lookup
    five minutes later."""
    prices.update({BTC["id"]: "100.00000000", SOL["id"]: "20.00000000"})
    with patch(_QUERY, wraps=statistics.statistics_during_period) as query:
        await _set_up(hass, freezer, _DAY_BEFORE, BTC, SOL)
        assert query.call_count == 1
        assert query.call_args.args[3] == {_BTC_PRICE, _SOL_PRICE}
        assert query.call_args.args[4:] == ("5minute", None, {"state"})

        await _later(hass, freezer, timedelta(minutes=5))

    assert query.call_count == 2
    assert query.call_args.args[3] == {_BTC_PRICE, _SOL_PRICE}


async def test_a_disabled_price_sensor_is_not_asked_for(hass, freezer, prices):
    prices.update({BTC["id"]: "100.00000000", SOL["id"]: "20.00000000"})
    entry = _entry(BTC, SOL)
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, price_unique_id(entry.entry_id, SOL["id"], "EUR"),
        config_entry=entry, suggested_object_id="bitpanda_solana_sol_price_tracker_eur",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    with patch(_QUERY, wraps=statistics.statistics_during_period) as query:
        await _set_up(hass, freezer, _DAY_BEFORE, entry=entry)
    assert query.call_args.args[3] == {_BTC_PRICE}


async def test_a_price_sensor_disabled_while_the_entry_runs_is_no_longer_asked_for(
    hass, freezer, prices
):
    """Disabled, the sensor leaves Home Assistant at once -- the entry's
    reload follows half a minute later --: no lookup asks for it after
    that."""
    prices.update({BTC["id"]: "100.00000000", SOL["id"]: "20.00000000"})
    await _set_up(hass, freezer, _DAY_BEFORE, BTC, SOL)
    with patch(_QUERY, wraps=statistics.statistics_during_period) as query:
        er.async_get(hass).async_update_entity(
            _SOL_PRICE, disabled_by=er.RegistryEntryDisabler.USER
        )
        await hass.async_block_till_done()
        await _later(hass, freezer, timedelta(minutes=5))
    assert hass.states.get(_SOL_PRICE) is None
    assert query.call_count >= 1
    assert [call.args[3] for call in query.call_args_list] == [{_BTC_PRICE}] * query.call_count


async def test_a_period_without_a_state_is_no_reference(hass, freezer):
    """A 5-minute row without a state -- the sensor unavailable for the
    whole period -- is no value: the nearest row with one counts."""
    target = _NOW - timedelta(hours=24)
    rows = {
        _BTC_PRICE: [
            {"start": target.timestamp() - 300, "end": target.timestamp(), "state": None},
            {"start": target.timestamp() + 300, "end": target.timestamp() + 600, "state": 99.0},
        ],
        _SOL_PRICE: [{"start": target.timestamp() - 300, "end": target.timestamp(), "state": None}],
    }
    with patch(_QUERY, return_value=rows):
        found = await async_prices_24h_ago(hass, {_BTC_PRICE, _SOL_PRICE}, _NOW)
    assert found == {_BTC_PRICE: 99.0}


async def test_a_statistic_without_any_row_is_left_out(hass):
    """Asked for, but not in the answer -- a sensor whose statistics do
    not reach back a day: no value, and no error."""
    rows = {_BTC_PRICE: [{"start": _DAY_BEFORE.timestamp() - 300, "end": _DAY_BEFORE.timestamp(), "state": 98.0}]}
    with patch(_QUERY, return_value=rows):
        found = await async_prices_24h_ago(hass, {_BTC_PRICE, _SOL_PRICE}, _NOW)
    assert found == {_BTC_PRICE: 98.0}
