"""Groups: config subentries that sort an entry's devices by asset type."""
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigSubentryData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.groups import (
    async_add_asset_to_group,
    async_group_titles,
    group_of_category,
    groups_of_type,
    price_group_of_asset,
    tracked_assets,
)

from tests.conftest import load_fixture, price_group

_TRANSLATIONS = "custom_components.bitpanda.groups.async_get_translations"


def _asset(symbol: str, type_: str | None = None) -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == symbol and (type_ is None or a["type"] == type_)
    )


BTC, SOL, BCI5, GOLD = _asset("BTC"), _asset("SOL"), _asset("BCI5"), _asset("XAU", "commodity")


def _entry(hass, *groups: ConfigSubentryData) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": []},
        subentries_data=list(groups),
    )
    entry.add_to_hass(hass)
    return entry


# --- Titles --------------------------------------------------------------------


async def test_group_titles_are_in_the_language_home_assistant_runs_in(hass):
    assert await async_group_titles(hass) == {
        "crypto": "Cryptocurrencies",
        "stock": "Stocks",
        "etf": "ETFs",
        "etc": "ETCs",
        "index": "Crypto indices",
        "metal": "Precious metals",
        "other": "Other",
    }
    hass.config.language = "de"
    assert await async_group_titles(hass) == {
        "crypto": "Kryptowährungen",
        "stock": "Aktien",
        "etf": "ETFs",
        "etc": "ETCs",
        "index": "Krypto-Indizes",
        "metal": "Edelmetalle",
        "other": "Sonstige",
    }


async def test_a_category_without_a_translation_is_titled_with_its_key(hass):
    translations = AsyncMock(
        return_value={"component.bitpanda.selector.asset_group.options.crypto": "Krypto"}
    )
    with patch(_TRANSLATIONS, translations):
        titles = await async_group_titles(hass)
    translations.assert_awaited_once_with(hass, "en", "selector", {"bitpanda"})
    assert titles["crypto"] == "Krypto"
    assert titles["metal"] == "metal"
    assert titles["other"] == "other"


# --- Lookups ---------------------------------------------------------------------


async def test_groups_are_found_by_their_type_and_category(hass):
    wallets = ConfigSubentryData(
        data={"category": "metal"}, subentry_type="wallet_group", title="Metals", unique_id="metal"
    )
    entry = _entry(hass, price_group("crypto", BTC), price_group("index", BCI5), wallets)
    ids = {sub.unique_id: sub.subentry_id for sub in entry.subentries.values()}
    assert [group.unique_id for group in groups_of_type(entry, "price_group")] == [
        "crypto", "index",
    ]
    assert group_of_category(entry, "price_group", "index").subentry_id == ids["index"]
    assert group_of_category(entry, "price_group", "metal") is None
    assert group_of_category(entry, "wallet_group", "metal").subentry_id == ids["metal"]


async def test_the_price_tracker_tracks_the_assets_of_all_its_groups(hass):
    entry = _entry(hass, price_group("crypto", BTC, SOL), price_group("index", BCI5))
    assert tracked_assets(entry) == {a["id"]: slim_asset(a) for a in (BTC, SOL, BCI5)}
    assert price_group_of_asset(entry, SOL["id"]).unique_id == "crypto"
    assert price_group_of_asset(entry, BCI5["id"]).unique_id == "index"
    assert price_group_of_asset(entry, GOLD["id"]) is None


# --- Changes ---------------------------------------------------------------------


async def test_an_asset_added_to_a_group_is_saved_and_keeps_the_title(hass):
    entry = _entry(hass, price_group("crypto", BTC, title="My coins"))
    listener = AsyncMock()
    entry.add_update_listener(listener)
    group = group_of_category(entry, "price_group", "crypto")

    async_add_asset_to_group(hass, entry, group, slim_asset(SOL))
    await hass.async_block_till_done()

    assert dict(group.data) == {
        "category": "crypto",
        "assets": {BTC["id"]: slim_asset(BTC), SOL["id"]: slim_asset(SOL)},
    }
    assert group.title == "My coins"
    listener.assert_called_once()
