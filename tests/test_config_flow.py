"""Tests for the config flow: service menu, both setups, reauth, reconfigure,
import and the options of both services."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.data_entry_flow import section
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.const import API_KEY_URL, DOMAIN, TROUBLESHOOTING_URL
from custom_components.bitpanda.purge import OldStatistics

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


def _setup_language(language: str) -> dict:
    """What the language section of a setup form sends."""
    return {"language": {"language": language}}


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
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"currency": {"currency": "eur"}, **_setup_language("en")}
    )
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "already_configured"


# --- Portfolio setup --------------------------------------------------------------


async def _finish_portfolio_setup(hass, result) -> None:
    """Go on from the key form `result` -- shown again with an error --
    with a valid key and a currency, to the new entry: every error of the
    dialog leaves a way to finish it."""
    assert (result["type"], result["step_id"]) == (_FLOW.FORM, "portfolio")
    result = await _submit_key(hass, result, "good")
    assert result["step_id"] == "currency"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"currency": {"currency": "eur"}, **_setup_language("en")}
    )
    assert result["type"] == _FLOW.CREATE_ENTRY
    assert (result["result"].data["api_key"], result["result"].data["currency"]) == (
        "good", "EUR"
    )


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
    await _finish_portfolio_setup(hass, result)


async def test_portfolio_names_missing_scopes(hass):
    """The error marks each permission -- ✓ for one the key has, ✗ for one
    it lacks; the permissions' names stay in the translated texts."""
    result = await _submit_key(
        hass, await _portfolio_form(hass), "partial", missing=("transaction", "earn")
    )
    assert result["errors"]["base"] == "missing_scopes"
    placeholders = result["description_placeholders"]
    assert {scope: placeholders[scope] for scope in ("balance", "transaction", "earn")} == {
        "balance": "✓", "transaction": "✗", "earn": "✗"
    }
    assert "missing_scopes" not in placeholders
    await _finish_portfolio_setup(hass, result)


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (BitpandaRateLimitError("Rate limited on /portfolio"), "rate_limited"),
        (BitpandaApiError("Timeout for /portfolio"), "cannot_connect"),
    ],
    ids=["rate_limited", "cannot_connect"],
)
async def test_portfolio_maps_a_failed_key_check(hass, failure, error):
    result = await _portfolio_form(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(side_effect=failure)):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "k"})
    assert result["errors"]["base"] == error
    await _finish_portfolio_setup(hass, result)


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (BitpandaRateLimitError("Rate limited on /currencies"), "rate_limited"),
        (BitpandaApiError("Timeout for /currencies"), "cannot_connect"),
    ],
    ids=["rate_limited", "cannot_connect"],
)
async def test_portfolio_maps_a_currency_listing_failure(hass, failure, error):
    result = await _portfolio_form(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_currencies", AsyncMock(side_effect=failure)
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "k"})
    assert result["errors"]["base"] == error
    await _finish_portfolio_setup(hass, result)


@pytest.mark.parametrize(
    "currencies", [[], [{"symbol": "JPY", "id": "jpy-id"}]], ids=["empty", "unsupported"]
)
async def test_portfolio_without_a_supported_currency_cannot_connect(hass, currencies):
    """Nothing to choose from: Bitpanda's answer is broken."""
    result = await _submit_key(hass, await _portfolio_form(hass), "good", currencies=currencies)
    assert result["step_id"] == "portfolio"
    assert result["errors"]["base"] == "cannot_connect"
    await _finish_portfolio_setup(hass, result)


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
    await _finish_portfolio_setup(hass, result)


async def test_portfolio_currency_step_offers_the_supported_currencies(hass):
    result = await _submit_key(hass, await _portfolio_form(hass), "good")
    assert result["step_id"] == "currency"
    config = _selector_config(_section_schema(result["data_schema"], "currency"), "currency")
    # Lowercase: hassfest's translation-key validator rejects uppercase
    # selector option keys.
    assert config["options"] == [
        "chf", "czk", "dkk", "eur", "gbp", "huf", "nok", "pln", "ron", "sek", "try", "usd",
    ]
    assert config["translation_key"] == "currency"


async def test_the_currency_step_offers_only_the_currencies_bitpanda_lists(hass):
    """A supported currency that /currencies does not list has no id to
    store, so the step does not offer it, and the form refuses it."""
    listed = [c for c in load_fixture("currencies.json") if c["symbol"] != "HUF"]
    result = await _submit_key(hass, await _portfolio_form(hass), "good", currencies=listed)
    config = _selector_config(_section_schema(result["data_schema"], "currency"), "currency")
    assert "huf" not in config["options"] and len(config["options"]) == 11
    with pytest.raises(data_entry_flow.InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"currency": {"currency": "huf"}, **_setup_language("en")}
        )


async def test_portfolio_creates_the_entry(hass):
    result = await _submit_key(hass, await _portfolio_form(hass), "  good  \n")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"currency": {"currency": "usd"}, **_setup_language("it")}
    )
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
    # Flat, as Configure stores it.
    assert dict(entry.options) == {"language": "it"}
    assert "good" not in entry.title


