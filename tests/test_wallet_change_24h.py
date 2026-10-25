"""A wallet's price of 24 hours ago, read from a real recorder.

A price is the Balance (total) sensor's value over its units at one
moment. The value comes from the 5-minute statistics -- a row every 5
minutes, changed or not, none while Home Assistant was off -- and the units
from the recorded state in effect when that row's value stood, its end
(day_ago.async_wallet_prices_24h_ago): the nearest row to 24 hours ago
within half an hour whose moment has units.

States are written as the sensor writes them, with the recorder's
statistics attributes; statistics rows come from real compiles
(do_adhoc_statistics) of the 5-minute period a state stood in.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.recorder import history, statistics
from homeassistant.core import State
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
    do_adhoc_statistics,
)

from custom_components.bitpanda.api import BitpandaApiError
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.day_ago import async_wallet_prices_24h_ago
from custom_components.bitpanda.naming import total_unique_id

from tests.conftest import load_fixture

_QUERY = "homeassistant.components.recorder.statistics.statistics_during_period"
_HISTORY = "homeassistant.components.recorder.history.get_significant_states"
_VSN = "sensor.bitpanda_vision_vsn_wallet_total"
_BTC = "sensor.bitpanda_bitcoin_btc_wallet_total"
_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
VSN = next(a for a in load_fixture("assets-sample.json") if a["symbol"] == "VSN")
BTC = next(a for a in load_fixture("assets-sample.json") if a["symbol"] == "BTC")

# A day before _NOW, to the second: the time each lookup at _NOW looks for.
_DAY_BEFORE = datetime(2026, 10, 13, 12, 5, 30, tzinfo=timezone.utc)
_NOW = _DAY_BEFORE + timedelta(days=1)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Replaces the shared fixture of the same name for this module: the
    recorder must be set up before Home Assistant itself, and this order of
    arguments is what guarantees it."""
    return


@pytest.fixture(autouse=True)
async def sensor_component(hass):
    """The recorder compiles the statistics of sensor states only once the
    sensor component is loaded; the integration's setup loads it, these
    tests write the states themselves."""
    assert await async_setup_component(hass, "sensor", {})


def _period(at: datetime) -> datetime:
    """The start of the 5-minute period `at` lies in."""
    return at.replace(minute=at.minute - at.minute % 5, second=0, microsecond=0)


async def _stood(
    hass, freezer, at: datetime, value: float, units: float, entity_id: str = _VSN,
    currency: str = "EUR", priced: bool = True,
) -> None:
    """The wallet was worth `value` for `units` from `at` on, its ticker
    price value over units unless not `priced` (a state of the version
    before the ticker prices): the state is written at `at` -- the clock
    moved there without firing it -- as the Balance (total) sensor writes
    it, in `currency`."""
    freezer.move_to(at)
    attributes = {"units": units, "unit_of_measurement": currency, "device_class": "monetary", "state_class": "total"}
    if priced:
        attributes["price"] = value / units
    hass.states.async_set(entity_id, str(value), attributes)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)


async def _compiled(hass, at: datetime) -> None:
    """The recorder compiles the 5-minute period `at` lies in; its row ends
    at the period's end."""
    do_adhoc_statistics(hass, start=_period(at))
    await async_wait_recording_done(hass)


async def test_the_price_of_a_day_ago_is_the_price_recorded_then(hass, freezer):
    await _stood(hass, freezer, _DAY_BEFORE, 100.0, 1000.0)
    await _compiled(hass, _DAY_BEFORE)
    assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == {_VSN: pytest.approx(0.1)}


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        # Rows ending 15.5 min before and 14.5 min after: the later one.
        (timedelta(minutes=20), timedelta(minutes=10), 0.12),
        # Rows ending 5.5 min before and 24.5 min after: the earlier one.
        (timedelta(minutes=10), timedelta(minutes=20), 0.1),
    ],
    ids=["nearer after", "nearer before"],
)
async def test_the_nearest_row_counts_on_either_side(hass, freezer, before, after, expected):
    await _stood(hass, freezer, _DAY_BEFORE - before, 100.0, 1000.0)
    await _compiled(hass, _DAY_BEFORE - before)
    await _stood(hass, freezer, _DAY_BEFORE + after, 120.0, 1000.0)
    await _compiled(hass, _DAY_BEFORE + after)
    assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == {_VSN: pytest.approx(expected)}


