"""Earn changes of held assets are announced (announcements.EarnAnnouncer):
the event bitpanda_earn_changed and the Earn change event entity, never a
notification -- a product offered or withdrawn, sold out or available again,
its APR moved by a quarter point or more. The first catalogue after setup,
a wallet new since, an asset bought back: no news. End to end, Bitpanda
mocked as in tests/test_init.py."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.bitpanda.api import BitpandaApiError
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import find_entry_device

from tests.conftest import ANNOUNCEMENT_FIELDS, load_fixture

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_EVENT = "bitpanda_earn_changed"
_ENTITY = "event.bitpanda_portfolio_earn_change"


def _record(symbol: str) -> dict:
    return next(a for a in load_fixture("assets-sample.json") if a["symbol"] == symbol)


VSN, BTC, SOL, ADA = _record("VSN"), _record("BTC"), _record("SOL"), _record("ADA")
_CASH = {"currency_id": _EUR_ID, "balance": {"value": "10.00"}}


def _position(asset: dict) -> dict:
    return {
        "asset_id": asset["id"],
        "balance": {"value": "10.00000000"},
        "available_balance": {"value": "10.00000000"},
        "currency_balance": {"value": "100.00"},
    }


def _answer(*assets: dict) -> list[dict]:
    return [*(_position(asset) for asset in assets), _CASH]


def _product(asset: dict, apr: float = 0.05, *, enabled=True, sold_out=False) -> dict:
    return {
        "asset_id": asset["id"], "annual_percentage_rate": apr, "type": "FLEXIBLE",
        "mode": "STAKING_EARN", "enabled": enabled, "soldout": sold_out,
    }


def _lookup(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]


@pytest.fixture
def earn():
    """/earn/configs: Bitcoin's product alone, unless a test lists others."""
    with patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[_product(BTC, 0.01)])) as configs:
        yield configs


@pytest.fixture
def portfolio_api(earn):
    """Vision and Bitcoin held."""
    with patch(
        f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=_answer(VSN, BTC))
    ) as portfolio, patch(
        f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 1.5})
    ), patch(f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_lookup)
    ), patch(f"{_CLIENT}async_get_ticker", AsyncMock(return_value={"price": "10.00000000"})):
        yield portfolio


@pytest.fixture
def events(hass):
    return async_capture_events(hass, _EVENT)


def _portfolio_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": _EUR_ID},
    )
    entry.add_to_hass(hass)
    return entry


async def _setup(hass, entry) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED


async def _catalogue(hass, entry, earn, *configs: dict) -> None:
    """The next hourly read of the Earn catalogue lists `configs`."""
    earn.return_value = list(configs)
    await entry.runtime_data.earn.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)


async def _portfolio(hass, entry, portfolio_api, *assets: dict) -> None:
    portfolio_api.return_value = _answer(*assets)
    await entry.runtime_data.portfolio.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)


def _changes(events) -> list[tuple]:
    return [
        (event.data["symbol"], event.data["change"], event.data["apr_before"], event.data["apr_after"])
        for event in events
    ]


async def _set_up_with(hass, earn, *configs: dict) -> MockConfigEntry:
    earn.return_value = list(configs)
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    return entry


# --- What changes ------------------------------------------------------------------------


async def test_a_product_offered_for_a_held_asset_is_announced(hass, portfolio_api, earn, events):
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.0544))
    device = find_entry_device(dr.async_get(hass), entry.entry_id, f"{entry.entry_id}_wallet_{VSN['id']}")
    [event] = events
    assert event.data == {
        "device_id": device.id,
        "asset_id": VSN["id"],
        "symbol": "VSN",
        "name": "Vision",
        "wallet": "Vision (VSN) Wallet",
        "change": "offered",
        "apr_before": None,
        "apr_after": 5.44,
    }
    assert set(event.data) == ANNOUNCEMENT_FIELDS["earn_change"]
    state = hass.states.get(_ENTITY)
    assert state.attributes["event_type"] == "offered"
    assert {key: state.attributes[key] for key in event.data} == event.data


async def test_a_product_appearing_sold_out_is_one_offered_event(hass, portfolio_api, earn, events):
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05, sold_out=True))
    assert _changes(events) == [("VSN", "offered", None, 5.0)]


async def test_a_withdrawn_product_is_announced(hass, portfolio_api, earn, events):
    """Gone from the catalogue, or there but disabled: withdrawn, with the
    APR it had."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.06))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.06, enabled=False))
    assert _changes(events) == [
        ("VSN", "withdrawn", 5.0, None),
        ("VSN", "offered", None, 6.0),
        ("VSN", "withdrawn", 6.0, None),
    ]


async def test_a_withdrawal_names_the_apr_last_seen(hass, portfolio_api, earn, events):
    """A drift below a quarter point is no news, but a withdrawal after it
    names the APR the Staking sensor showed last, not the reference."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.052))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01))
    assert _changes(events) == [("VSN", "withdrawn", 5.2, None)]


async def test_sold_out_and_available_again(hass, portfolio_api, earn, events):
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05, sold_out=True))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    assert _changes(events) == [("VSN", "sold_out", 5.0, 5.0), ("VSN", "available_again", 5.0, 5.0)]