# --- Old statistics at setup ---------------------------------------------------------

_FIND = "custom_components.bitpanda.config_flow.async_find_old_statistics"
_PURGE_RECORDED = "custom_components.bitpanda.config_flow.async_purge_recorded"
_FOUND = OldStatistics(
    entity_ids=["sensor.bitpanda_portfolio_cash", "sensor.bitpanda_vision_vsn_wallet_available"],
    currencies=["CHF", "EUR"],
)


async def _submit_currency(hass, found: OldStatistics):
    """The Portfolio's setup, with a valid key, up to what follows the
    currency step: USD chosen, `found` what the detection reports."""
    result = await _submit_key(hass, await _portfolio_form(hass), "good")
    with patch(_FIND, AsyncMock(return_value=found)) as find:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"currency": {"currency": "usd"}, **_setup_language("en")}
        )
    return result, find


def _assert_portfolio_created(result) -> None:
    assert result["type"] == _FLOW.CREATE_ENTRY
    assert dict(result["result"].data) == {
        "entry_type": "portfolio", "api_key": "good", "currency": "USD", "currency_id": _USD_ID,
    }
    assert dict(result["result"].options) == {"language": "en"}


async def test_the_setup_looks_for_old_statistics_in_the_chosen_currency(hass):
    result, find = await _submit_currency(hass, OldStatistics(entity_ids=[], currencies=[]))
    find.assert_awaited_once_with(hass, "USD")
    _assert_portfolio_created(result)


async def test_old_statistics_in_another_currency_are_asked_about_first(hass):
    result, _ = await _submit_currency(hass, _FOUND)
    assert (result["type"], result["step_id"]) == (_FLOW.MENU, "old_statistics")
    assert result["menu_options"] == ["delete_statistics", "keep_statistics", "cancel_setup"]
    assert result["description_placeholders"] == {
        "old": "CHF, EUR", "new": "USD", "troubleshooting_url": TROUBLESHOOTING_URL,
    }
    assert hass.config_entries.async_entries(DOMAIN) == []


def test_the_troubleshooting_link_leads_to_the_readmes_troubleshooting_section():
    """The anchor GitHub gives the heading "🔧 Troubleshooting": the emoji
    dropped, the space after it kept as a dash. The issue templates'
    config.yml links the same section."""
    readme = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
    assert "\n## \U0001f527 Troubleshooting\n" in readme
    assert TROUBLESHOOTING_URL == "https://github.com/Spegeli/hacs_bitpanda#-troubleshooting"


async def test_delete_and_set_up_deletes_first_then_creates_the_entry(hass):
    result, _ = await _submit_currency(hass, _FOUND)
    entries_while_deleting: list = []
    purge = AsyncMock(
        side_effect=lambda hass_, ids: entries_while_deleting.append(
            hass_.config_entries.async_entries(DOMAIN)
        )
    )
    with patch(_PURGE_RECORDED, purge):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "delete_statistics"}
        )
    purge.assert_awaited_once_with(hass, _FOUND.entity_ids)
    assert entries_while_deleting == [[]]
    _assert_portfolio_created(result)


async def test_keep_and_set_up_creates_the_entry_and_deletes_nothing(hass):
    result, _ = await _submit_currency(hass, _FOUND)
    with patch(_PURGE_RECORDED, AsyncMock()) as purge:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "keep_statistics"}
        )
    purge.assert_not_awaited()
    _assert_portfolio_created(result)


async def test_cancel_sets_up_and_deletes_nothing(hass):
    result, _ = await _submit_currency(hass, _FOUND)
    with patch(_PURGE_RECORDED, AsyncMock()) as purge:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "cancel_setup"}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "setup_cancelled")
    purge.assert_not_awaited()
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_closing_the_question_creates_and_deletes_nothing(hass):
    result, _ = await _submit_currency(hass, _FOUND)
    with patch(_PURGE_RECORDED, AsyncMock()) as purge:
        hass.config_entries.flow.async_abort(result["flow_id"])
        await hass.async_block_till_done()
    purge.assert_not_awaited()
    assert hass.config_entries.async_entries(DOMAIN) == []


@pytest.mark.parametrize("choice", ["delete_statistics", "keep_statistics"])
async def test_a_portfolio_set_up_meanwhile_stops_either_choice(hass, choice):
    """Home Assistant already stops a second dialog at its key step. Should a
    Portfolio exist all the same, deleting now would hit what it records
    under the same IDs: the check comes before anything is deleted."""
    result, _ = await _submit_currency(hass, _FOUND)
    _portfolio_entry().add_to_hass(hass)
    with patch(_PURGE_RECORDED, AsyncMock()) as purge:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": choice}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "already_configured")
    purge.assert_not_awaited()


# --- Price Tracker setup ------------------------------------------------------------


