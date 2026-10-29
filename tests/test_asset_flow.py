"""Tests for the "Add price tracker" subentry flow."""
from datetime import timedelta
import json
from pathlib import Path
from unittest.mock import ANY, AsyncMock, patch

from homeassistant import data_entry_flow
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.config_entries import ConfigSubentryData, UnknownEntry
from homeassistant.util import dt as dt_util
import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda import keys
from custom_components.bitpanda.api import BitpandaApiError, BitpandaAuthError, BitpandaRateLimitError
from custom_components.bitpanda.assets import asset_label, slim_asset
from custom_components.bitpanda.const import API_BASE_URL, DOMAIN
from custom_components.bitpanda.naming import asset_display_label

from tests.conftest import LENT_KEY, load_fixture, price_group

_LIST = "custom_components.bitpanda.asset_flow.BitpandaApiClient.async_list_assets"
_STORE = "bitpanda_asset_catalogue"
_FLOW = data_entry_flow.FlowResultType


def _fixture(symbol: str, type_: str | None = None) -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == symbol and (type_ is None or a["type"] == type_)
    )


def _metals() -> list[dict]:
    return [a for a in load_fixture("assets-sample.json") if a.get("group") == "metal"]


GOLD, SILVER = _fixture("XAU", "commodity"), _fixture("XAG")


def _entry(hass, *groups: ConfigSubentryData, **options) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="price_tracker",
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": [], **options},
        subentries_data=list(groups),
    )
    entry.add_to_hass(hass)
    return entry


async def _start(hass, entry):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "price_group"), context={"source": "user"}
    )
    assert result["step_id"] == "user"
    return result


async def _pick_category(hass, entry, category="metal"):
    result = await _start(hass, entry)
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"category": category}
    )


async def _pick_metal(hass, entry, asset: dict):
    """Precious metals, then `asset`."""
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
        return await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": asset["id"]}
        )


def _options(result) -> list[dict]:
    for marker, validator in result["data_schema"].schema.items():
        if marker == "asset":
            return validator.config["options"]
    raise KeyError("asset")


_STEP_TEXTS = json.loads(
    (
        Path(__file__).parent.parent / "custom_components" / "bitpanda" / "strings.json"
    ).read_text(encoding="utf-8")
)["config_subentries"]["price_group"]["step"]


async def test_every_field_of_every_step_has_a_label_and_a_help_text(hass):
    """Each field shows its label and, under it, its help text -- in the
    asset step of either kind of search too."""
    entry = _entry(hass)
    forms = [await _start(hass, entry)]
    with patch(_LIST, AsyncMock(return_value=_metals())):
        forms.append(await _pick_category(hass, entry))
        forms.append(await _pick_category(hass, entry, "stock"))
    assert [result["step_id"] for result in forms] == ["user", "asset", "security"]
    for result in forms:
        step = _STEP_TEXTS[result["step_id"]]
        fields = {str(marker) for marker in result["data_schema"].schema}
        assert set(step["data"]) == fields, result["step_id"]
        assert set(step.get("data_description", {})) == fields, result["step_id"]


async def test_the_portfolio_offers_no_subentries(hass):
    from custom_components.bitpanda.config_flow import BitpandaConfigFlow

    portfolio = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    assert BitpandaConfigFlow.async_get_supported_subentry_types(portfolio) == {}


# --- Listing ---------------------------------------------------------------------


async def test_listing_is_one_searchable_single_pick_minus_tracked_assets(hass):
    entry = _entry(hass, price_group("metal", GOLD))
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
    assert result["step_id"] == "asset"
    options = _options(result)
    assert all(option["value"] == option["label"] for option in options)
    labels = {option["label"] for option in options}
    assert asset_label(GOLD) not in labels
    assert len(labels) == 3
    for marker, validator in result["data_schema"].schema.items():
        if marker == "asset":
            assert validator.config["custom_value"] is True
            assert validator.config.get("multiple", False) is False