async def test_an_apr_move_of_a_quarter_point_is_announced(hass, portfolio_api, earn, events):
    """5.00 % to 5.24 % is no news; to 5.25 % it is -- compared unrounded."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.0524))
    assert events == []
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.0525))
    assert _changes(events) == [("VSN", "apr", 5.0, 5.25)]


async def test_the_apr_is_announced_once_its_drift_reaches_a_quarter_point(
    hass, portfolio_api, earn, events
):
    """0.1 points at a time: the third step reaches 0.3 from the APR last
    announced, and becomes the new reference."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    for apr in (0.051, 0.052, 0.053, 0.054):
        await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, apr))
    assert _changes(events) == [("VSN", "apr", 5.0, 5.3)]


async def test_sold_out_and_an_apr_move_together_are_two_events(hass, portfolio_api, earn, events):
    """One asset, two changes in one read: two events, two states."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    states: list[str] = []
    hass.bus.async_listen(
        "state_changed",
        lambda event: states.append(event.data["new_state"].attributes.get("event_type"))
        if event.data["entity_id"] == _ENTITY else None,
    )
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.06, sold_out=True))
    await asyncio.sleep(0.02)
    await hass.async_block_till_done()
    assert _changes(events) == [("VSN", "sold_out", 6.0, 6.0), ("VSN", "apr", 5.0, 6.0)]
    assert states == ["sold_out", "apr"]


async def test_offered_or_withdrawn_brings_no_apr_event(hass, portfolio_api, earn, events):
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.09))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01))
    assert [change for _, change, _, _ in _changes(events)] == ["offered", "withdrawn"]


# --- What is no news ------------------------------------------------------------------------


async def test_the_first_catalogue_announces_nothing(hass, portfolio_api, earn, events):
    await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05, sold_out=True))
    assert events == []
    assert hass.states.get(_ENTITY).state == "unknown"


async def test_a_new_wallets_earn_state_is_set_silently(hass, portfolio_api, earn, events):
    """Solana bought while offered: no news at the next read; a change after
    that is."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(SOL, 0.04))
    await _portfolio(hass, entry, portfolio_api, VSN, BTC, SOL)
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(SOL, 0.04))
    assert events == []
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(SOL, 0.05))
    assert _changes(events) == [("SOL", "apr", 4.0, 5.0)]


async def test_a_sold_and_rebought_asset_starts_silently(hass, portfolio_api, earn, events):
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    await _portfolio(hass, entry, portfolio_api, BTC)
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    await _portfolio(hass, entry, portfolio_api, VSN, BTC)
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.08, sold_out=True))
    assert events == []


async def test_an_unreadable_entry_keeps_the_assets_earn_state(hass, portfolio_api, earn, events):
    """An entry that cannot be read is no sale: the asset keeps its state
    meanwhile, and a change seen once it reads again is news."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    portfolio_api.return_value = [{**_position(VSN), "balance": {"value": "?"}}, _position(BTC), _CASH]
    await entry.runtime_data.portfolio.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05, sold_out=True))
    assert events == []
    await _portfolio(hass, entry, portfolio_api, VSN, BTC)
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05, sold_out=True))
    assert _changes(events) == [("VSN", "sold_out", 5.0, 5.0)]


async def test_an_empty_portfolio_answer_forgets_no_asset(hass, portfolio_api, earn, events):
    """An answer that lists nothing at all is no sale (as for the wallets):
    the states stay, and a change after it is news."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    portfolio_api.return_value = []
    await entry.runtime_data.portfolio.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    await _portfolio(hass, entry, portfolio_api, VSN, BTC)
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.06))
    assert _changes(events) == [("VSN", "apr", 5.0, 6.0)]


async def test_a_failed_refresh_changes_nothing(hass, portfolio_api, earn, events):
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    earn.side_effect = BitpandaApiError("down", kind="http_status", path="/earn/configs")
    await entry.runtime_data.earn.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert events == []
    earn.side_effect = None
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    assert events == []


async def test_an_answer_listing_no_product_changes_nothing(hass, portfolio_api, earn, events):
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    await _catalogue(hass, entry, earn)
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    assert events == []


async def test_only_held_assets_are_announced(hass, portfolio_api, earn, events):
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(ADA, 0.03))
    assert events == []


async def test_earn_changes_need_no_staking_sensor(hass, portfolio_api, earn, events):
    """Vision's Balance (staking) disabled: its Earn changes are news all
    the same."""
    earn.return_value = [_product(BTC, 0.01), _product(VSN, 0.05)]
    entry = _portfolio_entry(hass)
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_staking_{VSN['id']}", config_entry=entry,
        suggested_object_id="bitpanda_vision_vsn_wallet_staking",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    await _setup(hass, entry)
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is None
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.06))
    assert _changes(events) == [("VSN", "apr", 5.0, 6.0)]


async def test_the_earn_event_comes_after_the_staking_sensor_wrote(hass, portfolio_api, earn, events):
    """An automation on the event reads Balance (staking) as it is after
    the read: the sensor writes first."""
    entry = await _set_up_with(hass, earn, _product(BTC, 0.01), _product(VSN, 0.05))
    order: list[str] = []
    hass.bus.async_listen(
        "state_changed",
        lambda event: order.append("sensor")
        if event.data["entity_id"] == "sensor.bitpanda_vision_vsn_wallet_staking" else None,
    )
    hass.bus.async_listen(_EVENT, lambda event: order.append("event"))
    await _catalogue(hass, entry, earn, _product(BTC, 0.01), _product(VSN, 0.06))
    assert order == ["sensor", "event"]
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking").attributes[
        "apr_percent"
    ] == 6.0