async def test_price_tracker_form_offers_the_extra_currencies(hass):
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "price_tracker"}
    )
    assert result["step_id"] == "price_tracker"
    config = _selector_config(_section_schema(result["data_schema"], "currencies"), "extra_currencies")
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
        result["flow_id"],
        {"currencies": {"extra_currencies": ["usd", "chf"]}, **_setup_language("nl")},
    )
    entry = result["result"]
    assert entry.title == "Bitpanda Price Tracker"
    assert entry.unique_id == "price_tracker"
    assert dict(entry.data) == {"entry_type": "price_tracker"}
    # The currencies in a fixed order, whatever order they were picked in;
    # both flat, as Configure stores them.
    assert dict(entry.options) == {"extra_currencies": ["CHF", "USD"], "language": "nl"}


async def test_a_second_price_tracker_aborts_even_from_an_open_dialog(hass):
    """As for the Portfolio: the fixed unique_id is checked again when the
    form is submitted."""
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "price_tracker"}
    )
    assert result["step_id"] == "price_tracker"
    _price_tracker_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"currencies": {"extra_currencies": []}, **_setup_language("en")}
    )
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "already_configured"


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


async def test_imported_groups_are_english_whatever_language_home_assistant_runs_in(hass):
    """The imported Price Tracker has no language option yet: English, the
    default (language.py)."""
    hass.config.language = "de"
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={"assets": [_asset("BTC"), _asset("BCI5")]},
    )
    titles = {s.unique_id: s.title for s in result["result"].subentries.values()}
    assert titles == {"crypto": "Cryptocurrencies", "index": "Crypto indices"}
    assert "language" not in result["result"].options


@pytest.mark.parametrize("extra", [{}, {"legacy_adopt": {}}], ids=["absent", "empty"])
async def test_an_import_without_legacy_entities_stores_no_adoption_list(hass, extra):
    """Nothing for the new entry to adopt, so nothing is stored."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={"assets": [_asset("BTC")], **extra},
    )
    assert dict(result["result"].data) == {"entry_type": "price_tracker"}


async def test_an_import_keeps_only_the_supported_extra_currencies(hass):
    """EUR is always there, not an extra; an unknown code is dropped; the
    rest is stored upper case in the fixed order."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data={"assets": [_asset("BTC")], "extra_currencies": ["USD", "EUR", "JPY", "chf"]},
    )
    assert dict(result["result"].options) == {"extra_currencies": ["CHF", "USD"]}


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


async def _finish_reauth(hass, entry, result) -> None:
    """Go on from the reauth form `result` -- shown again with an error --
    with a valid key, to the end: the key is replaced."""
    assert (result["type"], result["step_id"]) == (_FLOW.FORM, "reauth_confirm")
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "fresh"}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "reauth_successful")
    assert entry.data["api_key"] == "fresh"


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
    placeholders = result["description_placeholders"]
    assert {scope: placeholders[scope] for scope in ("balance", "transaction", "earn")} == {
        "balance": "✓", "transaction": "✓", "earn": "✗"
    }
    assert entry.data["api_key"] == "key"
    assert secret not in repr(result["description_placeholders"])
    assert secret not in caplog.text
    await _finish_reauth(hass, entry, result)


@pytest.mark.parametrize(
    ("check", "error"),
    [
        (AsyncMock(return_value=["balance", "transaction", "earn"]), "invalid_auth"),
        (AsyncMock(side_effect=BitpandaRateLimitError("Rate limited on /portfolio")), "rate_limited"),
        (AsyncMock(side_effect=BitpandaApiError("Timeout for /portfolio")), "cannot_connect"),
    ],
    ids=["invalid_auth", "rate_limited", "cannot_connect"],
)
async def test_reauth_shows_a_failed_key_check_and_keeps_the_stored_key(hass, check, error):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    with patch(f"{_CLIENT}async_missing_scopes", check):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "k"})
    assert result["errors"]["base"] == error
    assert result["description_placeholders"]["api_key_url"] == API_KEY_URL
    assert entry.data["api_key"] == "key"
    await _finish_reauth(hass, entry, result)


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
    await _finish_reauth(hass, entry, result)


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


async def _finish_reconfigure_with_a_new_key(hass, entry, result) -> None:
    """Go on from the Reconfigure form `result` -- shown again with an
    error -- with a valid key and the stored currency, to the end: the key
    is replaced."""
    assert (result["type"], result["step_id"]) == (_FLOW.FORM, "reconfigure")
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "fresh", "currency": "eur"}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "reconfigure_successful")
    assert (entry.data["api_key"], entry.data["currency"]) == ("fresh", "EUR")


async def _finish_currency_change(hass, entry, result, user_input) -> None:
    """Go on from the Reconfigure form `result` -- shown again with an
    error -- with `user_input`, which changes the currency to USD and now
    works, through the confirmation to the end."""
    assert (result["type"], result["step_id"]) == (_FLOW.FORM, "reconfigure")
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_currencies", AsyncMock(return_value=load_fixture("currencies.json"))
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    assert result["step_id"] == "confirm_currency"
    change = "change_key_and_currency" if user_input.get("api_key") else "change_currency"
    with patch(_PURGE, AsyncMock(return_value=True)), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": change}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "currency_changed")
    assert (entry.data["currency"], entry.data["currency_id"]) == ("USD", _USD_ID)


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
    placeholders = result["description_placeholders"]
    assert {scope: placeholders[scope] for scope in ("balance", "transaction", "earn")} == {
        "balance": "✓", "transaction": "✓", "earn": "✗"
    }
    assert entry.data["api_key"] == "key"
    assert secret not in repr(result["description_placeholders"])
    assert secret not in caplog.text
    await _finish_reconfigure_with_a_new_key(hass, entry, result)