async def test_without_a_row_within_half_an_hour_there_is_no_price(hass, freezer):
    await _stood(hass, freezer, _DAY_BEFORE - timedelta(hours=1, minutes=5), 100.0, 1000.0)
    await _compiled(hass, _DAY_BEFORE - timedelta(hours=1, minutes=5))
    await _stood(hass, freezer, _DAY_BEFORE + timedelta(hours=1), 120.0, 1000.0)
    await _compiled(hass, _DAY_BEFORE + timedelta(hours=1))
    assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == {}


async def test_the_price_recorded_at_the_rows_end_counts(hass, freezer):
    """The price changed 5 minutes after the time a day ago; the only row
    ends 9.5 minutes after it: the state in effect at the row's end counts
    -- 0.2 --, not the one at the time a day ago."""
    await _stood(hass, freezer, _DAY_BEFORE - timedelta(hours=3), 100.0, 1000.0)
    await _stood(hass, freezer, _DAY_BEFORE + timedelta(minutes=5), 400.0, 2000.0)
    await _compiled(hass, _DAY_BEFORE + timedelta(minutes=5))
    assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == {_VSN: pytest.approx(0.2)}


async def test_a_state_recorded_before_the_ticker_prices_is_no_reference(hass, freezer):
    """Recorded without a price -- by the version before -- : the value over
    the units of then is no reference; the 24-hour figures wait a day."""
    await _stood(hass, freezer, _DAY_BEFORE, 100.0, 1000.0, priced=False)
    await _compiled(hass, _DAY_BEFORE)
    assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == {}


async def test_a_value_unchanged_for_a_day_gives_no_change(hass, freezer):
    """A stablecoin, or a stock over the weekend: no new state for hours,
    yet the statistics hold a row every 5 minutes, and the units are those
    of the state recorded long before."""
    await _stood(hass, freezer, _DAY_BEFORE - timedelta(hours=1), 100.0, 1000.0)
    freezer.move_to(_DAY_BEFORE + timedelta(minutes=10))
    await _compiled(hass, _DAY_BEFORE)
    assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == {_VSN: pytest.approx(0.1)}


async def test_a_value_of_a_day_ago_in_another_currency_is_no_price(hass, freezer):
    """The Portfolio's currency changed since -- its statistics kept, or not
    purged yet: a price in USD is no reference for one in EUR."""
    await _stood(hass, freezer, _DAY_BEFORE, 110.0, 1000.0, currency="USD")
    await _compiled(hass, _DAY_BEFORE)
    await _stood(hass, freezer, _NOW, 100.0, 1000.0, currency="EUR")
    assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == {}


def _row(end: datetime, state: float | None) -> dict:
    return {"start": end.timestamp() - 300, "end": end.timestamp(), "state": state}


def _recorded(at: datetime, state: str, attributes: dict) -> State:
    return State(_VSN, state, attributes, last_changed=at, last_updated=at)


@pytest.mark.parametrize(
    ("recorded", "expected"),
    [
        # The state in effect at the nearest row's end recorded no price.
        ([_recorded(_DAY_BEFORE - timedelta(hours=1), "100.0", {"units": 1000.0})], {}),
        # Unavailable then.
        ([_recorded(_DAY_BEFORE - timedelta(hours=1), "unavailable", {"price": 0.12})], {}),
        # A price of 0 is none.
        ([_recorded(_DAY_BEFORE - timedelta(hours=1), "0.0", {"price": 0})], {}),
        # Unavailable at the nearest row's end, a state with a price before
        # the second row's: that row gives the price.
        (
            [
                _recorded(_DAY_BEFORE - timedelta(hours=1), "120.0", {"price": 0.12}),
                _recorded(_DAY_BEFORE + timedelta(minutes=1), "unavailable", {}),
            ],
            {_VSN: pytest.approx(0.12)},
        ),
        # No state recorded by either row's end.
        ([_recorded(_DAY_BEFORE + timedelta(hours=1), "120.0", {"price": 0.12})], {}),
    ],
    ids=["no price", "unavailable", "zero", "next row", "nothing recorded"],
)
async def test_a_state_without_a_price_or_unavailable_is_no_reference(hass, recorded, expected):
    rows = {
        _VSN: [
            _row(_DAY_BEFORE - timedelta(minutes=10), 120.0),
            _row(_DAY_BEFORE + timedelta(minutes=5), 100.0),
        ]
    }
    with patch(_QUERY, return_value=rows), patch(_HISTORY, return_value={_VSN: recorded}):
        assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == expected


