"""Tests for the "Add price tracker" subentry flow."""
from datetime import timedelta
from unittest.mock import ANY, AsyncMock, patch

from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigSubentryData, UnknownEntry
from homeassistant.util import dt as dt_util
import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.assets import asset_label, slim_asset
from custom_components.bitpanda.const import DOMAIN

from tests.conftest import load_fixture, price_group

_LIST = "custom_components.bitpanda.asset_flow.BitpandaApiClient.async_list_assets"
_FLOW = data_entry_flow.FlowResultType


def _fixture(symbol: str, type_: str | None = None) -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == symbol and (type_ is None or a["type"] == type_)
    )


def _metals() -> list[dict]:
    return [a for a in load_fixture("assets-sample.json") if a.get("group") == "metal"]


GOLD, SILVER = _fixture("XAU", "commodity"), _fixture("XAG")


def _entry(hass, *groups: ConfigSubentryData) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="price_tracker",
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": []},
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


async def test_a_fully_tracked_category_says_so(hass):
    entry = _entry(hass, price_group("metal", *_metals()))
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
    assert result["errors"]["base"] == "no_assets_available"


async def test_listing_errors_map_to_form_errors(hass):
    entry = _entry(hass)
    with patch(_LIST, AsyncMock(side_effect=BitpandaRateLimitError("x"))):
        result = await _pick_category(hass, entry)
    assert result["errors"]["base"] == "rate_limited"
    with patch(_LIST, AsyncMock(side_effect=BitpandaApiError("x"))):
        result = await _pick_category(hass, entry)
    assert result["errors"]["base"] == "cannot_connect"


async def test_the_catalogue_is_fetched_without_a_key(hass):
    entry = _entry(hass)
    with patch("custom_components.bitpanda.asset_flow.BitpandaApiClient") as client_cls:
        client_cls.return_value.async_list_assets = AsyncMock(return_value=_metals())
        await _pick_category(hass, entry)
    client_cls.assert_called_once_with(None, ANY)


async def test_the_stock_category_merges_both_listing_families(hass):
    entry = _entry(hass)
    listing = AsyncMock(side_effect=[[_fixture("517")], [_fixture("ESSITYB", "security")]])
    with patch(_LIST, listing):
        result = await _pick_category(hass, entry, "stock")
    assert [call.args for call in listing.call_args_list] == [
        ("equity_security", "equity_stock"),
        ("security", "stock"),
    ]
    assert len(_options(result)) == 2


async def test_a_listing_is_cached_for_24_hours_in_slim_records(hass):
    """Time is moved by editing the cached timestamp, not by mocking the clock."""
    entry = _entry(hass)
    listing = AsyncMock(return_value=_metals())
    with patch(_LIST, listing):
        await _pick_category(hass, entry)
        await _pick_category(hass, entry)
        assert listing.await_count == 1
        store = hass.data["bitpanda_asset_catalogue"]
        fetched_at, records = store["metal"]
        assert all(
            set(record) <= {"id", "symbol", "name", "isin", "type", "group"}
            for record in records
        )
        store["metal"] = (fetched_at - timedelta(hours=24, minutes=1), records)
        await _pick_category(hass, entry)
    assert listing.await_count == 2


async def test_expired_listings_are_dropped_not_kept(hass):
    store = hass.data.setdefault("bitpanda_asset_catalogue", {})
    store["stock"] = (dt_util.utcnow() - timedelta(hours=25), [{"id": "old"}])
    with patch(_LIST, AsyncMock(return_value=_metals())):
        await _pick_category(hass, _entry(hass))
    assert "stock" not in store
    assert "metal" in store


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


async def test_a_new_group_is_titled_in_the_language_home_assistant_runs_in(hass):
    hass.config.language = "de"
    entry = _entry(hass)
    await _pick_metal(hass, entry, SILVER)
    [group] = entry.subentries.values()
    assert group.title == "Edelmetalle"


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
    entry = _entry(hass)
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": "gold please"}
        )
    assert result["step_id"] == "asset"
    assert result["errors"]["base"] == "unknown_asset"


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