@pytest.mark.parametrize(
    ("check", "error"),
    [
        (AsyncMock(return_value=["balance", "transaction", "earn"]), "invalid_auth"),
        (AsyncMock(side_effect=BitpandaRateLimitError("Rate limited on /portfolio")), "rate_limited"),
        (AsyncMock(side_effect=BitpandaApiError("Timeout for /portfolio")), "cannot_connect"),
    ],
    ids=["invalid_auth", "rate_limited", "cannot_connect"],
)
async def test_reconfigure_shows_a_failed_key_check_and_keeps_the_stored_key(hass, check, error):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    with patch(f"{_CLIENT}async_missing_scopes", check):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "k", "currency": "eur"}
        )
    assert result["errors"]["base"] == error
    assert entry.data["api_key"] == "key"
    await _finish_reconfigure_with_a_new_key(hass, entry, result)


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
    await _finish_reconfigure_with_a_new_key(hass, entry, result)


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
    await _finish_currency_change(hass, entry, result, {"api_key": "good", "currency": "usd"})
    assert entry.data["api_key"] == "good"


async def test_currency_change_asks_for_confirmation_first(hass):
    """Without a new API key the choice is to change the currency or not."""
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    with patch(_PURGE, AsyncMock()) as purge:
        result = await _reconfigure(hass, entry, {"currency": "usd"})
    assert (result["type"], result["step_id"]) == (_FLOW.MENU, "confirm_currency")
    assert result["menu_options"] == ["change_currency", "cancel_currency_change"]
    assert result["description_placeholders"] == {"old": "EUR", "new": "USD"}
    purge.assert_not_called()
    assert entry.data["currency"] == "EUR"


async def test_a_currency_change_with_a_new_key_offers_to_save_only_the_key(hass):
    """A new API key entered together with another currency can be kept
    without the currency change, which would delete every Portfolio sensor."""
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await _reconfigure(hass, entry, {"api_key": "new", "currency": "usd"})
    assert (result["type"], result["step_id"]) == (_FLOW.MENU, "confirm_currency")
    assert result["menu_options"] == [
        "change_key_and_currency", "save_key_only", "cancel_currency_change"
    ]


async def test_saving_only_the_new_key_keeps_the_currency_and_deletes_nothing(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    with patch(_PURGE, AsyncMock()) as purge, patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as reload:
        result = await _reconfigure(hass, entry, {"api_key": "new", "currency": "usd"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "save_key_only"}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "reconfigure_successful")
    purge.assert_not_called()
    reload.assert_called_once()
    assert (entry.data["api_key"], entry.data["currency"]) == ("new", "EUR")


@pytest.mark.parametrize(
    "user_input", [{"currency": "usd"}, {"api_key": "new", "currency": "usd"}],
    ids=["currency_only", "with_a_new_key"],
)
async def test_cancelling_the_currency_change_changes_nothing(hass, user_input):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    before = dict(entry.data)
    with patch(_PURGE, AsyncMock()) as purge:
        result = await _reconfigure(hass, entry, user_input)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "cancel_currency_change"}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "no_changes")
    purge.assert_not_called()
    assert dict(entry.data) == before


async def test_confirmed_currency_change_purges_then_stores_and_reloads(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    with patch(_PURGE, AsyncMock(return_value=True)) as purge, patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as reload:
        result = await _reconfigure(hass, entry, {"api_key": "new", "currency": "usd"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "change_key_and_currency"}
        )
    assert result["reason"] == "currency_changed"
    purge.assert_awaited_once_with(hass, entry)
    reload.assert_called_once()
    assert entry.data["currency"] == "USD"
    assert entry.data["currency_id"] == _USD_ID
    assert entry.data["api_key"] == "new"


async def test_confirmed_currency_change_without_a_new_key_keeps_the_old_one(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    with patch(_PURGE, AsyncMock(return_value=True)), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ):
        result = await _reconfigure(hass, entry, {"currency": "chf"})
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "change_currency"}
        )
    assert entry.data["api_key"] == "key"
    assert entry.data["currency"] == "CHF"


async def test_a_currency_change_whose_unload_fails_changes_nothing(hass):
    """The purge refuses when the Portfolio cannot be unloaded first; the
    currency, the key and the entry stay as they were."""
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    before = dict(entry.data)
    with patch(_PURGE, AsyncMock(return_value=False)) as purge, patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ) as reload:
        result = await _reconfigure(hass, entry, {"api_key": "new", "currency": "usd"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "change_key_and_currency"}
        )
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "unload_failed"
    purge.assert_awaited_once_with(hass, entry)
    reload.assert_not_called()
    assert dict(entry.data) == before


