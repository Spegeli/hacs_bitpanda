"""The Portfolio's event entities (event.py): one per kind of announcement, on
the Portfolio device, each showing what its bus event fired -- the same call
fires both (announcements.async_announce). End to end, Bitpanda mocked as in
tests/test_init.py."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_mock_service,
    mock_restore_cache_with_extra_data,
)

from custom_components.bitpanda import announcements
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import find_entry_device
from custom_components.bitpanda.naming import portfolio_event_entity_id

from tests.conftest import load_fixture, price_group

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"


def _record(symbol: str) -> dict:
    return next(a for a in load_fixture("assets-sample.json") if a["symbol"] == symbol)


VSN, BTC = _record("VSN"), _record("BTC")
NEW_WALLET = "event.bitpanda_portfolio_new_wallet"
STAKING_REWARD = "event.bitpanda_portfolio_staking_reward"
EARN_CHANGE = "event.bitpanda_portfolio_earn_change"
_VSN_POSITION = {
    "asset_id": VSN["id"],
    "balance": {"value": "100.00000000"},
    "available_balance": {"value": "100.00000000"},
    "currency_balance": {"value": "200.00"},
}
_CASH = {"currency_id": _EUR_ID, "balance": {"value": "10.00"}}


def _lookup(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]


@pytest.fixture
def portfolio_api():
    """Bitpanda as the Portfolio asks it: Vision and cash; nothing offered,
    no payout."""
    with patch(
        f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=[_VSN_POSITION, _CASH])
    ) as portfolio, patch(
        f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 1.5})
    ), patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])
    ), patch(f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_lookup)), patch(
        f"{_CLIENT}async_get_ticker", AsyncMock(return_value={"price": "2.00000000"})
    ):
        yield portfolio


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


def _announce(hass, entry, key: str, event_type: str, bus_event: str, **data) -> None:
    announcements.async_announce(
        hass, entry.entry_id, bus_event=bus_event, entity_key=key, event_type=event_type,
        data=data,
    )


async def _drained(hass) -> None:
    """Events queued a millisecond apart are written: real time passes."""
    await asyncio.sleep(0.02)
    await hass.async_block_till_done()


async def _count_runs(hass, alias: str, trigger: dict) -> list:
    """An automation `alias` on `trigger`; the calls of the service it runs."""
    calls = async_mock_service(hass, "test", alias)
    assert await async_setup_component(
        hass,
        "automation",
        {"automation": [{"alias": alias, "triggers": [trigger],
                         "actions": [{"action": f"test.{alias}"}]}]},
    )
    await hass.async_block_till_done()
    return calls


def test_the_event_entity_ids_follow_the_fixed_scheme():
    """English and fixed, as every entity ID of the integration; the keys are
    no Portfolio figures (naming.PORTFOLIO_KEYS)."""
    assert [portfolio_event_entity_id(key) for key in announcements.PORTFOLIO_EVENT_TYPES] == [
        NEW_WALLET, STAKING_REWARD, EARN_CHANGE,
    ]


async def test_the_portfolio_gets_three_event_entities_on_its_device(hass, portfolio_api):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    device = find_entry_device(dr.async_get(hass), entry.entry_id, f"{entry.entry_id}_portfolio")
    events = {
        reg_entry.entity_id: reg_entry
        for reg_entry in er.async_entries_for_device(er.async_get(hass), device.id)
        if reg_entry.domain == "event"
    }
    assert set(events) == {NEW_WALLET, STAKING_REWARD, EARN_CHANGE}
    assert {reg_entry.unique_id for reg_entry in events.values()} == {
        f"{entry.entry_id}_portfolio_{key}" for key in ("new_wallet", "staking_reward", "earn_change")
    }
    assert all(reg_entry.config_subentry_id is None for reg_entry in events.values())
    assert hass.states.get(NEW_WALLET).attributes["event_types"] == ["wallet_added"]
    assert hass.states.get(STAKING_REWARD).attributes["event_types"] == ["staking_reward_received"]
    assert hass.states.get(EARN_CHANGE).attributes["event_types"] == [
        "offered", "withdrawn", "sold_out", "available_again", "apr",
    ]
    assert hass.states.get(NEW_WALLET).state == "unknown"


async def test_the_price_tracker_gets_no_event_entity(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker"}, options={"extra_currencies": []},
        subentries_data=[price_group("crypto", BTC)],
    )
    entry.add_to_hass(hass)
    with patch(f"{_CLIENT}async_get_ticker", AsyncMock(return_value={"price": "100.00000000"})):
        await _setup(hass, entry)
    assert not [
        reg_entry
        for reg_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if reg_entry.domain == "event"
    ]


async def test_an_event_entity_shows_a_fired_event_with_its_data(hass, portfolio_api):
    """One call fires the bus event and the entity's, with the same data;
    the other entities stay as they are."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    bus = async_capture_events(hass, "bitpanda_wallet_added")
    _announce(hass, entry, "new_wallet", "wallet_added", "bitpanda_wallet_added",
              asset_id=BTC["id"], wallet="Bitcoin (BTC) Wallet")
    await hass.async_block_till_done()
    assert [event.data for event in bus] == [
        {"asset_id": BTC["id"], "wallet": "Bitcoin (BTC) Wallet"}
    ]
    state = hass.states.get(NEW_WALLET)
    assert state.state not in ("unknown", "unavailable")
    assert state.attributes["event_type"] == "wallet_added"
    assert (state.attributes["asset_id"], state.attributes["wallet"]) == (
        BTC["id"], "Bitcoin (BTC) Wallet"
    )
    assert hass.states.get(STAKING_REWARD).state == "unknown"


