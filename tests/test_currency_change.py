"""A Portfolio currency change end to end, through a real recorder.

Confirming the change deletes every Portfolio sensor with its history, then
recreates them in the new currency under the same entity IDs -- with exactly
one reload, and without the update listener Home Assistant warns about. What
the version 1 migration left in place keeps its entity and its history.
"""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_purge_done,
    async_wait_recording_done,
)

from custom_components.bitpanda.const import DOMAIN

from tests.conftest import load_fixture

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_USD_ID = "b88b8879-efe3-11eb-b56f-0691764446a7"
_WALLET = "sensor.bitpanda_vision_vsn_wallet"
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


async def _history(hass, entity_id: str) -> list[tuple[str, str | None]]:
    """(state, unit) of every state the recorder holds for `entity_id`."""
    start = dt_util.utcnow() - timedelta(hours=1)
    states = await get_instance(hass).async_add_executor_job(
        get_significant_states, hass, start, None, [entity_id]
    )
    return [
        (state.state, state.attributes.get("unit_of_measurement"))
        for state in states.get(entity_id, [])
    ]


async def test_a_currency_change_recreates_the_sensors_without_the_old_history(
    hass, portfolio_api, caplog
):
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": _EUR_ID},
    )
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_wallet_fiat_USD", config_entry=entry,
        suggested_object_id=_LEFTOVER.split(".", 1)[1],
    )
    hass.states.async_set(_LEFTOVER, "5.0", {"unit_of_measurement": "USD"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)
    entity_ids = _entity_ids(hass, entry)
    assert {_WALLET, _LEFTOVER} <= set(entity_ids)
    assert await _history(hass, _WALLET) == [("50.0", "EUR")]
    assert await _history(hass, _LEFTOVER) == [("5.0", "USD")]
    calls = portfolio_api.call_count
    [group] = entry.subentries.values()

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"currency": "usd"})
    assert result["step_id"] == "confirm_currency"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["reason"] == "currency_changed"
    await async_wait_purge_done(hass)

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
    assert await _history(hass, _WALLET) == [("50.0", "USD")]
    # The leftover is not the Portfolio's own: the migration promised it
    # stays until the user deletes it, and so does its history.
    assert await _history(hass, _LEFTOVER) == [("5.0", "USD")]
    assert "update listener" not in caplog.text