@pytest.mark.parametrize(
    ("listing", "error"),
    [
        (AsyncMock(side_effect=BitpandaApiError("Timeout for /currencies")), "cannot_connect"),
        (AsyncMock(side_effect=BitpandaRateLimitError("Rate limited on /currencies")), "rate_limited"),
        (AsyncMock(return_value=[{"symbol": "EUR", "id": _EUR_ID}]), "cannot_connect"),
    ],
    ids=["cannot_connect", "rate_limited", "currency_not_listed"],
)
async def test_a_currency_change_without_the_currencys_id_changes_nothing(hass, listing, error):
    """The new currency's Bitpanda id comes from /currencies: without it --
    the listing failed, or does not name the currency -- the form says why,
    keeps the chosen currency, and nothing is stored."""
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    with patch(f"{_CLIENT}async_get_currencies", listing):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"currency": "usd"})
    assert result["step_id"] == "reconfigure"
    assert result["errors"]["base"] == error
    assert result["data_schema"]({})["currency"] == "usd"
    assert entry.data["currency"] == "EUR"
    await _finish_currency_change(hass, entry, result, {"currency": "usd"})


# The repair issue of the version 1 upgrade saying that the old currency is
# not available and the Portfolio reports in EUR; it sends the user to
# Reconfigure to choose another currency.
_SWITCH_TO_EUR = "currency_dropped"


def _raise_switch_to_eur_issue(hass) -> None:
    """The issue as the upgrade raises it (migration.py)."""
    ir.async_create_issue(
        hass, DOMAIN, _SWITCH_TO_EUR, is_fixable=False, is_persistent=True,
        severity=ir.IssueSeverity.WARNING, translation_key=_SWITCH_TO_EUR,
        translation_placeholders={"currency": "JPY"},
    )


def _switch_to_eur_issue(hass) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, _SWITCH_TO_EUR)


async def test_a_currency_change_resolves_the_switch_to_eur_issue(hass):
    """Choosing another currency is what the issue asks for: once the
    change is made, the issue goes."""
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    _raise_switch_to_eur_issue(hass)
    with patch(_PURGE, AsyncMock(return_value=True)), patch(
        "homeassistant.config_entries.ConfigEntries.async_schedule_reload"
    ):
        result = await _reconfigure(hass, entry, {"currency": "usd"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "change_currency"}
        )
    assert result["reason"] == "currency_changed"
    assert _switch_to_eur_issue(hass) is None


async def test_replacing_the_key_alone_leaves_the_switch_to_eur_issue(hass):
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    _raise_switch_to_eur_issue(hass)
    with patch("homeassistant.config_entries.ConfigEntries.async_schedule_reload"):
        result = await _reconfigure(hass, entry, {"api_key": "new", "currency": "eur"})
    assert result["reason"] == "reconfigure_successful"
    assert _switch_to_eur_issue(hass) is not None


async def test_a_currency_change_that_could_not_be_made_leaves_the_issue(hass):
    """The Portfolio could not be unloaded, so the currency stayed EUR."""
    entry = _portfolio_entry()
    entry.add_to_hass(hass)
    _raise_switch_to_eur_issue(hass)
    with patch(_PURGE, AsyncMock(return_value=False)):
        result = await _reconfigure(hass, entry, {"currency": "usd"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "change_currency"}
        )
    assert result["reason"] == "unload_failed"
    assert _switch_to_eur_issue(hass) is not None


async def test_the_price_tracker_has_nothing_to_reconfigure(hass):
    entry = _price_tracker_entry()
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "no_reconfigure"


# --- Options: Configure, both services ----------------------------------------------------
#
# Each service shows its own form under a step id of its own, so each has
# texts of its own (options.step.price_tracker / options.step.portfolio).
# Saving calls the entry's update listener, which reloads it (__init__.py;
# the reload itself is exercised in tests/test_init.py).

# Discovered from disk, the way the integration offers them
# (language.async_shipped_languages).
_LANGUAGES = sorted(
    path.stem
    for path in (
        Path(__file__).parent.parent / "custom_components" / "bitpanda" / "translations"
    ).glob("*.json")
)


def _with_options(entry: MockConfigEntry, **options) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id=entry.unique_id,
        title=entry.title,
        data=dict(entry.data),
        options={**entry.options, **options},
    )


async def _options_form(hass, entry: MockConfigEntry):
    entry.add_to_hass(hass)
    return await hass.config_entries.options.async_init(entry.entry_id)


# Both Configure forms group their fields in sections, and their input
# arrives nested by section: the Price Tracker's in two, the Portfolio's in one.
def _section_schema(schema, key: str):
    """The fields of the section `key` of a form."""
    validator = dict(schema.schema)[key]
    assert isinstance(validator, section), key
    return validator.schema


def _price_tracker_input(extra: list[str], language: str) -> dict:
    """What the Price Tracker's Configure form sends: its fields by section."""
    return {"currencies": {"extra_currencies": extra}, "language": {"language": language}}


def _portfolio_input(language: str) -> dict:
    """What the Portfolio's Configure form sends: its one section."""
    return {"language": {"language": language}}