async def test_a_new_wallet_shows_on_the_new_wallet_entity(hass, portfolio_api):
    """Bitcoin bought: the announcement of its wallet is the entity's event,
    with the bus event's data."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    bus = async_capture_events(hass, "bitpanda_wallet_added")
    btc = {**_VSN_POSITION, "asset_id": BTC["id"], "currency_balance": {"value": "500.00"}}
    portfolio_api.return_value = [_VSN_POSITION, btc, _CASH]
    await entry.runtime_data.portfolio.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    [event] = bus
    state = hass.states.get(NEW_WALLET)
    assert state.attributes["event_type"] == "wallet_added"
    assert {key: state.attributes[key] for key in event.data} == event.data


# The README's trigger on an event entity: never on the way to or from
# unavailable -- a reload -- or unknown.
_GUARDED = {"not_from": ["unavailable", "unknown"], "not_to": ["unavailable", "unknown"]}


async def test_two_events_in_one_go_become_two_states(hass, portfolio_api):
    """Two payouts announced in one pass: two states, a millisecond apart at
    least, so that an automation on the entity runs twice."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    _announce(hass, entry, "staking_reward", "staking_reward_received",
              "bitpanda_staking_reward_received", symbol="ADA")
    await _drained(hass)
    calls = await _count_runs(
        hass, "payout", {"trigger": "state", "entity_id": STAKING_REWARD, **_GUARDED}
    )
    for symbol in ("VSN", "SOL"):
        _announce(hass, entry, "staking_reward", "staking_reward_received",
                  "bitpanda_staking_reward_received", symbol=symbol)
    await _drained(hass)
    assert len(calls) == 2
    assert hass.states.get(STAKING_REWARD).attributes["symbol"] == "SOL"


async def test_events_queued_close_together_are_written_in_order(hass, portfolio_api):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    seen: list[str] = []
    hass.bus.async_listen(
        "state_changed",
        lambda event: seen.append(event.data["new_state"].attributes.get("symbol"))
        if event.data["entity_id"] == STAKING_REWARD else None,
    )
    for symbol in ("A", "B", "C"):
        _announce(hass, entry, "staking_reward", "staking_reward_received",
                  "bitpanda_staking_reward_received", symbol=symbol)
    await _drained(hass)
    assert seen == ["A", "B", "C"]


async def test_a_disabled_event_entity_leaves_the_bus_event_alone(hass, portfolio_api):
    entry = _portfolio_entry(hass)
    er.async_get(hass).async_get_or_create(
        "event", DOMAIN, f"{entry.entry_id}_portfolio_staking_reward", config_entry=entry,
        suggested_object_id="bitpanda_portfolio_staking_reward",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    await _setup(hass, entry)
    bus = async_capture_events(hass, "bitpanda_staking_reward_received")
    _announce(hass, entry, "staking_reward", "staking_reward_received",
              "bitpanda_staking_reward_received", symbol="VSN")
    await _drained(hass)
    assert len(bus) == 1
    assert hass.states.get(STAKING_REWARD) is None


async def test_an_event_entity_restores_its_last_event_without_firing(hass, portfolio_api):
    """A start shows the last event again, as Home Assistant restores it,
    and announces nothing."""
    mock_restore_cache_with_extra_data(hass, [(
        State(NEW_WALLET, "2026-10-20T10:00:00.000+00:00",
              {"event_type": "wallet_added", "wallet": "Gold (XAU) Wallet"}),
        {"last_event_type": "wallet_added", "last_event_attributes": {"wallet": "Gold (XAU) Wallet"}},
    )])
    bus = async_capture_events(hass, "bitpanda_wallet_added")
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    state = hass.states.get(NEW_WALLET)
    assert state.state == "2026-10-20T10:00:00.000+00:00"
    assert state.attributes["wallet"] == "Gold (XAU) Wallet"
    assert bus == []


async def test_a_reload_runs_a_plain_state_trigger_but_not_the_guarded_one(
    hass, portfolio_api
):
    """At a reload the entity is unavailable for a moment, then shows its
    last event again: a plain state trigger runs twice, the README's -- with
    `not_from` and `not_to` [unavailable, unknown] -- not at all."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    _announce(hass, entry, "new_wallet", "wallet_added", "bitpanda_wallet_added",
              wallet="Bitcoin (BTC) Wallet")
    await _drained(hass)
    plain = await _count_runs(hass, "plain", {"trigger": "state", "entity_id": NEW_WALLET})
    guarded = await _count_runs(
        hass, "guarded", {"trigger": "state", "entity_id": NEW_WALLET, **_GUARDED}
    )
    shown = hass.states.get(NEW_WALLET).state
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(NEW_WALLET).state == shown
    assert (len(plain), len(guarded)) == (2, 0)
