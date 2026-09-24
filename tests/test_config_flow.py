"""Tests for the config and options flow."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaAuthError, BitpandaRateLimitError
from custom_components.bitpanda.const import API_KEY_URL, DOMAIN
from custom_components.bitpanda.coordinator import Holding, PortfolioData

from tests.conftest import load_fixture

_INTEGRATION_DIR = Path(__file__).parent.parent / "custom_components" / "bitpanda"

_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"


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


# --- Options flow: add_asset (price tracker) --------------------------------
#
# Maintainer feedback from the live instance (2026-09-24): a free-text symbol
# field is unusable -- a user knows neither the 14,000 catalogue symbols nor
# their own holdings' exact symbols. add_asset is now a category choice
# followed by a multi-select list of real assets; the value submitted is
# always a UUID, so there is nothing left here for a symbol to be ambiguous
# about (see task-23-brief.md).


def _btc() -> dict:
    return {"id": "uuid-btc", "symbol": "BTC", "name": "Bitcoin",
            "type": "cryptocoin", "group": "coin"}


def _eth() -> dict:
    return {"id": "uuid-eth", "symbol": "ETH", "name": "Ethereum",
            "type": "cryptocoin", "group": "coin"}


async def test_add_asset_category_step_lists_only_that_categorys_assets_minus_tracked(
    hass,
):
    entry = _mock_entry(tracked_assets=["uuid-eth"])
    result = await _open_menu_step(hass, entry, "add_asset")
    assert result["step_id"] == "asset_category"

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_list_assets",
        AsyncMock(return_value=[_btc(), _eth()]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"category": "crypto"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_asset"
    options = _select_options(result["data_schema"], "assets")
    assert options == [{"value": "uuid-btc", "label": "Bitcoin / BTC"}]


async def test_add_asset_submitting_two_ids_appends_both_and_persists_cache(hass):
    result = await _open_menu_step(hass, _mock_entry(), "add_asset")

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_list_assets",
        AsyncMock(return_value=[_btc(), _eth()]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"category": "crypto"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"assets": ["uuid-btc", "uuid-eth"]}
        )

    assert result["type"] == data_entry_flow.FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "save"}
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["tracked_assets"] == ["uuid-btc", "uuid-eth"]
    assert result["data"]["asset_cache"]["uuid-btc"]["id"] == "uuid-btc"
    assert result["data"]["asset_cache"]["uuid-eth"]["id"] == "uuid-eth"


async def test_add_asset_does_not_cache_unchosen_catalogue_entries(hass):
    """A category can list thousands of assets (stocks alone is 10,182) --
    only the ones actually picked belong in the persisted per-entry cache,
    or every save would carry the weight of the whole category.
    """
    result = await _open_menu_step(hass, _mock_entry(), "add_asset")

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_list_assets",
        AsyncMock(return_value=[_btc(), _eth()]),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"category": "crypto"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"assets": ["uuid-btc"]}
        )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "save"}
    )

    assert result["data"]["tracked_assets"] == ["uuid-btc"]
    assert list(result["data"]["asset_cache"]) == ["uuid-btc"]


async def test_add_asset_category_listing_is_cached_for_24_hours(hass):
    """The first stock listing alone costs ~103 requests -- the 24 hour cache
    is what keeps a second open of the same category free (task-23-brief.md).
    """
    entry = _mock_entry()
    entry.add_to_hass(hass)
    mock_list = AsyncMock(return_value=[_btc()])

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_list_assets",
        mock_list,
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_asset"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"category": "crypto"}
        )
        assert result["step_id"] == "add_asset"
        assert mock_list.call_count == 1

        # A second, independent options-flow session for the same category.
        result2 = await hass.config_entries.options.async_init(entry.entry_id)
        result2 = await hass.config_entries.options.async_configure(
            result2["flow_id"], {"next_step_id": "add_asset"}
        )
        result2 = await hass.config_entries.options.async_configure(
            result2["flow_id"], {"category": "crypto"}
        )
        assert result2["step_id"] == "add_asset"

    assert mock_list.call_count == 1


async def test_add_asset_stock_category_merges_both_filters(hass):
    """Stocks exist in two families (equity_security/equity_stock and
    security/stock) -- often the same company twice -- and both are genuine,
    priced listings that must both be offered (task-23-brief.md).
    """
    accenture_plc = {
        "id": "id-equity", "symbol": "ACN", "name": "Accenture PLC",
        "isin": "IE00B4BNMY34", "type": "equity_security", "group": "equity_stock",
    }
    accenture = {
        "id": "id-security", "symbol": "ACN", "name": "Accenture",
        "isin": "IE00B4BNMY34", "type": "security", "group": "stock",
    }

    def _list_assets(type_, group=None):
        return {
            ("equity_security", "equity_stock"): [accenture_plc],
            ("security", "stock"): [accenture],
        }.get((type_, group), [])

    result = await _open_menu_step(hass, _mock_entry(), "add_asset")

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_list_assets",
        AsyncMock(side_effect=_list_assets),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"category": "stock"}
        )

    options = _select_options(result["data_schema"], "assets")
    assert {o["value"] for o in options} == {"id-equity", "id-security"}


async def test_add_asset_auth_error_maps_to_invalid_auth(hass):
    result = await _open_menu_step(hass, _mock_entry(), "add_asset")

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_list_assets",
        AsyncMock(side_effect=BitpandaAuthError("nope")),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"category": "crypto"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_asset"
    assert result["errors"]["base"] == "invalid_auth"


async def test_add_asset_rate_limit_maps_to_rate_limited(hass):
    result = await _open_menu_step(hass, _mock_entry(), "add_asset")

    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_list_assets",
        AsyncMock(side_effect=BitpandaRateLimitError("slow down")),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"category": "crypto"}
        )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_asset"
    assert result["errors"]["base"] == "rate_limited"


# --- Options flow: add_wallet ------------------------------------------------
#
# The list is built from holdings, never typed -- a wallet id is always the
# UUID of an asset the user actually holds.


def _store_with_holdings(hass, entry, holdings: dict[str, Holding]) -> None:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "portfolio_coordinator": SimpleNamespace(
            data=PortfolioData(holdings=holdings)
        ),
    }


async def test_add_wallet_lists_holdings_minus_tracked_ids(hass):
    entry = _mock_entry(
        tracked_wallets=["uuid-eth"],
        asset_cache={"uuid-btc": _btc(), "uuid-eth": _eth()},
    )
    entry.add_to_hass(hass)
    _store_with_holdings(
        hass, entry,
        {
            "uuid-btc": Holding(asset_id="uuid-btc", balance=1.0, available=1.0,
                                staked=0.0, value=100.0),
            "uuid-eth": Holding(asset_id="uuid-eth", balance=1.0, available=1.0,
                                staked=0.0, value=50.0),
        },
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_wallet"}
    )

    assert result["step_id"] == "add_wallet"
    options = _select_options(result["data_schema"], "wallets")
    assert options == [{"value": "uuid-btc", "label": "Bitcoin / BTC"}]


async def test_add_wallet_submitting_appends_and_returns_to_menu(hass):
    entry = _mock_entry(asset_cache={"uuid-btc": _btc()})
    entry.add_to_hass(hass)
    _store_with_holdings(
        hass, entry,
        {"uuid-btc": Holding(asset_id="uuid-btc", balance=1.0, available=1.0,
                             staked=0.0, value=100.0)},
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_wallet"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"wallets": ["uuid-btc"]}
    )

    assert result["type"] == data_entry_flow.FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "save"}
    )
    assert result["data"]["tracked_wallets"] == ["uuid-btc"]


async def test_add_wallet_looks_up_a_held_id_missing_from_cache_once(hass):
    entry = _mock_entry(asset_cache={})
    entry.add_to_hass(hass)
    _store_with_holdings(
        hass, entry,
        {"uuid-btc": Holding(asset_id="uuid-btc", balance=1.0, available=1.0,
                             staked=0.0, value=100.0)},
    )

    mock_get_assets = AsyncMock(return_value=[_btc()])
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_get_assets",
        mock_get_assets,
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_wallet"}
        )

    mock_get_assets.assert_called_once_with(asset_id="uuid-btc")
    options = _select_options(result["data_schema"], "wallets")
    assert options == [{"value": "uuid-btc", "label": "Bitcoin / BTC"}]


async def test_add_wallet_with_everything_tracked_shows_no_wallets_available(hass):
    entry = _mock_entry(
        tracked_wallets=["uuid-btc"], asset_cache={"uuid-btc": _btc()}
    )
    entry.add_to_hass(hass)
    _store_with_holdings(
        hass, entry,
        {"uuid-btc": Holding(asset_id="uuid-btc", balance=1.0, available=1.0,
                             staked=0.0, value=100.0)},
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_wallet"}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_wallet"
    assert result["errors"]["base"] == "no_wallets_available"


async def test_add_wallet_falls_back_to_one_portfolio_call_when_entry_not_loaded(
    hass,
):
    """No hass.data[DOMAIN] store for this entry at all -- the entry is not
    (or not yet) loaded -- so the holdings must come from one direct
    /portfolio call instead of a running coordinator.
    """
    entry = _mock_entry()

    mock_portfolio = AsyncMock(
        return_value=[
            {
                "asset_id": "uuid-btc",
                "balance": {"value": "1.0"},
                "available_balance": {"value": "1.0"},
                "currency_balance": {"value": "100.0"},
            }
        ]
    )
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_get_portfolio",
        mock_portfolio,
    ), patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_get_assets",
        AsyncMock(return_value=[_btc()]),
    ):
        result = await _open_menu_step(hass, entry, "add_wallet")

    mock_portfolio.assert_called_once()
    options = _select_options(result["data_schema"], "wallets")
    assert options == [{"value": "uuid-btc", "label": "Bitcoin / BTC"}]


async def test_add_wallet_rate_limit_maps_to_rate_limited(hass):
    entry = _mock_entry()
    with patch(
        "custom_components.bitpanda.config_flow.BitpandaApiClient.async_get_portfolio",
        AsyncMock(side_effect=BitpandaRateLimitError("slow down")),
    ):
        result = await _open_menu_step(hass, entry, "add_wallet")

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_wallet"
    assert result["errors"]["base"] == "rate_limited"


# --- No leftover free-text surface -------------------------------------------


def _all_keys(obj) -> set:
    keys: set = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    return keys


def test_no_leftover_symbol_pick_or_unknown_symbol_naming():
    """Step 3b removed the free-text symbol field entirely -- nothing named
    "symbol", "pick" or "unknown_symbol" (the old error code) should remain
    in any of the three UI string files (task-23-brief.md, Step 6).
    """
    forbidden = {"symbol", "pick", "unknown_symbol"}
    for filename in ("strings.json", "translations/en.json", "translations/de.json"):
        data = json.loads((_INTEGRATION_DIR / filename).read_text(encoding="utf-8"))
        found = _all_keys(data) & forbidden
        assert not found, f"{filename} still has forbidden key(s): {found}"


def test_options_flow_handler_has_no_symbol_step():
    from custom_components.bitpanda.config_flow import BitpandaOptionsFlowHandler

    assert not hasattr(BitpandaOptionsFlowHandler, "async_step_symbol")


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