def _form_defaults(result) -> dict:
    """What a Configure form shows before anything is touched: each
    section's defaults."""
    return result["data_schema"]({str(key): {} for key in result["data_schema"].schema})


async def test_both_services_have_options(hass):
    from custom_components.bitpanda.config_flow import BitpandaConfigFlow

    assert BitpandaConfigFlow.async_supports_options_flow(_price_tracker_entry())
    assert BitpandaConfigFlow.async_supports_options_flow(_portfolio_entry())


async def test_the_price_tracker_options_come_in_two_open_sections(hass):
    """The currencies first, then the language, each under a heading of its
    own -- a Home Assistant form has no plain divider -- and both open."""
    result = await _options_form(hass, _price_tracker_entry(extra=["USD"]))
    assert result["step_id"] == "price_tracker"
    schema = result["data_schema"]
    assert list(schema.schema) == ["currencies", "language"]
    assert [dict(schema.schema)[key].options for key in schema.schema] == [
        {"collapsed": False}, {"collapsed": False},
    ]
    assert list(_section_schema(schema, "currencies").schema) == ["extra_currencies"]
    assert list(_section_schema(schema, "language").schema) == ["language"]
    config = _selector_config(_section_schema(schema, "language"), "language")
    assert config["options"] == _LANGUAGES
    assert config["translation_key"] == "language"
    assert config.get("multiple", False) is False
    # The stored currencies, and English until the user picks another language.
    assert _form_defaults(result) == {
        "currencies": {"extra_currencies": ["usd"]}, "language": {"language": "en"},
    }


async def test_the_frontend_gets_the_two_sections_open_and_filled_in(hass, hass_client):
    """What the Configure dialog receives, through Home Assistant's own
    options-flow API: two expandable sections, expanded, each with its
    field and the stored value as its default."""
    entry = _with_options(_price_tracker_entry(extra=["USD"]), language="de")
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()
    response = await client.post(
        "/api/config/config_entries/options/flow", json={"handler": entry.entry_id}
    )
    shown = await response.json()
    assert shown["step_id"] == "price_tracker"
    assert [
        (field["name"], field["type"], field["expanded"]) for field in shown["data_schema"]
    ] == [("currencies", "expandable", True), ("language", "expandable", True)]
    assert [
        [(inner["name"], inner["default"]) for inner in field["schema"]]
        for field in shown["data_schema"]
    ] == [[("extra_currencies", ["usd"])], [("language", "de")]]


async def test_the_price_tracker_options_step_has_no_text_above_its_sections(hass):
    """Its two headed sections say it all: no step description renders
    above them."""
    result = await _options_form(hass, _price_tracker_entry())
    assert "description" not in _STRINGS["options"]["step"][result["step_id"]]
    assert result["description_placeholders"] is None


async def test_options_change_the_extra_currencies(hass):
    """Stored flat, exactly as before the sections."""
    entry = _price_tracker_entry(extra=["USD"])
    result = await _options_form(hass, entry)
    # The default travels lowercase (hassfest); the stored option stays USD.
    assert _form_defaults(result)["currencies"]["extra_currencies"] == ["usd"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _price_tracker_input(["gbp", "chf"], "en")
    )
    assert result["type"] == _FLOW.CREATE_ENTRY
    assert dict(entry.options) == {"extra_currencies": ["CHF", "GBP"], "language": "en"}


async def test_the_price_tracker_options_keep_other_stored_options(hass):
    """Whatever else the entry's options hold stays as it is."""
    entry = _with_options(_price_tracker_entry(extra=["USD"]), language="de", other="kept")
    result = await _options_form(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _price_tracker_input([], "fr")
    )
    assert dict(entry.options) == {"extra_currencies": [], "language": "fr", "other": "kept"}


async def test_the_price_tracker_options_store_the_language_and_reload(hass):
    entry = _price_tracker_entry(extra=["USD"])
    result = await _options_form(hass, entry)
    listener = AsyncMock()
    entry.add_update_listener(listener)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _price_tracker_input(["usd"], "de")
    )
    await hass.async_block_till_done()
    assert result["type"] == _FLOW.CREATE_ENTRY
    assert dict(entry.options) == {"extra_currencies": ["USD"], "language": "de"}
    listener.assert_called_once()


async def test_the_portfolio_options_offer_the_language_in_an_open_section(hass):
    """Its only option, in a section like the Price Tracker's, so that any
    later option gets a section of its own; its key and currency change
    through Reconfigure."""
    result = await _options_form(hass, _portfolio_entry())
    assert result["step_id"] == "portfolio"
    schema = result["data_schema"]
    assert list(schema.schema) == ["language"]
    assert dict(schema.schema)["language"].options == {"collapsed": False}
    assert list(_section_schema(schema, "language").schema) == ["language"]
    config = _selector_config(_section_schema(schema, "language"), "language")
    assert config["options"] == _LANGUAGES
    assert config["translation_key"] == "language"
    assert config.get("multiple", False) is False
    assert _form_defaults(result) == {"language": {"language": "en"}}


async def test_the_frontend_gets_the_portfolio_language_open_and_filled_in(hass, hass_client):
    """Through Home Assistant's own options-flow API: one expandable
    section, expanded, with the stored language as its default."""
    entry = _with_options(_portfolio_entry(), language="de")
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()
    response = await client.post(
        "/api/config/config_entries/options/flow", json={"handler": entry.entry_id}
    )
    shown = await response.json()
    assert shown["step_id"] == "portfolio"
    [field] = shown["data_schema"]
    assert (field["name"], field["type"], field["expanded"]) == ("language", "expandable", True)
    assert [(inner["name"], inner["default"]) for inner in field["schema"]] == [("language", "de")]


async def test_the_portfolio_options_store_the_language_flat_and_reload(hass):
    """The input arrives nested in its section and is stored flat, exactly
    as before the section: an entry that chose a language keeps working,
    and whatever else its options hold stays."""
    entry = _with_options(_portfolio_entry(), language="de", other="kept")
    result = await _options_form(hass, entry)
    assert _form_defaults(result) == {"language": {"language": "de"}}
    listener = AsyncMock()
    entry.add_update_listener(listener)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _portfolio_input("fr")
    )
    await hass.async_block_till_done()
    assert result["type"] == _FLOW.CREATE_ENTRY
    assert dict(entry.options) == {"language": "fr", "other": "kept"}
    # The key and the currency stay where they are.
    assert dict(entry.data) == dict(_portfolio_entry().data)
    listener.assert_called_once()


def _shown_language(result) -> str:
    return _form_defaults(result)["language"]["language"]


def _language_input(service: str, language: str) -> dict:
    if service == "price_tracker":
        return _price_tracker_input([], language)
    return _portfolio_input(language)


@pytest.mark.parametrize("service", ["price_tracker", "portfolio"])
async def test_the_options_form_shows_the_stored_language(hass, service):
    entry = _price_tracker_entry() if service == "price_tracker" else _portfolio_entry()
    result = await _options_form(hass, _with_options(entry, language="it"))
    assert _shown_language(result) == "it"


async def test_a_stored_language_no_longer_shipped_shows_english(hass):
    """So the form can still be saved unchanged: a default outside the
    options would be refused."""
    result = await _options_form(hass, _with_options(_portfolio_entry(), language="xx"))
    assert _form_defaults(result) == {"language": {"language": "en"}}


@pytest.mark.parametrize("service", ["price_tracker", "portfolio"])
async def test_a_language_the_integration_does_not_ship_is_refused(hass, service):
    """Refused by the form itself; the same dialog then saves a shipped
    language."""
    entry = _price_tracker_entry() if service == "price_tracker" else _portfolio_entry()
    result = await _options_form(hass, entry)
    before = dict(entry.options)
    with pytest.raises(data_entry_flow.InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"], _language_input(service, "xx")
        )
    assert dict(entry.options) == before
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _language_input(service, "nl")
    )
    assert result["type"] == _FLOW.CREATE_ENTRY
    assert dict(entry.options) == {**before, "language": "nl"}


# --- Language at setup ------------------------------------------------------------------
# Both setups ask for it below the service's own field, in a section like
# Configure's, and store it flat in the new entry's options (the setup tests
# above).


async def _setup_form(hass, service: str):
    """The last setup form of `service`: the Price Tracker's only one, the
    Portfolio's currency step."""
    if service == "portfolio":
        return await _submit_key(hass, await _portfolio_form(hass), "good")
    result = await _start(hass)
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "price_tracker"}
    )


def _preselected(result) -> str:
    """The language a setup form shows before anything is touched."""
    return _section_schema(result["data_schema"], "language")({})["language"]


@pytest.mark.parametrize(
    ("service", "own_field"), [("price_tracker", "currencies"), ("portfolio", "currency")]
)
async def test_the_setup_asks_for_the_language_in_an_open_section_below(
    hass, service, own_field
):
    """Below the service's own field, under a heading of its own and open:
    every shipped language, one to pick -- the field Configure shows."""
    result = await _setup_form(hass, service)
    schema = result["data_schema"]
    assert list(schema.schema) == [own_field, "language"]
    assert dict(schema.schema)["language"].options == {"collapsed": False}
    assert list(_section_schema(schema, "language").schema) == ["language"]
    config = _selector_config(_section_schema(schema, "language"), "language")
    assert config["options"] == _LANGUAGES
    assert config["translation_key"] == "language"
    assert config.get("multiple", False) is False


async def test_the_price_tracker_setup_shows_its_currencies_as_configure_does(hass):
    """Under a heading of their own, open, in the section Configure shows
    them in -- none chosen yet."""
    schema = (await _setup_form(hass, "price_tracker"))["data_schema"]
    assert dict(schema.schema)["currencies"].options == {"collapsed": False}
    assert list(_section_schema(schema, "currencies").schema) == ["extra_currencies"]
    assert _section_schema(schema, "currencies")({}) == {"extra_currencies": []}