async def test_a_state_written_at_the_rows_end_belongs_to_the_next_period(hass):
    """A 5-minute row holds the states written before its end: one written
    exactly at the end is the next period's, and its units are not those
    of the row's value."""
    end = _DAY_BEFORE + timedelta(minutes=5)
    rows = {_VSN: [_row(end, 100.0)]}
    recorded = [
        _recorded(end - timedelta(hours=1), "100.0", {"price": 0.1}),
        _recorded(end, "400.0", {"price": 0.2}),
    ]
    with patch(_QUERY, return_value=rows), patch(_HISTORY, return_value={_VSN: recorded}):
        assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == {_VSN: pytest.approx(0.1)}


@pytest.mark.parametrize(
    ("attributes", "expected"),
    [
        # The ticker's price recorded then, not the row's value over units.
        ({"units": 1000.0, "price": 0.11}, {_VSN: pytest.approx(0.11)}),
        # A state recorded before the ticker prices: no reference.
        ({"units": 1000.0}, {}),
        # A recorded price that is no price: no reference.
        ({"units": 1000.0, "price": 0}, {}),
    ],
    ids=["recorded price", "no recorded price", "zero"],
)
async def test_only_a_recorded_price_is_a_reference(hass, attributes, expected):
    rows = {_VSN: [_row(_DAY_BEFORE + timedelta(minutes=5), 100.0)]}
    recorded = [_recorded(_DAY_BEFORE - timedelta(hours=1), "100.0", attributes)]
    with patch(_QUERY, return_value=rows), patch(_HISTORY, return_value={_VSN: recorded}):
        assert await async_wallet_prices_24h_ago(hass, {_VSN}, _NOW) == expected


async def test_one_query_each_serves_every_wallet(hass, freezer):
    await _stood(hass, freezer, _DAY_BEFORE, 100.0, 1000.0)
    await _stood(hass, freezer, _DAY_BEFORE, 500.0, 0.01, _BTC)
    await _compiled(hass, _DAY_BEFORE)
    with patch(_QUERY, wraps=statistics.statistics_during_period) as query, patch(
        _HISTORY, wraps=history.get_significant_states
    ) as recorded:
        found = await async_wallet_prices_24h_ago(hass, {_VSN, _BTC}, _NOW)
    assert found == {_VSN: pytest.approx(0.1), _BTC: pytest.approx(50000.0)}
    assert query.call_count == 1 and recorded.call_count == 1
    assert set(query.call_args.args[3]) == {_VSN, _BTC}
    assert set(recorded.call_args.kwargs["entity_ids"]) == {_VSN, _BTC}


# --- The Balance (total) sensor of a set-up Portfolio ------------------------


@pytest.fixture
def ticker():
    """Bitpanda's ticker for every asset: the price a test sets, or no
    answer while it is None."""
    answer = {"price": None}

    async def _ask(asset_id):
        if answer["price"] is None:
            raise BitpandaApiError("no price", kind="http_status", path="/tickers")
        return {"asset_id": asset_id, "price": answer["price"]}

    with patch(f"{_CLIENT}async_get_ticker", AsyncMock(side_effect=_ask)):
        yield answer


@pytest.fixture
def portfolio():
    """What Bitpanda's /portfolio answers, by asset id: (units, value);
    tests change it. Cash beside it."""
    held: dict[str, tuple[str, str]] = {}

    def answer(*_args, **_kwargs):
        return [
            *(
                {
                    "asset_id": asset_id,
                    "balance": {"value": units},
                    "available_balance": {"value": units},
                    "currency_balance": {"value": value},
                }
                for asset_id, (units, value) in held.items()
            ),
            {"currency_id": _EUR_ID, "balance": {"value": "10.00"}},
        ]

    def lookup(**kwargs):
        return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]

    with patch(f"{_CLIENT}async_get_portfolio", AsyncMock(side_effect=answer)), patch(
        f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 1.5})
    ), patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])
    ), patch(f"{_CLIENT}async_get_assets", AsyncMock(side_effect=lookup)):
        yield held


def _portfolio_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR", "currency_id": _EUR_ID},
    )
    entry.add_to_hass(hass)
    return entry


async def _later(hass, freezer, delta: timedelta) -> None:
    """Home Assistant's clock moves on by `delta`, and what is due runs to
    its end, background tasks -- the lookup, the refresh -- included."""
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def _set_up(hass, freezer, at: datetime, entry: MockConfigEntry | None = None) -> MockConfigEntry:
    """The Portfolio set up at `at`, its first lookup done a second later."""
    freezer.move_to(at)
    entry = entry or _portfolio_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await _later(hass, freezer, timedelta(seconds=1))
    await async_wait_recording_done(hass)
    return entry