async def test_an_asset_tracked_in_any_group_is_left_out_of_the_listing(hass):
    """Gold filed under another group -- as if the catalogue had re-typed it
    since -- is tracked all the same."""
    entry = _entry(hass, price_group("other", GOLD))
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
    assert asset_label(GOLD) not in {option["label"] for option in _options(result)}


async def _finish_by_starting_a_group(hass, entry, result, category: str, asset: dict) -> None:
    """Go on from the asset step `result` -- shown with an error -- back to
    the asset types (an empty submit), then through `category`, whose
    listing now works, to `asset`: the first of its type, it starts its
    group."""
    assert (result["type"], result["step_id"]) == (_FLOW.FORM, "asset")
    listing = [a for a in load_fixture("assets-sample.json") if a["id"] == asset["id"]]
    with patch(_LIST, AsyncMock(return_value=listing)):
        result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
        assert result["step_id"] == "user"
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"category": category}
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": asset_label(asset)}
        )
    assert result["type"] == _FLOW.CREATE_ENTRY
    group = next(sub for sub in entry.subentries.values() if sub.unique_id == category)
    assert list(group.data["assets"]) == [asset["id"]]


async def test_a_fully_tracked_category_says_so(hass):
    entry = _entry(hass, price_group("metal", *_metals()))
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
    assert result["errors"]["base"] == "no_assets_available"
    await _finish_by_starting_a_group(hass, entry, result, "crypto", _fixture("BTC"))


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (BitpandaRateLimitError("Rate limited on /assets"), "rate_limited"),
        (BitpandaApiError("Timeout for /assets"), "cannot_connect"),
    ],
    ids=["rate_limited", "cannot_connect"],
)
async def test_listing_errors_map_to_form_errors(hass, failure, error):
    entry = _entry(hass)
    with patch(_LIST, AsyncMock(side_effect=failure)):
        result = await _pick_category(hass, entry)
    assert result["errors"]["base"] == error
    assert _options(result) == []
    await _finish_by_starting_a_group(hass, entry, result, "metal", SILVER)


async def test_a_listing_of_the_wrong_shape_says_cannot_connect(hass):
    """The real client against the test mocker, one level up from api.py's
    own tests -- a wrong-shaped /assets body must not escape
    _paginate as AttributeError and leave the dialog showing "Unknown error
    occurred"; it is as unreadable as a malformed body, and cannot_connect
    the same way."""
    entry = _entry(hass)
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets",
            json={"data": ["x"], "has_next_page": False},
        )
        result = await _pick_category(hass, entry)
    assert result["errors"]["base"] == "cannot_connect"


async def test_the_listing_sends_the_portfolios_key(hass):
    """Since 2026-10-28 Bitpanda lists its catalogue only to a key with Trade
    (Read): the dialog asks with the Portfolio's."""
    entry = _entry(hass)
    with patch("custom_components.bitpanda.asset_flow.BitpandaApiClient") as client_cls:
        client_cls.return_value.async_list_assets = AsyncMock(return_value=_metals())
        await _pick_category(hass, entry)
    client_cls.assert_called_once_with(LENT_KEY, ANY)


@pytest.mark.no_portfolio_key
async def test_add_price_tracker_needs_a_portfolio(hass):
    """Without a Portfolio to lend its key, the dialog says to set one up
    before it asks anything."""
    entry = _entry(hass)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "price_group"), context={"source": "user"}
    )
    assert (result["type"], result["reason"]) == (FlowResultType.ABORT, "portfolio_required")


async def test_a_portfolio_gone_before_the_listing_aborts(hass):
    """The Portfolio deleted while the dialog is open, after its own check:
    no key for the listing, the same answer."""
    entry = _entry(hass)
    result = await _start(hass, entry)
    with patch.object(keys, "portfolio_api_key", side_effect=[LENT_KEY, None]):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"category": "metal"}
        )
    assert (result["type"], result["reason"]) == (FlowResultType.ABORT, "portfolio_required")