async def test_the_portfolio_setup_shows_its_currency_in_an_open_section(hass):
    """Like the language below it: under a heading of its own, open, with
    EUR chosen until the user picks another."""
    schema = (await _setup_form(hass, "portfolio"))["data_schema"]
    assert dict(schema.schema)["currency"].options == {"collapsed": False}
    assert list(_section_schema(schema, "currency").schema) == ["currency"]
    assert _section_schema(schema, "currency")({}) == {"currency": "eur"}


@pytest.mark.parametrize("service", ["price_tracker", "portfolio"])
@pytest.mark.parametrize(
    ("system", "shown"),
    [("de", "de"), ("en", "en"), ("en-GB", "en"), ("es-419", "es"), ("pt-BR", "en")],
)
async def test_the_setup_offers_home_assistants_language_first(hass, service, system, shown):
    """The system language where the integration ships it -- a regional
    variant by its base language -- and English where it does not."""
    hass.config.language = system
    assert _preselected(await _setup_form(hass, service)) == shown


async def test_the_frontend_gets_the_setup_language_open_and_preselected(hass, hass_client):
    """What the Price Tracker's setup dialog receives, through Home
    Assistant's own flow API: two expandable sections, expanded -- the
    currencies with none chosen, then the language with the system language
    as its default."""
    hass.config.language = "de"
    assert await async_setup_component(hass, "config", {})
    client = await hass_client()
    response = await client.post("/api/config/config_entries/flow", json={"handler": DOMAIN})
    menu = await response.json()
    response = await client.post(
        f"/api/config/config_entries/flow/{menu['flow_id']}",
        json={"next_step_id": "price_tracker"},
    )
    shown = await response.json()
    assert shown["step_id"] == "price_tracker"
    assert [
        (field["name"], field["type"], field["expanded"]) for field in shown["data_schema"]
    ] == [("currencies", "expandable", True), ("language", "expandable", True)]
    assert [
        [(inner["name"], inner["default"]) for inner in field["schema"]]
        for field in shown["data_schema"]
    ] == [[("extra_currencies", [])], [("language", "de")]]


# --- Every field has a label and a help text ------------------------------------------

_STRINGS = json.loads(
    (
        Path(__file__).parent.parent / "custom_components" / "bitpanda" / "strings.json"
    ).read_text(encoding="utf-8")
)


def _fields_without_texts(flow: str, result) -> dict[str, list[str]]:
    """The fields of the form `result` shows that lack a label (`data`) or a
    help text shown under the field (`data_description`) in strings.json --
    a field inside a section by that section's texts, which also need the
    section's `name`."""
    step = _STRINGS[flow]["step"][result["step_id"]]
    markers = list(result["data_schema"].schema.items())
    assert markers, result["step_id"]
    missing: dict[str, list[str]] = {}
    for marker, validator in markers:
        if isinstance(validator, section):
            texts = step.get("sections", {}).get(str(marker), {})
            if not texts.get("name"):
                missing.setdefault("name", []).append(str(marker))
            fields = [str(field) for field in validator.schema.schema]
        else:
            texts, fields = step, [str(marker)]
        for kind in ("data", "data_description"):
            for field in fields:
                if field not in texts.get(kind, {}):
                    missing.setdefault(kind, []).append(field)
    return missing


async def test_every_field_of_every_form_has_a_label_and_a_help_text(hass):
    """Setup of both services, reauth, reconfigure and both Configure forms:
    each field shows its label and, under it, its help text -- but the key
    in the Portfolio's setup, whose step text is the guide to it."""
    forms = []
    result = await _portfolio_form(hass)
    forms.append(("config", result))
    forms.append(("config", await _submit_key(hass, result, "good")))
    result = await _start(hass)
    forms.append(
        (
            "config",
            await hass.config_entries.flow.async_configure(
                result["flow_id"], {"next_step_id": "price_tracker"}
            ),
        )
    )
    portfolio = _portfolio_entry()
    portfolio.add_to_hass(hass)
    forms.append(("config", await portfolio.start_reauth_flow(hass)))
    forms.append(("config", await portfolio.start_reconfigure_flow(hass)))
    forms.append(("options", await hass.config_entries.options.async_init(portfolio.entry_id)))
    tracker = _price_tracker_entry()
    tracker.add_to_hass(hass)
    forms.append(("options", await hass.config_entries.options.async_init(tracker.entry_id)))

    assert [(flow, result["step_id"]) for flow, result in forms] == [
        ("config", "portfolio"),
        ("config", "currency"),
        ("config", "price_tracker"),
        ("config", "reauth_confirm"),
        ("config", "reconfigure"),
        ("options", "portfolio"),
        ("options", "price_tracker"),
    ]
    without_help_text = {("config", "portfolio"): {"data_description": ["api_key"]}}
    for flow, result in forms:
        form = (flow, result["step_id"])
        assert _fields_without_texts(flow, result) == without_help_text.get(form, {}), form


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
        result["flow_id"], {"currencies": {"extra_currencies": ["usd"]}, **_setup_language("en")}
    )
    entry = result["result"]
    assert dict(entry.options) == {"extra_currencies": ["USD"], "language": "en"}

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert _form_defaults(result)["currencies"]["extra_currencies"] == ["usd"]
