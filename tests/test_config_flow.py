"""Tests for the config and options flow."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaAuthError, BitpandaRateLimitError
from custom_components.bitpanda.const import API_KEY_URL, DOMAIN

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
    """A key with none of the required scopes: identical to a wrong key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=["balance", "transaction", "earn"]),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "bad"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_user_step_missing_scopes_names_them(hass):
    """A key valid for one scope but not the other two: named, not rejected outright."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=["transaction", "earn"]),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "partial"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "missing_scopes"
    assert (
        result["description_placeholders"]["missing_scopes"]
        == "Transaktion (Transaction), Earn (Read)"
    )


async def test_user_step_rate_limited_maps(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(side_effect=BitpandaRateLimitError("slow down")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "key"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "rate_limited"


async def test_user_step_shows_api_key_url_placeholder(hass):
    """The initial form (no submission yet) still carries the key-page link."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL


async def test_user_step_all_scopes_present_proceeds_to_currency(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=[]),
    ), patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "good"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "currency"


async def test_user_step_stores_stripped_api_key(hass):
    """A pasted key with surrounding whitespace/newlines is stored trimmed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=[]),
    ), patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "  good  \n"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"currency": "EUR"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["api_key"] == "good"


async def test_full_setup_stores_currency_id(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=[]),
    ), patch(
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


# --- Reauth flow -------------------------------------------------------
#
# Triggered automatically when a coordinator's plain async_refresh() meets
# ConfigEntryAuthFailed (see coordinator.py and __init__.py). Replaces the
# key in place -- tracked assets, entity_ids and history all survive, unlike
# deleting and re-adding the entry.
#
# A successful reauth/reconfigure ends up in _async_replace_key
# (config_flow.py), which picks exactly one reload path: an entry that
# finished setup already has the update listener registered at
# __init__.py's async_setup_entry (`entry.add_update_listener(...)`), which
# reloads on any entry change -- so that path only updates the entry and
# lets the listener do the reloading. An entry with no listener (the
# typical reauth case: setup failed before that line ever ran) falls back
# to async_update_reload_and_abort, whose own explicit
# ConfigEntries.async_schedule_reload is then the only reload. Both paths
# are patched/observed below rather than left to run for real, since a real
# reload would exercise this integration's actual async_setup_entry -- and a
# real network call -- from inside a unit test.


async def test_reauth_confirm_initial_form_carries_api_key_url(hass):
    entry = _mock_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL


async def test_reauth_confirm_missing_scopes_reshows_form_without_leaking_key(
    hass, caplog
):
    entry = _mock_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)

    secret = "totally-secret-reauth-key"
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=["earn"]),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": secret}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"]["base"] == "missing_scopes"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL
    assert result["description_placeholders"]["missing_scopes"] == "Earn (Read)"
    # A rejected key must not change what is stored.
    assert entry.data["api_key"] == "key"
    assert entry.options == {
        "tracked_assets": [],
        "tracked_wallets": [],
        "asset_cache": {},
    }
    # The key must never reach a title, a log line, or a placeholder.
    assert secret not in entry.title
    assert secret not in repr(result["description_placeholders"])
    assert secret not in caplog.text


async def test_reauth_confirm_with_listener_lets_the_listener_reload(hass):
    """A loaded entry's update listener must be the only thing that reloads
    it. async_update_reload_and_abort's own async_schedule_reload must not
    also fire, or the entry would reload twice (see task-22-report.md, Fix
    round 1).
    """
    entry = _mock_entry()
    entry.add_to_hass(hass)
    listener = AsyncMock()
    entry.add_update_listener(listener)
    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=[]),
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as mock_reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "  new-key  \n"}
        )
        # Update listeners are fired via hass.async_create_task (see
        # ConfigEntries._async_save_and_notify), so the listener has only
        # been scheduled, not necessarily run, until this is awaited.
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "new-key"
    listener.assert_called_once()
    mock_reload.assert_not_called()


async def test_reauth_confirm_without_listener_schedules_a_reload(hass):
    """The typical reauth case: the stored key was rejected on the first
    portfolio refresh, so async_setup_entry raised before ever reaching the
    line that registers the update listener. No listener exists to reload
    the entry, so the explicit reload is the only one there is.
    """
    entry = _mock_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=[]),
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as mock_reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "  new-key  \n"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "new-key"
    # Only the key changes.
    assert entry.data["currency"] == "EUR"
    assert entry.data["currency_id"] == _EUR_ID
    assert entry.options == {
        "tracked_assets": [],
        "tracked_wallets": [],
        "asset_cache": {},
    }
    assert "new-key" not in entry.title
    mock_reload.assert_called_once()


# --- Reconfigure flow ----------------------------------------------------
#
# User-initiated from the entry's menu, otherwise the same shape as reauth.
# The currency step is skipped entirely -- reconfigure only ever replaces
# the key; the currency step itself already tells the user it cannot be
# changed after setup.


async def test_reconfigure_initial_form_carries_api_key_url(hass):
    entry = _mock_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL


async def test_reconfigure_missing_scopes_reshows_form_without_leaking_key(
    hass, caplog
):
    entry = _mock_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)

    secret = "totally-secret-reconfigure-key"
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=["earn"]),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": secret}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"]["base"] == "missing_scopes"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL
    assert entry.data["api_key"] == "key"
    assert entry.options == {
        "tracked_assets": [],
        "tracked_wallets": [],
        "asset_cache": {},
    }
    assert secret not in entry.title
    assert secret not in repr(result["description_placeholders"])
    assert secret not in caplog.text


async def test_reconfigure_with_listener_lets_the_listener_reload(hass):
    """Same double-reload hazard as reauth: a loaded entry's update listener
    must be the only thing that reloads it.
    """
    entry = _mock_entry()
    entry.add_to_hass(hass)
    listener = AsyncMock()
    entry.add_update_listener(listener)
    result = await entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=[]),
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as mock_reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "  new-key  \n"}
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["api_key"] == "new-key"
    listener.assert_called_once()
    mock_reload.assert_not_called()


async def test_reconfigure_without_listener_schedules_a_reload(hass):
    entry = _mock_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=[]),
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as mock_reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "  new-key  \n"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["api_key"] == "new-key"
    # The currency is fixed: reconfigure changes only the key.
    assert entry.data["currency"] == "EUR"
    assert entry.data["currency_id"] == _EUR_ID
    assert entry.options == {
        "tracked_assets": [],
        "tracked_wallets": [],
        "asset_cache": {},
    }
    assert "new-key" not in entry.title
    mock_reload.assert_called_once()


# --- user step: error re-render keeps the api_key_url placeholder --------
#
# Home Assistant's frontend substitutes description_placeholders into both
# a step's description and any shown error string (confirmed in the frontend
# source -- see task-22-report.md). A step that forgets to carry a
# placeholder through an error re-render would show the user the literal
# text "{api_key_url}" instead of a working link.


async def test_user_step_error_rerender_keeps_api_key_url_placeholder(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient."
        "async_missing_scopes",
        AsyncMock(return_value=["earn"]),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "partial"}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["base"] == "missing_scopes"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL
