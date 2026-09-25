"""Tests for the config flow: service menu, both setups, reauth, reconfigure,
import and the Price Tracker options."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.const import API_KEY_URL, DOMAIN

from tests.conftest import load_fixture

_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_USD_ID = "b88b8879-efe3-11eb-b56f-0691764446a7"
_CLIENT = "custom_components.bitpanda.config_flow.BitpandaApiClient."
_FLOW = data_entry_flow.FlowResultType


@pytest.fixture(autouse=True)
def _no_entry_setup():
    """A created entry is set up by Home Assistant; that is not under test here."""
    with patch("custom_components.bitpanda.async_setup_entry", return_value=True):
        yield


def _portfolio_entry(**data) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="portfolio",
        title="Bitpanda Portfolio",
        data={
            "entry_type": "portfolio",
            "api_key": "key",
            "currency": "EUR",
            "currency_id": _EUR_ID,
            **data,
        },
    )


def _price_tracker_entry(extra=None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="price_tracker",
        title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": extra or []},
    )


def _selector_config(schema, key: str) -> dict:
    for marker, validator in schema.schema.items():
        if marker == key:
            return validator.config
    raise KeyError(key)


def _asset(symbol: str, type_: str | None = None) -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == symbol and (type_ is None or a["type"] == type_)
    )


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def _portfolio_form(hass):
    result = await _start(hass)
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "portfolio"}
    )


async def _submit_key(hass, result, key: str, *, missing=(), currencies=None):
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=list(missing))), patch(
        f"{_CLIENT}async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json") if currencies is None else currencies),
    ):
        return await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": key}
        )


# --- Service menu -------------------------------------------------------------


async def test_menu_offers_both_services_on_a_fresh_install(hass):
    result = await _start(hass)
    assert result["type"] == _FLOW.MENU
    assert result["menu_options"] == ["portfolio", "price_tracker"]


async def test_menu_offers_only_the_service_not_yet_set_up(hass):
    _portfolio_entry().add_to_hass(hass)
    result = await _start(hass)
    assert result["menu_options"] == ["price_tracker"]


async def test_a_version_1_entry_counts_as_the_portfolio(hass):
    MockConfigEntry(domain=DOMAIN, version=1, data={"api_key": "k", "currency": "EUR"}).add_to_hass(hass)
    result = await _start(hass)
    assert result["menu_options"] == ["price_tracker"]


async def test_menu_aborts_when_both_services_exist(hass):
    _portfolio_entry().add_to_hass(hass)
    _price_tracker_entry().add_to_hass(hass)
    result = await _start(hass)
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "all_configured"


async def test_a_second_portfolio_aborts_even_from_an_open_dialog(hass):
    """A dialog left open while another one finished: the fixed unique_id,
    re-checked on the last step, stops the second entry."""
    result = await _submit_key(hass, await _portfolio_form(hass), "good")
    assert result["step_id"] == "currency"
    _portfolio_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"currency": "eur"})
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "already_configured"


# --- Portfolio setup --------------------------------------------------------------


async def test_portfolio_form_links_the_key_page(hass):
    result = await _portfolio_form(hass)
    assert result["step_id"] == "portfolio"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL


async def test_portfolio_rejects_a_key_with_no_scope(hass):
    result = await _submit_key(
        hass, await _portfolio_form(hass), "bad", missing=("balance", "transaction", "earn")
    )
    assert result["errors"]["base"] == "invalid_auth"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL


async def test_portfolio_names_missing_scopes(hass):
    result = await _submit_key(
        hass, await _portfolio_form(hass), "partial", missing=("transaction", "earn")
    )
    assert result["errors"]["base"] == "missing_scopes"
    assert (
        result["description_placeholders"]["missing_scopes"]
        == "Transaktion (Transaction), Earn (Read)"
    )


async def test_portfolio_maps_a_rate_limit(hass):
    result = await _portfolio_form(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(side_effect=BitpandaRateLimitError("x"))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "k"})
    assert result["errors"]["base"] == "rate_limited"


async def test_portfolio_maps_a_currency_listing_failure(hass):
    result = await _portfolio_form(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_currencies", AsyncMock(side_effect=BitpandaApiError("Timeout"))
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "k"})
    assert result["errors"]["base"] == "cannot_connect"


async def test_portfolio_unexpected_error_is_logged_by_type_only(hass, caplog):
    result = await _portfolio_form(hass)
    with patch(
        f"{_CLIENT}async_missing_scopes",
        AsyncMock(side_effect=RuntimeError("detail with totally-secret-key")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "totally-secret-key"}
        )
    assert result["errors"]["base"] == "unknown"
    records = [r for r in caplog.records if r.name == "custom_components.bitpanda.config_flow"]
    assert any("RuntimeError" in r.getMessage() for r in records)
    assert all(r.exc_info is None for r in records)
    assert "totally-secret-key" not in caplog.text


async def test_portfolio_currency_step_offers_the_supported_currencies(hass):
    result = await _submit_key(hass, await _portfolio_form(hass), "good")
    assert result["step_id"] == "currency"
    config = _selector_config(result["data_schema"], "currency")
    # Lowercase: hassfest's translation-key validator rejects uppercase
    # selector option keys.
    assert config["options"] == [
        "chf", "czk", "dkk", "eur", "gbp", "huf", "nok", "pln", "ron", "sek", "try", "usd",
    ]
    assert config["translation_key"] == "currency"


async def test_portfolio_creates_the_entry(hass):
    result = await _submit_key(hass, await _portfolio_form(hass), "  good  \n")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"currency": "usd"})
    assert result["type"] == _FLOW.CREATE_ENTRY
    entry = result["result"]
    assert entry.title == "Bitpanda Portfolio"
    assert entry.unique_id == "portfolio"
    assert entry.version == 3
    assert dict(entry.data) == {
        "entry_type": "portfolio",
        "api_key": "good",
        "currency": "USD",
        "currency_id": _USD_ID,
    }
    assert "good" not in entry.title


# --- Price Tracker setup ------------------------------------------------------------


async def test_price_tracker_form_offers_the_extra_currencies(hass):
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "price_tracker"}
    )
    assert result["step_id"] == "price_tracker"
    config = _selector_config(result["data_schema"], "extra_currencies")
    # Lowercase: hassfest's translation-key validator rejects uppercase
    # selector option keys.
    assert "eur" not in config["options"]
    assert len(config["options"]) == 11
    assert config["multiple"] is True
    assert config["translation_key"] == "currency"


async def test_price_tracker_creates_a_keyless_entry(hass):
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "price_tracker"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"extra_currencies": ["usd", "chf"]}
    )
    entry = result["result"]
    assert entry.title == "Bitpanda Price Tracker"
    assert entry.unique_id == "price_tracker"
    assert dict(entry.data) == {"entry_type": "price_tracker"}
    # Stored in a fixed order, whatever order they were picked in.
    assert dict(entry.options) == {"extra_currencies": ["CHF", "USD"]}


# --- Import (used by the version 1 migration) --------------------------------------


async def test_import_creates_the_price_tracker_with_one_group_per_asset_type(hass):
    btc, sol, gold = _asset("BTC"), _asset("SOL"), _asset("XAU", "commodity")
    adopt = {"source_entry_id": "v1", "entities": []}
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={"assets": [btc, gold, sol], "extra_currencies": ["USD"], "legacy_adopt": adopt},
    )
    assert result["type"] == _FLOW.CREATE_ENTRY
    entry = result["result"]
    assert entry.unique_id == "price_tracker"
    assert entry.data["legacy_adopt"] == adopt
    assert dict(entry.options) == {"extra_currencies": ["USD"]}
    groups = {s.unique_id: s for s in entry.subentries.values()}
    assert set(groups) == {"crypto", "metal"}
    assert {s.subentry_type for s in groups.values()} == {"price_group"}
    assert groups["crypto"].title == "Cryptocurrencies"
    assert groups["metal"].title == "Precious metals"
    assert dict(groups["crypto"].data) == {
        "category": "crypto",
        "assets": {btc["id"]: slim_asset(btc), sol["id"]: slim_asset(sol)},
    }
    assert dict(groups["metal"].data) == {
        "category": "metal",
        "assets": {gold["id"]: slim_asset(gold)},
    }


async def test_imported_groups_are_titled_in_the_language_home_assistant_runs_in(hass):
    hass.config.language = "de"
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={"assets": [_asset("BTC"), _asset("BCI5")]},
    )
    titles = {s.unique_id: s.title for s in result["result"].subentries.values()}
    assert titles == {"crypto": "Kryptowährungen", "index": "Krypto-Indizes"}


async def test_import_aborts_when_a_price_tracker_exists(hass):
    _price_tracker_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={"assets": []}
    )
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "already_configured"


# --- Reauth (Portfolio) ------------------------------------------------------------
#
# A loaded entry's update listener reloads it on any data change; an entry
# whose setup failed (the typical reauth case) has none, and then the flow's
# own explicit reload is the only one. Both paths are observed, not run.


async def test_reauth_form_links_the_key_page(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL


async def test_reauth_missing_scopes_keeps_the_stored_key_and_leaks_nothing(hass, caplog):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    secret = "totally-secret-reauth-key"
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=["earn"])):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": secret})
    assert result["errors"]["base"] == "missing_scopes"
    assert result["description_placeholders"]["missing_scopes"] == "Earn (Read)"
    assert entry.data["api_key"] == "key"
    assert secret not in repr(result["description_placeholders"])
    assert secret not in caplog.text


async def test_reauth_with_a_listener_lets_the_listener_reload(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    listener = AsyncMock()
    entry.add_update_listener(listener)
    result = await entry.start_reauth_flow(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as reload:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": " new \n"})
        await hass.async_block_till_done()
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "new"
    listener.assert_called_once()
    reload.assert_not_called()


async def test_reauth_with_the_same_key_and_a_listener_reloads_once(hass):
    """Re-entering the stored key changes nothing, so the update listener
    never fires -- yet a coordinator stopped by a 401 does not restart by
    itself. The flow reloads explicitly, once."""
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    listener = AsyncMock()
    entry.add_update_listener(listener)
    result = await entry.start_reauth_flow(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as reload:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": " key \n"})
        await hass.async_block_till_done()
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "key"
    reload.assert_called_once_with(entry.entry_id)
    listener.assert_not_called()


async def test_reauth_without_a_listener_schedules_one_reload(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as reload:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "new"})
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "new"
    assert entry.data["currency"] == "EUR"
    reload.assert_called_once()


async def test_reauth_unexpected_error_shows_unknown(hass, caplog):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(side_effect=RuntimeError("secret-x"))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "secret-x"})
    assert result["errors"]["base"] == "unknown"
    assert "secret-x" not in caplog.text


# --- Reconfigure: key and currency ----------------------------------------------------
#
# The currency selector travels lowercase (hassfest's translation-key
# validator rejects uppercase option keys), so every submitted currency here
# is lowercase; stored data and the confirm step's placeholders stay
# uppercase, like everywhere else in this flow.

_PURGE = "custom_components.bitpanda.config_flow.async_purge_portfolio"


async def _reconfigure(hass, entry, user_input, *, missing=()):
    result = await entry.start_reconfigure_flow(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=list(missing))), patch(
        f"{_CLIENT}async_get_currencies", AsyncMock(return_value=load_fixture("currencies.json"))
    ):
        return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_reconfigure_form_prefills_the_currency_but_never_the_key(hass):
    entry = _portfolio_entry(api_key="stored-secret-key", currency="USD", currency_id=_USD_ID)
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    defaults = result["data_schema"]({})
    assert defaults["currency"] == "usd"
    assert "api_key" not in defaults
    assert "stored-secret-key" not in repr(result)


async def test_reconfigure_missing_scopes_reshows_form_without_leaking_key(hass, caplog):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    secret = "totally-secret-reconfigure-key"
    result = await _reconfigure(
        hass, entry, {"api_key": secret, "currency": "eur"}, missing=("earn",)
    )
    assert result["step_id"] == "reconfigure"
    assert result["errors"]["base"] == "missing_scopes"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL
    assert result["description_placeholders"]["missing_scopes"] == "Earn (Read)"
    assert entry.data["api_key"] == "key"
    assert secret not in repr(result["description_placeholders"])
    assert secret not in caplog.text


async def test_reconfigure_unexpected_error_shows_unknown(hass, caplog):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    secret = "totally-secret-key"
    result = await entry.start_reconfigure_flow(hass)
    with patch(
        f"{_CLIENT}async_missing_scopes",
        AsyncMock(side_effect=RuntimeError(f"detail with {secret}")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": secret, "currency": "eur"}
        )
    assert result["errors"]["base"] == "unknown"
    records = [r for r in caplog.records if r.name == "custom_components.bitpanda.config_flow"]
    assert any("RuntimeError" in r.getMessage() for r in records)
    assert all(r.exc_info is None for r in records)
    assert secret not in caplog.text
    assert entry.data["api_key"] == "key"


async def test_reconfigure_with_nothing_changed_aborts(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await _reconfigure(hass, entry, {"currency": "eur"})
    assert result["reason"] == "no_changes"
    assert entry.data["api_key"] == "key"


async def test_reconfigure_key_only_keeps_the_currency(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload") as reload:
        result = await _reconfigure(hass, entry, {"api_key": " new \n", "currency": "eur"})
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["api_key"] == "new"
    assert entry.data["currency"] == "EUR"
    reload.assert_called_once()


async def test_reconfigure_key_only_with_a_listener_lets_the_listener_reload(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    listener = AsyncMock()
    entry.add_update_listener(listener)
    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload") as reload:
        result = await _reconfigure(hass, entry, {"api_key": " new \n", "currency": "eur"})
        await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["api_key"] == "new"
    listener.assert_called_once()
    reload.assert_not_called()


async def test_reconfigure_with_the_same_key_and_a_listener_reloads_once(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    listener = AsyncMock()
    entry.add_update_listener(listener)
    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload") as reload:
        result = await _reconfigure(hass, entry, {"api_key": "key", "currency": "eur"})
        await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["api_key"] == "key"
    reload.assert_called_once_with(entry.entry_id)
    listener.assert_not_called()


async def test_reconfigure_bad_key_stays_on_the_form_with_the_currency_kept(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await _reconfigure(
        hass, entry, {"api_key": "partial", "currency": "usd"}, missing=("earn",)
    )
    assert result["step_id"] == "reconfigure"
    assert result["errors"]["base"] == "missing_scopes"
    assert result["data_schema"]({})["currency"] == "usd"
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL


async def test_currency_change_asks_for_confirmation_first(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    with patch(_PURGE, AsyncMock()) as purge:
        result = await _reconfigure(hass, entry, {"currency": "usd"})
    assert result["step_id"] == "confirm_currency"
    assert result["description_placeholders"] == {"old": "EUR", "new": "USD"}
    purge.assert_not_called()
    assert entry.data["currency"] == "EUR"


async def test_confirmed_currency_change_purges_then_stores_and_reloads(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    with patch(_PURGE, AsyncMock()) as purge, patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as reload:
        result = await _reconfigure(hass, entry, {"api_key": "new", "currency": "usd"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["reason"] == "currency_changed"
    purge.assert_awaited_once_with(hass, entry)
    reload.assert_called_once()
    assert entry.data["currency"] == "USD"
    assert entry.data["currency_id"] == _USD_ID
    assert entry.data["api_key"] == "new"


async def test_confirmed_currency_change_without_a_new_key_keeps_the_old_one(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    with patch(_PURGE, AsyncMock()), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ):
        result = await _reconfigure(hass, entry, {"currency": "chf"})
        await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert entry.data["api_key"] == "key"
    assert entry.data["currency"] == "CHF"


async def test_currency_listing_failure_maps_to_cannot_connect(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    with patch(f"{_CLIENT}async_get_currencies", AsyncMock(side_effect=BitpandaApiError("x"))):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"currency": "usd"})
    assert result["errors"]["base"] == "cannot_connect"


async def test_the_price_tracker_has_nothing_to_reconfigure(hass):
    entry = _price_tracker_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "no_reconfigure"


# --- Options (Price Tracker only) ----------------------------------------------------------


async def test_only_the_price_tracker_has_options(hass):
    from custom_components.bitpanda.config_flow import BitpandaConfigFlow

    assert BitpandaConfigFlow.async_supports_options_flow(_price_tracker_entry())
    assert not BitpandaConfigFlow.async_supports_options_flow(_portfolio_entry())


async def test_options_change_the_extra_currencies(hass):
    entry = _price_tracker_entry(extra=["USD"])
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = result["data_schema"]
    # The default travels lowercase (hassfest); the stored option stays USD.
    assert schema({})["extra_currencies"] == ["usd"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"extra_currencies": ["gbp", "chf"]}
    )
    assert result["type"] == _FLOW.CREATE_ENTRY
    assert dict(entry.options) == {"extra_currencies": ["CHF", "GBP"]}


async def test_stored_currency_round_trips_through_the_options_form(hass):
    """Created lowercase (the selector's own shape), stored upper, and shown
    lowercase again the next time the options form renders -- the same
    conversion the Portfolio's currency step relies on, exercised here for
    the Price Tracker's own currency selector.
    """
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "price_tracker"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"extra_currencies": ["usd"]}
    )
    entry = result["result"]
    assert dict(entry.options) == {"extra_currencies": ["USD"]}

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"]({})["extra_currencies"] == ["usd"]