async def _a_day_later(hass, freezer) -> None:
    """The clock at _NOW: the lookup and the refresh due run, and the next
    refresh publishes the result."""
    freezer.move_to(_NOW)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    await _later(hass, freezer, timedelta(minutes=6))


async def test_a_wallet_shows_its_24h_figures_a_day_later(hass, freezer, portfolio, ticker):
    ticker["price"] = "0.10000000"
    portfolio[VSN["id"]] = ("1000.00000000", "100.00")
    entry = await _set_up(hass, freezer, _DAY_BEFORE - timedelta(seconds=10))
    await _compiled(hass, _DAY_BEFORE)
    assert hass.states.get(_VSN).attributes["price"] == pytest.approx(0.1)
    assert "price_24h_ago" not in hass.states.get(_VSN).attributes

    ticker["price"] = "0.11000000"
    portfolio[VSN["id"]] = ("1000.00000000", "110.00")
    await _a_day_later(hass, freezer)

    attributes = hass.states.get(_VSN).attributes
    assert attributes["price"] == pytest.approx(0.11)
    assert attributes["price_24h_ago"] == pytest.approx(0.1)
    assert attributes["change_24h_pct"] == 10.0
    assert attributes["return_24h"] == pytest.approx(10.0)
    # Kept for the actions, by the wallet's asset.
    assert entry.runtime_data.day_ago.last == {VSN["id"]: pytest.approx(0.1)}


async def test_the_24h_figures_compare_the_ticker_prices_of_now_and_a_day_ago(
    hass, freezer, portfolio
):
    """The ticker's price recorded a day ago is the reference, not the value
    over the units of then, which /portfolio gives in cents (0.10 here)."""
    ticker = {"price": "0.12000000"}
    with patch(f"{_CLIENT}async_get_ticker", AsyncMock(side_effect=lambda asset_id: dict(ticker))):
        portfolio[VSN["id"]] = ("1000.00000000", "100.00")
        await _set_up(hass, freezer, _DAY_BEFORE - timedelta(seconds=10))
        await _compiled(hass, _DAY_BEFORE)
        assert hass.states.get(_VSN).attributes["price"] == 0.12

        ticker["price"] = "0.13000000"
        portfolio[VSN["id"]] = ("1000.00000000", "110.00")
        await _a_day_later(hass, freezer)

    attributes = hass.states.get(_VSN).attributes
    assert attributes["price"] == 0.13
    assert attributes["price_24h_ago"] == 0.12
    assert attributes["change_24h_pct"] == round((0.13 - 0.12) / 0.12 * 100, 2)
    assert attributes["return_24h"] == pytest.approx(10.0)


async def test_a_disabled_balance_total_is_not_asked_for(hass, freezer, portfolio):
    portfolio.update({VSN["id"]: ("1000.00000000", "100.00"), BTC["id"]: ("0.01000000", "500.00")})
    entry = _portfolio_entry(hass)
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, total_unique_id(entry.entry_id, VSN["id"]),
        config_entry=entry, suggested_object_id="bitpanda_vision_vsn_wallet_total",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    with patch(_QUERY, wraps=statistics.statistics_during_period) as query:
        await _set_up(hass, freezer, _DAY_BEFORE, entry)
    assert query.call_count == 1
    assert set(query.call_args.args[3]) == {_BTC}
    # Nothing kept for the actions: they read null.
    assert set(entry.runtime_data.day_ago.last) == {BTC["id"]}


async def test_a_failed_lookup_leaves_no_stale_figures(hass, freezer, portfolio, ticker):
    ticker["price"] = "0.10000000"
    portfolio[VSN["id"]] = ("1000.00000000", "100.00")
    await _set_up(hass, freezer, _DAY_BEFORE - timedelta(seconds=10))
    await _compiled(hass, _DAY_BEFORE)
    ticker["price"] = "0.11000000"
    portfolio[VSN["id"]] = ("1000.00000000", "110.00")
    await _a_day_later(hass, freezer)
    assert hass.states.get(_VSN).attributes["price_24h_ago"] == pytest.approx(0.1)

    # Every lookup fails from here on, and a refresh follows the first.
    with patch(_QUERY, side_effect=RuntimeError("database gone")):
        await _later(hass, freezer, timedelta(minutes=5))
        await _later(hass, freezer, timedelta(minutes=6))

    attributes = hass.states.get(_VSN).attributes
    assert attributes["price"] == pytest.approx(0.11)
    for key in ("price_24h_ago", "change_24h_pct", "return_24h"):
        assert key not in attributes, key
