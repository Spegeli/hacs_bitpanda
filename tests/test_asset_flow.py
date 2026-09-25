"""Tests for the "Add price tracker" subentry flow."""
from datetime import timedelta
from unittest.mock import ANY, AsyncMock, patch

from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.const import DOMAIN

from tests.conftest import load_fixture

_LIST = "custom_components.bitpanda.asset_flow.BitpandaApiClient.async_list_assets"
_FLOW = data_entry_flow.FlowResultType


def _fixture(symbol: str, type_: str | None = None) -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == symbol and (type_ is None or a["type"] == type_)
    )


def _metals() -> list[dict]:
    return [a for a in load_fixture("assets-sample.json") if a.get("group") == "metal"]


def _entry(hass, tracked=()) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="price_tracker",
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": []},
        subentries_data=[
            ConfigSubentryData(
                data={"asset": slim_asset(a)},
                subentry_type="asset",
                title=a["name"],
                unique_id=a["id"],
            )
            for a in tracked
        ],
    )
    entry.add_to_hass(hass)
    return entry


async def _pick_category(hass, entry, category="metal"):
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "asset"), context={"source": "user"}
    )
    assert result["step_id"] == "user"
    return await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"category": category}
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


async def test_listing_is_one_searchable_single_pick_minus_tracked_assets(hass):
    gold = _fixture("XAU", "commodity")
    entry = _entry(hass, tracked=[gold])
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
    assert result["step_id"] == "asset"
    values = {option["value"] for option in _options(result)}
    assert gold["id"] not in values
    assert len(values) == 3
    for marker, validator in result["data_schema"].schema.items():
        if marker == "asset":
            assert validator.config["custom_value"] is True
            assert validator.config.get("multiple", False) is False


async def test_picking_an_asset_creates_its_subentry(hass):
    entry = _entry(hass)
    silver = _fixture("XAG")
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": silver["id"]}
        )
    assert result["type"] == _FLOW.CREATE_ENTRY
    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "Silver (XAG)"
    assert subentry.unique_id == silver["id"]
    assert dict(subentry.data) == {"asset": slim_asset(silver)}


async def test_an_empty_submit_goes_back_to_the_categories(hass):
    entry = _entry(hass)
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
        result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["step_id"] == "user"


async def test_a_typed_value_that_is_no_asset_is_rejected(hass):
    entry = _entry(hass)
    with patch(_LIST, AsyncMock(return_value=_metals())):
        result = await _pick_category(hass, entry)
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"asset": "gold please"}
        )
    assert result["step_id"] == "asset"
    assert result["errors"]["base"] == "unknown_asset"


async def test_a_fully_tracked_category_says_so(hass):
    entry = _entry(hass, tracked=_metals())
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
