"""A Portfolio currency change end to end, through a real recorder.

Confirming the change deletes every Portfolio sensor with its history and
its long-term statistics, then recreates them in the new currency under the
same entity IDs -- with exactly one reload, and without the update listener
Home Assistant warns about. What the version 1 migration left in place keeps
its entity and its history.

A new Portfolio after a deleted one takes the integration's entity IDs
again, where the deleted one's statistics may wait in another currency.
"""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_purge_done,
    async_wait_recording_done,
    do_adhoc_statistics,
    get_start_time,
)

from custom_components.bitpanda.const import DOMAIN, PORTFOLIO_UPDATE_INTERVAL

from tests.conftest import load_fixture, recorded_history, statistics_units

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_USD_ID = "b88b8879-efe3-11eb-b56f-0691764446a7"
_TOTAL = "sensor.bitpanda_portfolio_total"
_CASH = "sensor.bitpanda_portfolio_cash"
_WALLET = "sensor.bitpanda_vision_vsn_wallet_available"
# A fiat wallet the version 1 migration left in place: Portfolio Cash covers
# every fiat balance now.
_LEFTOVER = "sensor.bitpanda_wallets_usd_wallet"

VSN = next(a for a in load_fixture("assets-sample.json") if a["symbol"] == "VSN")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Replaces the shared fixture of the same name for this module: the
    recorder must be set up before Home Assistant itself, and this order of
    arguments is what guarantees it."""
    return


def _lookup(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]


@pytest.fixture
def portfolio_api():
    response = [
        {
            "asset_id": VSN["id"],
            "balance": {"value": "100.00000000"},
            "available_balance": {"value": "25.00000000"},
            "currency_balance": {"value": "200.00"},
        },
        {"currency_id": _EUR_ID, "balance": {"value": "10.00"}},
    ]
    with patch(f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=response)) as portfolio, patch(
        f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 1.5})
    ), patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])
    ), patch(f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_lookup)), patch(
        f"{_CLIENT}async_get_currencies", AsyncMock(return_value=load_fixture("currencies.json"))
    ):
        yield portfolio


def _entity_ids(hass, entry) -> list[str]:
    return sorted(
        reg_entry.entity_id
        for reg_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    )


def _portfolio(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": _EUR_ID},
    )
    entry.add_to_hass(hass)
    return entry


async def _change_currency_to_usd(hass, entry) -> None:
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"currency": "usd"})
    assert result["step_id"] == "confirm_currency"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["reason"] == "currency_changed"
    await async_wait_purge_done(hass)


async def test_a_currency_change_clears_the_statistics_of_every_portfolio_sensor(
    hass, portfolio_api
):
    """Every Portfolio sensor keeps long-term statistics, in the Portfolio
    currency -- the returns in %. Old-currency statistics would sit beside
    the new currency's, so the change clears them, for every one."""
    entry = _portfolio(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)
    sensors = _entity_ids(hass, entry)
    # Eight figures, and the staked VSN's Wallet, Staking and Total.
    assert len(sensors) == 11
    do_adhoc_statistics(hass, start=get_start_time(dt_util.utcnow()))
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, sensors) == {
        entity_id: "%" if "_return_" in entity_id else "EUR" for entity_id in sensors
    }

    await _change_currency_to_usd(hass, entry)
    await async_wait_recording_done(hass)

    assert _entity_ids(hass, entry) == sensors
    assert await statistics_units(hass, sensors) == {}


async def test_a_currency_change_recreates_the_sensors_without_the_old_history(
    hass, portfolio_api, caplog
):
    entry = _portfolio(hass)
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_wallet_fiat_USD", config_entry=entry,
        suggested_object_id=_LEFTOVER.split(".", 1)[1],
    )
    hass.states.async_set(_LEFTOVER, "5.0", {"unit_of_measurement": "USD"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)
    entity_ids = _entity_ids(hass, entry)
    assert {_WALLET, _LEFTOVER} <= set(entity_ids)
    assert await recorded_history(hass, _WALLET) == [("50.0", "EUR")]
    assert await recorded_history(hass, _LEFTOVER) == [("5.0", "USD")]
    calls = portfolio_api.call_count
    [group] = entry.subentries.values()

    await _change_currency_to_usd(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.data["currency"] == "USD"
    assert _entity_ids(hass, entry) == entity_ids
    # The purge (purge.py) removes entities and devices, not the wallet
    # group's subentry; the reload then refills the same group.
    [after] = entry.subentries.values()
    assert (after.subentry_id, after.title) == (group.subentry_id, group.title)
    assert er.async_get(hass).async_get(_WALLET).config_subentry_id == after.subentry_id
    assert hass.states.get(_WALLET).attributes["unit_of_measurement"] == "USD"
    # One reload: one more /portfolio request, now in the new currency.
    assert portfolio_api.call_count == calls + 1
    assert portfolio_api.call_args.kwargs == {"equivalent_currency_id": _USD_ID}
    # The EUR history is gone; the state the recreated sensor wrote is kept.
    assert await recorded_history(hass, _WALLET) == [("50.0", "USD")]
    # The leftover is not the Portfolio's own: the migration promised it
    # stays until the user deletes it, and so does its history.
    assert await recorded_history(hass, _LEFTOVER) == [("5.0", "USD")]
    assert "update listener" not in caplog.text


async def _next_refresh(hass, freezer) -> None:
    """The Portfolio's next regular refresh: Home Assistant's clock moves on
    past its update interval, and the refresh it scheduled runs to its end
    -- a background task, which only wait_background_tasks waits for."""
    freezer.tick(PORTFOLIO_UPDATE_INTERVAL + timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_an_empty_answer_right_after_a_currency_change_waits_for_confirmation(
    hass, portfolio_api, freezer
):
    """The purge has just removed the wallets when the reload asks, so none
    is registered; that the account listed something is remembered all the
    same. An empty answer then -- as likely a glitch at Bitpanda as ever --
    leaves the Portfolio unavailable until three answers in a row, at the
    usual pace, confirm it, rather than start the new currency's history
    with a 0."""
    entry = _portfolio(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)
    portfolio_api.return_value = []

    await _change_currency_to_usd(hass, entry)

    assert er.async_get(hass).async_get(_WALLET) is None
    for _ in range(2):
        assert hass.states.get(_TOTAL).state == "unavailable"
        await _next_refresh(hass, freezer)
    assert float(hass.states.get(_TOTAL).state) == 0.0


# --- A new Portfolio after a deleted one -------------------------------------------


async def test_a_new_portfolio_takes_the_integrations_entity_ids_again(hass, portfolio_api):
    """A deleted Portfolio keeps its statistics under its sensors' IDs. A new
    setup is a new entry with new unique_ids, so Home Assistant restores none
    of the deleted entry's IDs -- not even one the user gave: the new sensors
    take the integration's own IDs, where async_find_old_statistics looks."""
    old = _portfolio(hass)
    assert await hass.config_entries.async_setup(old.entry_id)
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity(_CASH, new_entity_id="sensor.my_cash")
    ids = _entity_ids(hass, old)
    await hass.config_entries.async_remove(old.entry_id)

    new = _portfolio(hass)
    assert await hass.config_entries.async_setup(new.entry_id)
    await hass.async_block_till_done()

    assert _entity_ids(hass, new) == sorted(
        _CASH if entity_id == "sensor.my_cash" else entity_id for entity_id in ids
    )
