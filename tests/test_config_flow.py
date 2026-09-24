"""Tests for the config and options flow."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaAuthError, BitpandaRateLimitError
from custom_components.bitpanda.const import DOMAIN

from tests.conftest import load_fixture

_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"


def _btc_asset() -> dict:
    return {
        "id": "uuid-btc",
        "symbol": "BTC",
        "name": "Bitcoin",
        "type": "cryptocoin",
        "group": "coin",
    }


def _mock_entry(**option_overrides) -> MockConfigEntry:
    """A config entry shaped like one this flow itself would create."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "key", "currency": "EUR", "currency_id": _EUR_ID},
        options={
            "tracked_assets": [],
            "tracked_wallets": [],
            "asset_cache": {},
            **option_overrides,
        },
    )


def _select_options(schema, key: str) -> list[dict]:
    """Pull the `options` list back out of a field's SelectSelector."""
    for marker, validator in schema.schema.items():
        if marker == key:
            return validator.config["options"]
    raise KeyError(key)


async def _open_menu_step(hass, entry: MockConfigEntry, step_id: str):
    """Add `entry`, start its options flow, and navigate to `step_id`."""
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.MENU
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step_id}
    )


async def test_user_step_rejects_bad_key(hass):
    from custom_components.bitpanda.api import BitpandaAuthError

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_get_currencies",
        side_effect=BitpandaAuthError("nope"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "bad"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_full_setup_stores_currency_id(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "good"}
        )
        assert result["step_id"] == "currency"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"currency": "EUR"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["currency"] == "EUR"
    assert result["data"]["currency_id"] == "b88b8466-efe3-11eb-b56f-0691764446a7"
    assert result["options"]["tracked_assets"] == []
    assert result["options"]["asset_cache"] == {}


async def test_config_flow_version_is_two(hass):
    from custom_components.bitpanda.config_flow import BitpandaConfigFlow

    assert BitpandaConfigFlow.VERSION == 2


# --- Options flow: add_asset / add_wallet error handling -------------------
#
# `AssetResolver.async_resolve` re-raises BitpandaAuthError and
# BitpandaRateLimitError instead of returning None for them. These three
# tests confirm the options flow turns that distinction into form errors
# instead of letting the exception escape unhandled (see task-15-report.md,
# check 1).


async def test_add_asset_unknown_symbol_shows_form_error(hass):
    result = await _open_menu_step(hass, _mock_entry(), "add_asset")
    assert result["step_id"] == "add_asset"

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_get_assets",
        AsyncMock(return_value=[]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"symbol": "nope"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_asset"
    assert result["errors"]["symbol"] == "unknown_symbol"


async def test_add_asset_auth_error_maps_to_invalid_auth(hass):
    result = await _open_menu_step(hass, _mock_entry(), "add_asset")

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_get_assets",
        AsyncMock(side_effect=BitpandaAuthError("nope")),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"symbol": "btc"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_asset"
    assert result["errors"]["base"] == "invalid_auth"


async def test_add_wallet_rate_limit_maps_to_rate_limited(hass):
    result = await _open_menu_step(hass, _mock_entry(), "add_wallet")

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_get_assets",
        AsyncMock(side_effect=BitpandaRateLimitError("slow down")),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"symbol": "btc"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_wallet"
    assert result["errors"]["base"] == "rate_limited"


async def test_add_asset_resolves_id_and_persists_cache_on_save(hass):
    result = await _open_menu_step(hass, _mock_entry(), "add_asset")

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_get_assets",
        AsyncMock(return_value=[_btc_asset()]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"symbol": "btc"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "save"}
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["tracked_assets"] == ["uuid-btc"]
    assert result["data"]["asset_cache"]["BTC"]["id"] == "uuid-btc"


# --- Options flow: config_entry access --------------------------------------
#
# `BitpandaOptionsFlowHandler` never assigns `self.config_entry` — on this
# installed Home Assistant version (2026.2.3) it is a read-only @property
# (see task-15-report.md, check 2). Every test above already exercises this
# indirectly (`_load()` and `_resolver()` both read `self.config_entry`), but
# this one pins the actual behaviour: assigning it must fail the way the
# base class defines it, so a future edit cannot silently reintroduce the
# old pattern.


def test_config_entry_has_no_setter():
    from custom_components.bitpanda.config_flow import BitpandaOptionsFlowHandler

    handler = BitpandaOptionsFlowHandler()
    with pytest.raises(AttributeError):
        handler.config_entry = _mock_entry()


# --- Options flow: removing an asset with no cache entry --------------------
#
# `async_step_remove` builds its SelectSelector options from `self._cache`,
# keyed by asset id. A tracked id that fell out of the cache (or was never
# in it) must still show up as a removable option instead of silently being
# excluded, or the user would be stuck with an entry they cannot delete
# (see task-15-report.md, check 3).


async def test_remove_step_offers_a_tracked_id_missing_from_cache(hass):
    entry = _mock_entry(tracked_assets=["uuid-ghost"], asset_cache={})
    result = await _open_menu_step(hass, entry, "remove")

    assert result["step_id"] == "remove"
    options = _select_options(result["data_schema"], "tracked_assets")
    assert {"value": "uuid-ghost", "label": "uuid-ghost (other)"} in options


async def test_remove_step_can_remove_a_tracked_id_missing_from_cache(hass):
    entry = _mock_entry(tracked_assets=["uuid-ghost"], asset_cache={})
    result = await _open_menu_step(hass, entry, "remove")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"tracked_assets": [], "tracked_wallets": []}
    )
    assert result["type"] == data_entry_flow.FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "save"}
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["tracked_assets"] == []
