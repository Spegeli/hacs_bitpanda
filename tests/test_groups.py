"""Groups: config subentries that sort an entry's devices by asset type."""
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigSubentryData
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.groups import (
    async_add_asset_to_group,
    async_get_or_create_wallet_group,
    async_group_titles,
    async_known_group_titles,
    async_remove_asset_from_group,
    async_retitle_groups_to_current_language,
    entities_by_group,
    group_of_category,
    groups_of_type,
    price_group_of_asset,
    tracked_assets,
)

from tests.conftest import load_fixture, price_group, wallet_group

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


async def test_entities_are_found_by_the_group_they_sit_in(hass):
    """Disabled ones included; an entity in no group, or of another entry,
    is in none of them."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, data={"entry_type": "portfolio"},
        subentries_data=[wallet_group("crypto"), wallet_group("metal"), wallet_group("etf")],
    )
    other = MockConfigEntry(domain=DOMAIN, version=3, subentries_data=[wallet_group("crypto")])
    entry.add_to_hass(hass)
    other.add_to_hass(hass)
    ids = {sub.unique_id: sub.subentry_id for sub in entry.subentries.values()}
    [elsewhere] = other.subentries
    ent_reg = er.async_get(hass)

    def _entity(owner, unique_id: str, subentry_id: str | None = None, **kwargs) -> str:
        return ent_reg.async_get_or_create(
            "sensor", DOMAIN, unique_id, config_entry=owner, config_subentry_id=subentry_id,
            **kwargs,
        ).entity_id

    btc = _entity(entry, "btc", ids["crypto"])
    sol = _entity(entry, "sol", ids["crypto"], disabled_by=er.RegistryEntryDisabler.USER)
    gold = _entity(entry, "gold", ids["metal"])
    _entity(entry, "outside")
    _entity(other, "elsewhere", elsewhere)

    members = entities_by_group(hass, entry)

    assert {group: sorted(e.entity_id for e in regs) for group, regs in members.items()} == {
        ids["crypto"]: sorted([btc, sol]),
        ids["metal"]: [gold],
    }


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


async def test_an_asset_leaves_its_group_and_the_last_one_takes_the_group_along(hass):
    """One change per removal, so the update listener reloads once."""
    entry = _entry(hass, price_group("crypto", BTC, SOL), price_group("index", BCI5))
    listener = AsyncMock()
    entry.add_update_listener(listener)

    async_remove_asset_from_group(hass, entry, SOL["id"])
    await hass.async_block_till_done()
    assert tracked_assets(entry) == {a["id"]: slim_asset(a) for a in (BTC, BCI5)}
    assert listener.call_count == 1

    async_remove_asset_from_group(hass, entry, BCI5["id"])
    await hass.async_block_till_done()
    assert [group.unique_id for group in groups_of_type(entry, "price_group")] == ["crypto"]
    assert listener.call_count == 2

    # Tracked nowhere: nothing changes.
    async_remove_asset_from_group(hass, entry, GOLD["id"])
    await hass.async_block_till_done()
    assert listener.call_count == 2


async def test_a_wallet_group_is_created_once_and_holds_just_its_category(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    entry.add_to_hass(hass)
    titles = await async_group_titles(hass)

    group = async_get_or_create_wallet_group(hass, entry, "metal", titles)

    assert (group.subentry_type, group.unique_id, group.title, dict(group.data)) == (
        "wallet_group", "metal", "Precious metals", {"category": "metal"},
    )
    assert list(entry.subentries) == [group.subentry_id]
    # Found, not created again -- and its title is the one it was created with.
    again = async_get_or_create_wallet_group(hass, entry, "metal", {**titles, "metal": "Metalle"})
    assert (again.subentry_id, again.title) == (group.subentry_id, "Precious metals")
    assert list(entry.subentries) == [group.subentry_id]


# --- Retitling to Home Assistant's current language (Task 24) ------------------


async def test_known_group_titles_are_read_from_every_shipped_language(hass):
    """Reads the real translation files, not mocked: a category's known set
    always has this integration's own EN and DE default title (its only
    shipped languages so far)."""
    known = await async_known_group_titles(hass)
    assert known["crypto"] == {"Cryptocurrencies", "Kryptowährungen"}
    assert known["metal"] == {"Precious metals", "Edelmetalle"}
    assert known["other"] == {"Other", "Sonstige"}


async def test_a_group_titled_a_default_in_another_language_is_retitled(hass):
    hass.config.language = "de"
    entry = _entry(hass, price_group("crypto", BTC, title="Cryptocurrencies"))

    await async_retitle_groups_to_current_language(hass, entry, "price_group")

    assert group_of_category(entry, "price_group", "crypto").title == "Kryptowährungen"


async def test_a_group_already_titled_for_the_current_language_is_left_alone(hass):
    hass.config.language = "de"
    entry = _entry(hass, price_group("crypto", BTC, title="Kryptowährungen"))
    group_before = group_of_category(entry, "price_group", "crypto")

    with patch.object(
        hass.config_entries, "async_update_subentry",
        wraps=hass.config_entries.async_update_subentry,
    ) as spy:
        await async_retitle_groups_to_current_language(hass, entry, "price_group")

    spy.assert_not_called()
    assert group_of_category(entry, "price_group", "crypto") is group_before


async def test_a_user_renamed_group_is_left_alone(hass):
    """A title the user chose, "Meine Coins", is not a shipped default of any
    language, so it is never mistaken for one, whatever category it sits in.
    """
    hass.config.language = "de"
    entry = _entry(hass, price_group("crypto", BTC, title="Meine Coins"))

    await async_retitle_groups_to_current_language(hass, entry, "price_group")

    assert group_of_category(entry, "price_group", "crypto").title == "Meine Coins"


async def test_retitling_ignores_groups_of_another_subentry_type(hass):
    """A wallet_group is never touched while retitling price_group groups."""
    wallets = ConfigSubentryData(
        data={"category": "crypto"}, subentry_type="wallet_group",
        title="Cryptocurrencies", unique_id="crypto",
    )
    entry = _entry(hass, price_group("crypto", BTC, title="Cryptocurrencies"), wallets)
    hass.config.language = "de"

    await async_retitle_groups_to_current_language(hass, entry, "price_group")

    assert group_of_category(entry, "wallet_group", "crypto").title == "Cryptocurrencies"
    assert group_of_category(entry, "price_group", "crypto").title == "Kryptowährungen"