async def test_a_refused_key_shows_its_own_error_and_asks_for_a_new_one(hass, lent_portfolio_key):
    """Bitpanda refuses the Portfolio's key for the listing: the dialog says
    the key lacks Trade (Read) and the Portfolio is asked for a new one.
    With a working key the same dialog goes on to add the asset."""
    entry = _entry(hass)
    refused = BitpandaAuthError("Unauthorized for /assets", kind="http_status", path="/assets", status=401)
    with patch(_LIST, AsyncMock(side_effect=refused)):
        result = await _pick_category(hass, entry)
    assert result["errors"]["base"] == "key_rejected"
    assert lent_portfolio_key.reauth_requests == 1
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["step_id"] == "user"
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"category": "metal"}
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": GOLD["id"]}
        )
    # Its group is new: the dialog creates it.
    assert result["type"] == _FLOW.CREATE_ENTRY


@pytest.mark.parametrize(
    ("category", "filters"),
    [
        ("stock", [("equity_security", "equity_stock")]),
        ("etf", [("equity_security", "equity_etf"), ("equity_security", "equity_complex_etf")]),
        ("etc", [("equity_security", "equity_complex_etc")]),
    ],
)
async def test_the_add_dialog_lists_only_bitpandas_current_securities(hass, category, filters):
    """Bitpanda lists most stocks, ETFs and ETCs twice: in its old line
    (type security, never buyable again) and in its current one, same
    symbol and ISIN. The dialog asks for the current line only."""
    entry = _entry(hass)
    listing = AsyncMock(return_value=[_fixture("517")])
    with patch(_LIST, listing):
        await _pick_category(hass, entry, category)
    assert [call.args for call in listing.call_args_list] == filters


async def test_a_listing_is_kept_for_an_hour_in_slim_records(hass):
    """Picked again within the hour, a category takes its listing from the
    store. An hour after the listing was loaded, a timer drops it -- whether
    or not anyone opens the dialog again, so no listing outstays its hour in
    memory -- and the next pick loads it anew."""
    entry = _entry(hass)
    listing = AsyncMock(return_value=_metals())
    with patch(_LIST, listing):
        await _pick_category(hass, entry)
        store = hass.data[_STORE]
        assert all(
            set(record) <= {"id", "symbol", "name", "isin", "type", "group"}
            for record in store["metal"]
        )
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=59))
        await _pick_category(hass, entry)
        assert listing.await_count == 1

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=1))
        assert "metal" not in store

        await _pick_category(hass, entry)
    assert listing.await_count == 2


async def test_a_timer_drops_only_the_listing_it_was_started_for(hass):
    """Two dialogs can load the same category at once, and the later listing
    replaces the earlier one in the store. The earlier one's timer must not
    drop the later listing before that listing's own hour is over."""
    with patch(_LIST, AsyncMock(return_value=_metals())):
        await _pick_category(hass, _entry(hass))
    store = hass.data[_STORE]
    later = [slim_asset(GOLD)]
    store["metal"] = later

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=1))

    assert store["metal"] is later


async def test_an_open_dialog_keeps_its_listing_when_the_hour_ends(hass):
    """The hour can end between showing the listing and submitting the pick:
    the dialog keeps the listing it showed, so the pick needs no new
    loading, and the store does not hold it any longer than its hour."""
    entry = _entry(hass)
    listing = AsyncMock(return_value=_metals())
    with patch(_LIST, listing):
        result = await _pick_category(hass, entry)
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=1))
        assert "metal" not in hass.data[_STORE]

        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": GOLD["id"]}
        )

    assert listing.await_count == 1
    assert result["type"] is _FLOW.CREATE_ENTRY


# --- One asset step per kind of search -------------------------------------------
# Stocks, ETFs and ETCs show their ISIN in the list, the other types have
# none. The asset step shows under a step id of its own for each kind, so
# each has a help text of its own -- the securities' naming the ISIN.


@pytest.mark.parametrize(
    ("category", "step_id"),
    [
        ("crypto", "asset"),
        ("index", "asset"),
        ("metal", "asset"),
        ("stock", "security"),
        ("etf", "security"),
        ("etc", "security"),
    ],
)
async def test_each_asset_type_is_picked_in_the_step_of_its_search(hass, category, step_id):
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, _entry(hass), category)
    assert (result["type"], result["step_id"]) == (_FLOW.FORM, step_id)


async def test_a_security_is_picked_like_any_asset(hass):
    """The securities' step is the asset step under texts of its own: an
    empty submit goes back to the asset types with the type picked before,
    and a pick is tracked."""
    stock = _fixture("517")
    entry = _entry(hass)
    with patch(_LIST, AsyncMock(return_value=[stock])):
        result = await _pick_category(hass, entry, "stock")
        assert result["step_id"] == "security"
        result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
        assert result["step_id"] == "user"
        assert result["data_schema"]({}) == {"category": "stock"}
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"category": "stock"}
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": stock["id"]}
        )
    assert result["type"] == _FLOW.CREATE_ENTRY
    [group] = entry.subentries.values()
    assert dict(group.data) == {"category": "stock", "assets": {stock["id"]: slim_asset(stock)}}


async def test_a_listing_error_stays_in_the_securities_step(hass):
    with patch(_LIST, AsyncMock(side_effect=BitpandaRateLimitError("Rate limited on /assets"))):
        result = await _pick_category(hass, _entry(hass), "etf")
    assert (result["step_id"], result["errors"]["base"]) == ("security", "rate_limited")


# --- Picking ---------------------------------------------------------------------


async def test_the_first_asset_of_a_type_starts_its_group(hass):
    entry = _entry(hass)
    result = await _pick_metal(hass, entry, SILVER)
    assert result["type"] == _FLOW.CREATE_ENTRY
    [group] = entry.subentries.values()
    assert group.subentry_type == "price_group"
    assert group.unique_id == "metal"
    assert group.title == "Precious metals"
    assert dict(group.data) == {"category": "metal", "assets": {SILVER["id"]: slim_asset(SILVER)}}


async def test_the_first_asset_of_a_type_ends_with_the_text_every_later_one_ends_with(hass):
    """Starting a group, the dialog names the asset and the new group, as
    joining one does (strings.json: create_entry.default = asset_added)."""
    entry = _entry(hass)
    result = await _pick_metal(hass, entry, SILVER)
    assert result["type"] == _FLOW.CREATE_ENTRY
    assert result["description_placeholders"] == {
        "asset": asset_display_label(slim_asset(SILVER)),
        "group": "Precious metals",
    }


async def test_the_picked_label_is_submitted_and_resolves_to_the_asset(hass):
    """The field's value is the label the user searched and picked, not the
    id (issue: with no valueRenderer, ha-picker-field always echoed the raw
    value back, so the field showed a UUID after picking)."""
    entry = _entry(hass)
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": asset_label(SILVER)}
        )
    assert result["type"] == _FLOW.CREATE_ENTRY
    [group] = entry.subentries.values()
    assert dict(group.data) == {
        "category": "metal",
        "assets": {SILVER["id"]: slim_asset(SILVER)},
    }


async def test_a_new_group_is_titled_in_the_entrys_language(hass):
    entry = _entry(hass, language="de")
    await _pick_metal(hass, entry, SILVER)
    [group] = entry.subentries.values()
    assert group.title == "Edelmetalle"


async def test_a_new_group_is_english_by_default_whatever_language_home_assistant_runs_in(
    hass,
):
    hass.config.language = "de"
    entry = _entry(hass)
    await _pick_metal(hass, entry, SILVER)
    [group] = entry.subentries.values()
    assert group.title == "Precious metals"


async def test_an_asset_joins_the_group_of_its_type(hass):
    """The group keeps the title the user gave it, and the dialog names it."""
    entry = _entry(
        hass, price_group("crypto", _fixture("BTC")), price_group("metal", GOLD, title="My metals")
    )
    result = await _pick_metal(hass, entry, SILVER)
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "asset_added"
    assert result["description_placeholders"] == {"asset": "Silver (XAG)", "group": "My metals"}
    groups = {group.unique_id: group for group in entry.subentries.values()}
    assert len(groups) == 2
    assert groups["metal"].title == "My metals"
    assert dict(groups["metal"].data) == {
        "category": "metal",
        "assets": {GOLD["id"]: slim_asset(GOLD), SILVER["id"]: slim_asset(SILVER)},
    }


async def test_a_stock_etf_or_etc_that_joins_its_group_is_named_with_its_isin(hass):
    """By its label, as its device is -- without the device's " Price
    Tracker"."""
    top500, exia = _fixture("SXR8", "security"), _fixture("EXIA")
    entry = _entry(hass, price_group("etf", exia, title="ETFs"))
    with patch(_LIST, AsyncMock(return_value=[top500, exia])):
        result = await _pick_category(hass, entry, "etf")
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": top500["id"]}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "asset_added")
    assert result["description_placeholders"] == {
        "asset": "Top 500 US Stocks X Acc (SXR8 / IE00B5BMR087)", "group": "ETFs",
    }


async def test_a_tracked_asset_typed_in_is_not_added_twice(hass):
    """The listing leaves tracked assets out; a typed-in id still arrives."""
    entry = _entry(hass, price_group("other", GOLD))
    result = await _pick_metal(hass, entry, GOLD)
    assert result["type"] == _FLOW.ABORT
    assert result["reason"] == "already_configured"
    [group] = entry.subentries.values()
    assert list(group.data["assets"]) == [GOLD["id"]]


async def test_an_empty_submit_goes_back_to_the_categories(hass):
    entry = _entry(hass)
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
        result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["step_id"] == "user"


async def test_going_back_keeps_the_category_picked_before(hass):
    """The first time, nothing is pre-selected; coming back from the asset
    step, the category the user had picked is."""
    entry = _entry(hass)
    result = await _start(hass, entry)
    with pytest.raises(vol.Invalid):
        result["data_schema"]({})
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"category": "metal"}
        )
        result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["step_id"] == "user"
    assert result["data_schema"]({}) == {"category": "metal"}


async def test_a_typed_value_that_is_no_asset_is_rejected(hass):
    """The same step then takes a picked asset: here it joins the group of
    its type, which exists already."""
    entry = _entry(hass, price_group("metal", GOLD, title="Metals"))
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": "gold please"}
        )
        assert result["step_id"] == "asset"
        assert result["errors"]["base"] == "unknown_asset"
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": asset_label(SILVER)}
        )
    assert (result["type"], result["reason"]) == (_FLOW.ABORT, "asset_added")
    assert result["description_placeholders"] == {"asset": "Silver (XAG)", "group": "Metals"}
    [group] = entry.subentries.values()
    assert list(group.data["assets"]) == [GOLD["id"], SILVER["id"]]


async def test_a_price_tracker_removed_while_the_dialog_is_open(hass):
    """The listing still opens; only the final pick ends in Home Assistant's
    own UnknownEntry."""
    entry = _entry(hass)
    result = await _start(hass, entry)
    await hass.config_entries.async_remove(entry.entry_id)
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"category": "metal"}
        )
        assert result["step_id"] == "asset"
        assert len(_options(result)) == 4
        with pytest.raises(UnknownEntry):
            await hass.config_entries.subentries.async_configure(
                result["flow_id"], {"asset": SILVER["id"]}
            )
