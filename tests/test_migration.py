"""Tests for v1 to v3 config entry migration."""
import logging
from unittest.mock import ANY, AsyncMock, patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import subentry_devices
from custom_components.bitpanda.ecb import EcbRates
from custom_components.bitpanda.migration import (
    async_adopt_legacy_prices,
    async_migrate_entry,
    free_entity_id,
    legacy_prefix,
    legacy_symbol,
)

from tests.conftest import load_fixture, price_group

_API = "custom_components.bitpanda.migration.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_USD_ID = "b88b8879-efe3-11eb-b56f-0691764446a7"
BTC_ID = "b86c034b-efe3-11eb-b56f-0691764446a7"
GOLD_ID = "b86c88d4-efe3-11eb-b56f-0691764446a7"
BCI5_ID = "b86ca64c-efe3-11eb-b56f-0691764446a7"


def _by_symbol(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["symbol"] == kwargs.get("symbol")]


@pytest.fixture
def legacy_api():
    with patch(
        f"{_API}async_get_currencies", AsyncMock(return_value=load_fixture("currencies.json"))
    ) as currencies, patch(f"{_API}async_get_assets", AsyncMock(side_effect=_by_symbol)) as assets:
        yield currencies, assets


@pytest.fixture
def no_setup():
    """The Price Tracker the import creates would be set up for real."""
    with patch("custom_components.bitpanda.async_setup_entry", return_value=True):
        yield


def _v1_entry(hass, currency="EUR", assets=(), wallets=()) -> MockConfigEntry:
    """Shaped like a genuine version 1 install: no entry_type, no currency_id."""
    # In production the migration always runs inside the domain's own setup,
    # so the domain is already registered by the time it runs. Without this,
    # the import flow's setup of the new Price Tracker would set up the whole
    # domain again, including the version 1 entry, and re-enter the migration.
    hass.config.components.add(DOMAIN)
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="Bitpanda",
        data={"api_key": "legacy-key", "currency": currency},
        options={"tracked_assets": list(assets), "tracked_wallets": list(wallets)},
    )
    entry.add_to_hass(hass)
    return entry


def _price_trackers(hass) -> list:
    return [
        e for e in hass.config_entries.async_entries(DOMAIN)
        if e.data.get("entry_type") == "price_tracker"
    ]


async def test_version_3_is_current(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)


async def test_a_newer_version_is_refused(hass, caplog):
    entry = MockConfigEntry(domain=DOMAIN, version=4, data={})
    entry.add_to_hass(hass)
    assert not await async_migrate_entry(hass, entry)
    assert "newer release" in caplog.text


async def test_a_version_2_development_build_must_be_re_added(hass, caplog):
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"api_key": "k"})
    entry.add_to_hass(hass)
    assert not await async_migrate_entry(hass, entry)
    assert "remove the Bitpanda integration and add it again" in caplog.text


_MIGRATION = "custom_components.bitpanda.migration"


@pytest.mark.parametrize("minor", [3, 4])
async def test_home_assistant_before_2025_5_leaves_the_entry_alone(
    hass, legacy_api, no_setup, notify, caplog, minor
):
    """Only from Home Assistant 2025.5 on does the recorder move history along
    with an entity-ID rename made while Home Assistant starts -- when this
    migration runs. Before, every migrated entity would lose its history, so
    the migration refuses and changes nothing, not even with an API call."""
    currencies, assets = legacy_api
    entry = _v1_entry(hass, assets=["BTC"], wallets=["cryptocoin_BTC"])
    eid = entry.entry_id
    wallet = _legacy_entity(
        hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet"
    )
    with patch(f"{_MIGRATION}.MAJOR_VERSION", 2025), patch(f"{_MIGRATION}.MINOR_VERSION", minor):
        assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1
    assert dict(entry.data) == {"api_key": "legacy-key", "currency": "EUR"}
    assert dict(entry.options) == {"tracked_assets": ["BTC"], "tracked_wallets": ["cryptocoin_BTC"]}
    reg_entry = er.async_get(hass).async_get(wallet)
    assert reg_entry.unique_id == f"{eid}_wallet_cryptocoin_BTC"
    assert reg_entry.entity_id == "sensor.bitpanda_wallets_btc_wallet"
    assert _price_trackers(hass) == []
    currencies.assert_not_called()
    assets.assert_not_called()
    notify.assert_not_called()
    assert "Home Assistant 2025.5 or newer" in caplog.text
    assert "legacy-key" not in caplog.text


async def test_home_assistant_2025_5_migrates(hass, legacy_api, no_setup, notify):
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    with patch(f"{_MIGRATION}.MAJOR_VERSION", 2025), patch(f"{_MIGRATION}.MINOR_VERSION", 5):
        assert await async_migrate_entry(hass, entry)
    assert entry.version == 3


async def test_v1_becomes_the_portfolio(hass, legacy_api, no_setup):
    entry = _v1_entry(hass, currency="USD", wallets=["cryptocoin_BTC"])
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 3
    assert entry.title == "Bitpanda Portfolio"
    assert entry.unique_id == "portfolio"
    assert dict(entry.data) == {
        "entry_type": "portfolio",
        "api_key": "legacy-key",
        "currency": "USD",
        "currency_id": _USD_ID,
    }
    assert dict(entry.options) == {}


async def test_public_lookups_never_carry_the_legacy_key(hass, no_setup):
    entry = _v1_entry(hass, assets=["BTC"])
    with patch("custom_components.bitpanda.migration.BitpandaApiClient") as client_cls:
        client_cls.return_value.async_get_currencies = AsyncMock(
            return_value=load_fixture("currencies.json")
        )
        client_cls.return_value.async_get_assets = AsyncMock(side_effect=_by_symbol)
        assert await async_migrate_entry(hass, entry)
    client_cls.assert_called_once_with(None, ANY)


async def test_tracked_prices_become_the_price_tracker(hass, legacy_api, no_setup):
    entry = _v1_entry(hass, currency="USD", assets=["BTC", "XAU"])
    assert await async_migrate_entry(hass, entry)
    [tracker] = _price_trackers(hass)
    assert tracker.unique_id == "price_tracker"
    assert dict(tracker.options) == {"extra_currencies": ["USD"]}
    # One group per asset type. XAU is both the GoldMoney stock and the Gold
    # metal; the legacy API only ever tracked the metal.
    groups = {s.unique_id: s for s in tracker.subentries.values()}
    assert {category: group.title for category, group in groups.items()} == {
        "crypto": "Cryptocurrencies",
        "metal": "Precious metals",
    }
    assert list(groups["crypto"].data["assets"]) == [BTC_ID]
    assert list(groups["metal"].data["assets"]) == [GOLD_ID]


async def test_an_eur_install_adds_no_extra_currency(hass, legacy_api, no_setup):
    assert await async_migrate_entry(hass, _v1_entry(hass, assets=["BTC"]))
    [tracker] = _price_trackers(hass)
    assert dict(tracker.options) == {"extra_currencies": []}


async def test_without_tracked_prices_no_price_tracker_is_created(hass, legacy_api, no_setup):
    assert await async_migrate_entry(hass, _v1_entry(hass, wallets=["cryptocoin_BTC"]))
    assert _price_trackers(hass) == []


async def test_any_api_error_changes_nothing(hass, legacy_api, no_setup, caplog):
    _, assets = legacy_api
    assets.side_effect = BitpandaApiError("Timeout for /assets")
    entry = _v1_entry(hass, assets=["BTC"], wallets=["cryptocoin_BTC"])
    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1
    assert dict(entry.options) == {"tracked_assets": ["BTC"], "tracked_wallets": ["cryptocoin_BTC"]}
    assert _price_trackers(hass) == []
    assert "Timeout for /assets" in caplog.text
    assert "legacy-key" not in caplog.text


async def test_a_rate_limit_changes_nothing(hass, legacy_api, no_setup):
    currencies, _ = legacy_api
    currencies.side_effect = BitpandaRateLimitError("Rate limited on /currencies")
    entry = _v1_entry(hass)
    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1


async def test_an_existing_portfolio_blocks_the_migration(hass, legacy_api, no_setup):
    MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", data={"entry_type": "portfolio"}
    ).add_to_hass(hass)
    entry = _v1_entry(hass)
    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1


async def test_a_currency_no_longer_offered_falls_back_to_eur(hass, legacy_api, no_setup):
    entry = _v1_entry(hass, currency="JPY")
    assert await async_migrate_entry(hass, entry)
    assert entry.data["currency"] == "EUR"
    assert entry.data["currency_id"] == _EUR_ID


async def test_each_symbol_is_looked_up_once(hass, legacy_api, no_setup):
    _, assets = legacy_api
    await async_migrate_entry(hass, _v1_entry(hass, assets=["BTC"], wallets=["cryptocoin_BTC"]))
    assert [call.kwargs["symbol"] for call in assets.call_args_list] == ["BTC"]


async def test_fiat_wallets_are_never_looked_up(hass, legacy_api, no_setup):
    _, assets = legacy_api
    await async_migrate_entry(hass, _v1_entry(hass, wallets=["fiat_EUR"]))
    assert assets.call_args_list == []


async def test_a_bare_prefix_wallet_id_never_lists_the_whole_catalogue(hass, legacy_api, no_setup):
    """`legacy_symbol("cryptocoin_")` is `""`. Without the empty-symbol guard
    in the migration's symbol lookup, an empty `symbol` would drop the query
    filter entirely and page through the whole ~14,000-asset catalogue
    instead of finding nothing.
    """
    _, assets = legacy_api
    assert await async_migrate_entry(hass, _v1_entry(hass, wallets=["cryptocoin_"]))
    assert assets.call_args_list == []


# --- legacy_symbol -----------------------------------------------------------
#
# Every id below is in a format the legacy options flow actually produced. It
# built wallet ids from the legacy /asset-wallets nesting: "{category}_{symbol}"
# for a flat category and "{category}_{sub}_{symbol}" for a nested one. Crypto
# was flat; metals sat under commodity -> metal and indices under
# index -> index (verified against the live legacy API). So the formats are
# cryptocoin_<SYM>, commodity_metal_<SYM>, index_index_<SYM>, plus fiat_<SYM>
# from the separate fiat wallet listing.


def test_legacy_symbol_from_two_part_id():
    assert legacy_symbol("fiat_EUR") == "EUR"
    assert legacy_symbol("cryptocoin_BTC") == "BTC"


def test_legacy_symbol_from_three_part_id():
    assert legacy_symbol("commodity_metal_XAU") == "XAU"
    assert legacy_symbol("index_index_BCI5") == "BCI5"


def test_legacy_symbol_tolerates_prefixes_the_legacy_flow_never_produced():
    """Defensive only: `index_`, `index_wallet_` and `metal_` never came out
    of the legacy options flow (see the section comment above), but they
    still strip cleanly rather than leave a mangled symbol behind.
    """
    assert legacy_symbol("index_BCI5") == "BCI5"
    assert legacy_prefix("index_BCI5") == "index_"
    assert legacy_symbol("index_wallet_BCI5") == "BCI5"
    assert legacy_prefix("index_wallet_BCI5") == "index_wallet_"
    assert legacy_symbol("metal_XAU") == "XAU"
    assert legacy_prefix("metal_XAU") == "metal_"


def test_legacy_symbol_keeps_symbols_containing_underscores():
    assert legacy_symbol("cryptocoin_SOME_TOKEN") == "SOME_TOKEN"


def test_legacy_symbol_of_bare_symbol():
    assert legacy_symbol("BTC") == "BTC"


def test_legacy_symbol_with_unrecognized_prefix_is_returned_unchanged():
    """No known legacy category is "stock_". The whole string is handed to
    resolution unchanged, which is expected to fail and be dropped rather
    than being misparsed into a wrong symbol.
    """
    assert legacy_symbol("stock_AAPL") == "stock_AAPL"


# --- legacy_prefix -------------------------------------------------------------
#
# pick_legacy needs to know which v1 category a wallet id claimed, not just
# its bare symbol -- legacy_prefix mirrors legacy_symbol's own prefix search
# (same _LEGACY_PREFIXES, longest/most-specific first) but returns the prefix
# itself instead of stripping it.


def test_legacy_prefix_of_two_part_id():
    assert legacy_prefix("fiat_EUR") == "fiat_"
    assert legacy_prefix("cryptocoin_BTC") == "cryptocoin_"


def test_legacy_prefix_of_three_part_id_prefers_the_longer_match():
    assert legacy_prefix("commodity_metal_XAU") == "commodity_metal_"
    # "index_" is itself a prefix of "index_index_": matching it first would
    # leave the symbol "index_BCI5", which does not exist.
    assert legacy_prefix("index_index_BCI5") == "index_index_"


def test_legacy_prefix_of_bare_symbol_is_none():
    assert legacy_prefix("BTC") is None


def test_legacy_prefix_of_unrecognized_prefix_is_none():
    assert legacy_prefix("stock_AAPL") is None


# --- free_entity_id ----------------------------------------------------------------


async def test_free_entity_id_skips_every_id_home_assistant_counts_as_taken(hass):
    """Free the way Home Assistant's entity registry means it -- registered by
    no entity, with no state and not reserved for an entity being added --
    and not already planned in this run. Renaming onto a reserved ID would
    raise in the middle of the migration."""
    er.async_get(hass).async_get_or_create(
        "sensor", "other", "u1", suggested_object_id="registered"
    )
    hass.states.async_set("sensor.with_state", "1")
    hass.states.async_reserve("sensor.reserved")
    assert free_entity_id(hass, "sensor.free") == "sensor.free"
    assert free_entity_id(hass, "sensor.registered") == "sensor.registered_2"
    assert free_entity_id(hass, "sensor.with_state") == "sensor.with_state_2"
    assert free_entity_id(hass, "sensor.planned", {"sensor.planned"}) == "sensor.planned_2"
    assert free_entity_id(hass, "sensor.reserved") == "sensor.reserved_2"


# --- Registry, adoption and notification -----------------------------------------


@pytest.fixture
def notify():
    with patch(
        "custom_components.bitpanda.migration.persistent_notification.async_create"
    ) as create:
        yield create


def _message(notify) -> str:
    notify.assert_called_once()
    return notify.call_args.args[1]


@pytest.fixture
def price_api():
    with patch(
        "custom_components.bitpanda.api.BitpandaApiClient.async_get_ticker",
        AsyncMock(return_value={"price": "100.00000000"}),
    ), patch(
        "custom_components.bitpanda.price_coordinator.async_fetch_ecb_rates",
        AsyncMock(return_value=EcbRates(date="2026-09-24", rates={"USD": 2.0})),
    ):
        yield


def _legacy_device(hass, entry, kind: str) -> str:
    names = {"wallets": "Bitpanda Wallets", "price_tracker": "Bitpanda Price Tracker"}
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_{kind}")},
        name=names[kind],
    ).id


def _legacy_entity(hass, entry, unique_id: str, object_id: str, device_id=None) -> str:
    return er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, unique_id, config_entry=entry, device_id=device_id,
        suggested_object_id=object_id,
    ).entity_id


async def test_wallets_are_rekeyed_and_default_ids_renamed(hass, legacy_api, no_setup, notify):
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC", "commodity_metal_XAU", "index_index_BCI5"])
    device = _legacy_device(hass, entry, "wallets")
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet", device)
    _legacy_entity(hass, entry, f"{eid}_wallet_commodity_metal_XAU", "bitpanda_wallets_xau_wallet_2", device)
    _legacy_entity(hass, entry, f"{eid}_wallet_index_index_BCI5", "my_index", device)

    assert await async_migrate_entry(hass, entry)

    ent_reg = er.async_get(hass)
    btc = ent_reg.async_get("sensor.bitpanda_bitcoin_btc_wallet")
    assert btc.unique_id == f"{eid}_wallet_{BTC_ID}"
    assert btc.device_id is None
    # A "_2" suffix still counts as the legacy default.
    assert ent_reg.async_get("sensor.bitpanda_gold_xau_wallet").unique_id == f"{eid}_wallet_{GOLD_ID}"
    # A user's own ID is kept; only the unique_id moves.
    assert ent_reg.async_get("sensor.my_index").unique_id == f"{eid}_wallet_{BCI5_ID}"
    assert dr.async_get(hass).async_get(device) is None
    message = _message(notify)
    assert "`sensor.bitpanda_wallets_btc_wallet` → `sensor.bitpanda_bitcoin_btc_wallet`" in message
    assert "sensor.my_index" not in message


def _by_symbol_or_id(**kwargs):
    """/assets as the migration (by symbol) and the Portfolio (by id) ask it."""
    return [
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == kwargs.get("symbol") or a["id"] == kwargs.get("asset_id")
    ]


def _position(asset_id: str, value: str) -> dict:
    return {
        "asset_id": asset_id,
        "balance": {"value": "1.00000000"},
        "available_balance": {"value": "1.00000000"},
        "currency_balance": {"value": value},
    }


async def test_a_migrated_install_ends_with_its_wallets_in_groups(hass, legacy_api, notify):
    """The upgrade end to end: the migration, then the Portfolio's first
    setup. The wallets the migration re-keyed move into the groups of their
    asset types; the Portfolio's own sensors, and a legacy wallet it left
    alone together with its device, stay outside every group."""
    _, assets = legacy_api
    assets.side_effect = _by_symbol_or_id
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC", "commodity_metal_XAU", "cryptocoin_GONE"])
    device = _legacy_device(hass, entry, "wallets")
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet", device)
    _legacy_entity(
        hass, entry, f"{eid}_wallet_commodity_metal_XAU", "bitpanda_wallets_xau_wallet", device
    )
    gone = _legacy_entity(
        hass, entry, f"{eid}_wallet_cryptocoin_GONE", "bitpanda_wallets_gone_wallet", device
    )
    _legacy_entity(hass, entry, f"{eid}_portfolio_total", "bitpanda_wallets_portfolio_total", device)
    portfolio = [
        _position(BTC_ID, "50000.00"),
        _position(GOLD_ID, "3000.00"),
        {"currency_id": _EUR_ID, "balance": {"value": "10.00"}},
    ]
    with patch(f"{_API}async_get_portfolio", AsyncMock(return_value=portfolio)), patch(
        f"{_API}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": "1.5"})
    ), patch(f"{_API}async_get_earn_configs", AsyncMock(return_value=[])), patch(
        f"{_API}async_get_operations", AsyncMock(return_value=[])
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert (entry.version, entry.state) == (3, ConfigEntryState.LOADED)
    groups = {sub.unique_id: sub for sub in entry.subentries.values()}
    assert {category: group.title for category, group in groups.items()} == {
        "crypto": "Cryptocurrencies",
        "metal": "Precious metals",
    }
    ent_reg = er.async_get(hass)
    btc = ent_reg.async_get("sensor.bitpanda_bitcoin_btc_wallet")
    gold = ent_reg.async_get("sensor.bitpanda_gold_xau_wallet")
    assert (btc.unique_id, btc.config_subentry_id) == (
        f"{eid}_wallet_{BTC_ID}", groups["crypto"].subentry_id,
    )
    assert (gold.unique_id, gold.config_subentry_id) == (
        f"{eid}_wallet_{GOLD_ID}", groups["metal"].subentry_id,
    )
    total = ent_reg.async_get("sensor.bitpanda_portfolio_total")
    assert (total.unique_id, total.config_subentry_id) == (f"{eid}_portfolio_total", None)
    left = ent_reg.async_get(gone)
    assert (left.config_subentry_id, left.device_id) == (None, device)
    assert all(
        device not in {d.id for d in subentry_devices(hass, eid, group.subentry_id)}
        for group in groups.values()
    )


async def test_the_fiat_wallet_of_the_entry_currency_becomes_portfolio_cash(
    hass, legacy_api, no_setup, notify
):
    entry = _v1_entry(hass, wallets=["fiat_EUR", "fiat_USD"])
    device = _legacy_device(hass, entry, "wallets")
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_fiat_EUR", "bitpanda_wallets_eur_wallet", device)
    usd = _legacy_entity(hass, entry, f"{eid}_wallet_fiat_USD", "bitpanda_wallets_usd_wallet", device)

    assert await async_migrate_entry(hass, entry)

    ent_reg = er.async_get(hass)
    assert ent_reg.async_get("sensor.bitpanda_portfolio_cash").unique_id == f"{eid}_portfolio_cash"
    assert ent_reg.async_get(usd).unique_id == f"{eid}_wallet_fiat_USD"
    # Still holds the USD wallet: the legacy device stays.
    assert dr.async_get(hass).async_get(device) is not None
    assert f"`{usd}`" in _message(notify)


async def test_the_only_fiat_wallet_becomes_portfolio_cash_whatever_its_currency(
    hass, legacy_api, no_setup, notify
):
    entry = _v1_entry(hass, wallets=["fiat_USD"])
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_fiat_USD", "bitpanda_wallets_usd_wallet")
    assert await async_migrate_entry(hass, entry)
    assert er.async_get(hass).async_get("sensor.bitpanda_portfolio_cash").unique_id == f"{eid}_portfolio_cash"


async def test_portfolio_total_keeps_its_unique_id_and_gets_the_new_id(hass, legacy_api, no_setup, notify):
    entry = _v1_entry(hass)
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_portfolio_total", "bitpanda_wallets_portfolio_total")
    assert await async_migrate_entry(hass, entry)
    total = er.async_get(hass).async_get("sensor.bitpanda_portfolio_total")
    assert total.unique_id == f"{eid}_portfolio_total"


async def test_an_unresolvable_wallet_is_left_alone_and_listed(hass, legacy_api, no_setup, notify):
    entry = _v1_entry(hass, wallets=["cryptocoin_GONE"])
    eid = entry.entry_id
    gone = _legacy_entity(hass, entry, f"{eid}_wallet_cryptocoin_GONE", "bitpanda_wallets_gone_wallet")
    assert await async_migrate_entry(hass, entry)
    assert er.async_get(hass).async_get(gone).unique_id == f"{eid}_wallet_cryptocoin_GONE"
    assert f"`{gone}`: GONE no longer exists at Bitpanda" in _message(notify)


async def test_a_wallet_prefix_decides_between_legacy_types(hass, legacy_api, no_setup, notify):
    """A wallet id's category prefix, not just its bare symbol, drives resolution.

    "TWIN" alone is ambiguous between a coin and a metal of the same symbol;
    only the `commodity_metal_` prefix (via `legacy_prefix` and `pick_legacy`)
    picks the metal instead of the coin.
    """
    _, assets = legacy_api
    assets.side_effect = lambda **kwargs: (
        [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "symbol": "TWIN",
                "name": "Twin Coin",
                "type": "cryptocoin",
                "group": "coin",
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "symbol": "TWIN",
                "name": "Twin Metal",
                "type": "commodity",
                "group": "metal",
            },
        ]
        if kwargs.get("symbol") == "TWIN"
        else []
    )
    entry = _v1_entry(hass, wallets=["commodity_metal_TWIN"])
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_commodity_metal_TWIN", "bitpanda_wallets_twin_wallet")

    assert await async_migrate_entry(hass, entry)

    ent_reg = er.async_get(hass)
    assert ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{eid}_wallet_22222222-2222-2222-2222-222222222222"
    ) == "sensor.bitpanda_twin_metal_twin_wallet"


async def test_legacy_price_sensors_move_to_the_price_tracker(hass, legacy_api, price_api, notify):
    entry = _v1_entry(hass, currency="USD", assets=["BTC"])
    device = _legacy_device(hass, entry, "price_tracker")
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_BTC_price_USD", "bitpanda_price_tracker_btc_usd", device)

    assert await async_migrate_entry(hass, entry)
    await hass.async_block_till_done()

    [tracker] = _price_trackers(hass)
    [group] = tracker.subentries.values()
    ent_reg = er.async_get(hass)
    moved = ent_reg.async_get("sensor.bitpanda_bitcoin_btc_usd")
    assert moved.config_entry_id == tracker.entry_id
    assert moved.config_subentry_id == group.subentry_id
    assert moved.unique_id == f"{tracker.entry_id}_{BTC_ID}_price_USD"
    # The adopted entity IS the live USD sensor: no "_2" twin beside it.
    assert ent_reg.async_get("sensor.bitpanda_bitcoin_btc_usd_2") is None
    assert float(hass.states.get("sensor.bitpanda_bitcoin_btc_usd").state) == 200.0
    assert "legacy_adopt" not in tracker.data
    assert dr.async_get(hass).async_get(device) is None
    assert (
        "`sensor.bitpanda_price_tracker_btc_usd` → `sensor.bitpanda_bitcoin_btc_usd`"
        in _message(notify)
    )


async def test_each_legacy_price_sensor_moves_into_the_group_of_its_asset(
    hass, legacy_api, price_api, notify
):
    entry = _v1_entry(hass, assets=["BTC", "XAU"])
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur")
    _legacy_entity(hass, entry, f"{eid}_XAU_price_EUR", "bitpanda_price_tracker_xau_eur")

    assert await async_migrate_entry(hass, entry)
    await hass.async_block_till_done()

    [tracker] = _price_trackers(hass)
    groups = {s.unique_id: s.subentry_id for s in tracker.subentries.values()}
    ent_reg = er.async_get(hass)
    btc = ent_reg.async_get("sensor.bitpanda_bitcoin_btc_eur")
    gold = ent_reg.async_get("sensor.bitpanda_gold_xau_eur")
    assert (btc.config_subentry_id, btc.unique_id) == (
        groups["crypto"], f"{tracker.entry_id}_{BTC_ID}_price_EUR",
    )
    assert (gold.config_subentry_id, gold.unique_id) == (
        groups["metal"], f"{tracker.entry_id}_{GOLD_ID}_price_EUR",
    )


async def test_adoption_skips_an_entity_whose_asset_no_group_tracks(hass):
    """The import only adopts what it tracks; should the two ever disagree,
    the legacy entity stays where it is."""
    source = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    source.add_to_hass(hass)
    sid = source.entry_id
    btc = _legacy_entity(hass, source, f"{sid}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur")
    gold = _legacy_entity(hass, source, f"{sid}_XAU_price_EUR", "bitpanda_price_tracker_xau_eur")
    items = [
        {"entity_id": btc, "unique_id": f"{sid}_BTC_price_EUR", "asset_id": BTC_ID,
         "currency": "EUR", "new_entity_id": None},
        {"entity_id": gold, "unique_id": f"{sid}_XAU_price_EUR", "asset_id": GOLD_ID,
         "currency": "EUR", "new_entity_id": None},
    ]
    tracker = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={"entry_type": "price_tracker",
              "legacy_adopt": {"source_entry_id": sid, "entities": items}},
        options={"extra_currencies": []},
        subentries_data=[price_group("crypto", *_by_symbol(symbol="BTC"))],
    )
    tracker.add_to_hass(hass)

    async_adopt_legacy_prices(hass, tracker)

    ent_reg = er.async_get(hass)
    [group] = tracker.subentries.values()
    adopted = ent_reg.async_get(btc)
    assert (adopted.config_entry_id, adopted.config_subentry_id) == (
        tracker.entry_id, group.subentry_id,
    )
    left = ent_reg.async_get(gold)
    assert (left.config_entry_id, left.unique_id) == (sid, f"{sid}_XAU_price_EUR")


async def test_an_unresolvable_price_is_left_alone_and_listed(hass, legacy_api, no_setup, notify):
    entry = _v1_entry(hass, assets=["GONE"])
    old = _legacy_entity(hass, entry, f"{entry.entry_id}_GONE_price_EUR", "bitpanda_price_tracker_gone_eur")
    assert await async_migrate_entry(hass, entry)
    assert _price_trackers(hass) == []
    assert er.async_get(hass).async_get(old).config_entry_id == entry.entry_id
    assert f"`{old}`" in _message(notify)


async def test_an_existing_price_tracker_does_not_block_the_migration(
    hass, legacy_api, no_setup, notify
):
    MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="price_tracker",
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": []},
    ).add_to_hass(hass)
    entry = _v1_entry(hass, assets=["BTC"])
    eid = entry.entry_id
    old = _legacy_entity(hass, entry, f"{eid}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur")

    assert await async_migrate_entry(hass, entry)
    assert entry.version == 3

    reg_entry = er.async_get(hass).async_get(old)
    # Untouched: still belongs to the v1 entry (now the Portfolio), under its
    # legacy unique_id -- nothing adopted it, because no Price Tracker entry
    # was ever created for this migration to hand it to.
    assert reg_entry.config_entry_id == eid
    assert reg_entry.unique_id == f"{eid}_BTC_price_EUR"
    assert f"`{old}`: a Price Tracker was already set up" in _message(notify)


async def test_a_failed_price_tracker_import_changes_nothing(hass, legacy_api, no_setup):
    entry = _v1_entry(hass, assets=["BTC"], wallets=["cryptocoin_BTC"])
    eid = entry.entry_id
    device = _legacy_device(hass, entry, "wallets")
    wallet = _legacy_entity(
        hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet", device
    )
    with patch.object(
        hass.config_entries.flow,
        "async_init",
        AsyncMock(
            return_value={"type": data_entry_flow.FlowResultType.ABORT, "reason": "unknown"}
        ),
    ):
        assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1
    assert dict(entry.options) == {"tracked_assets": ["BTC"], "tracked_wallets": ["cryptocoin_BTC"]}
    assert _price_trackers(hass) == []

    # The registry rewrite must not have run either: a failed import leaves
    # the whole entry -- registry included -- exactly as it was.
    reg_entry = er.async_get(hass).async_get(wallet)
    assert reg_entry.unique_id == f"{eid}_wallet_cryptocoin_BTC"
    assert reg_entry.entity_id == "sensor.bitpanda_wallets_btc_wallet"
    assert reg_entry.device_id == device
    assert dr.async_get(hass).async_get(device) is not None


async def test_the_notification_text_is_also_logged_once(
    hass, legacy_api, no_setup, notify, caplog
):
    """A persistent notification lives in memory only; the log keeps the
    old -> new mapping across a restart."""
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC", "cryptocoin_GONE"])
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet")
    gone = _legacy_entity(
        hass, entry, f"{eid}_wallet_cryptocoin_GONE", "bitpanda_wallets_gone_wallet"
    )

    assert await async_migrate_entry(hass, entry)

    warnings = [
        record for record in caplog.records
        if record.name == "custom_components.bitpanda.migration"
        and record.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    logged = warnings[0].getMessage()
    assert "`sensor.bitpanda_wallets_btc_wallet` → `sensor.bitpanda_bitcoin_btc_wallet`" in logged
    assert f"`{gone}`: GONE no longer exists at Bitpanda" in logged
    assert logged == _message(notify)
    assert "legacy-key" not in caplog.text


async def test_the_notification_asks_for_a_new_key(hass, legacy_api, no_setup, notify):
    assert await async_migrate_entry(hass, _v1_entry(hass))
    message = _message(notify)
    assert "https://app.bitpanda.com/my-account/apikey" in message
    assert "Earn (Read)" in message
    assert notify.call_args.kwargs["notification_id"] == "bitpanda_migration"


async def test_an_interrupted_migration_can_run_again(hass, legacy_api, no_setup, notify):
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet")
    assert await async_migrate_entry(hass, entry)
    # As if the version bump had never been saved.
    hass.config_entries.async_update_entry(
        entry, version=1, data={"api_key": "legacy-key", "currency": "EUR"},
        options={"tracked_assets": [], "tracked_wallets": ["cryptocoin_BTC"]},
    )
    notify.reset_mock()
    assert await async_migrate_entry(hass, entry)
    wallet = er.async_get(hass).async_get("sensor.bitpanda_bitcoin_btc_wallet")
    assert wallet.unique_id == f"{eid}_wallet_{BTC_ID}"
    assert "Not migrated" not in _message(notify)


async def test_an_empty_currency_list_aborts_the_migration(hass, legacy_api, no_setup):
    """An empty (or EUR-less) /currencies answer must not fall back to EUR.

    Such an answer means the list itself cannot be trusted, so the migration
    aborts with nothing changed and retries at the next start, exactly like a
    rate limit or any other API error.
    """
    currencies, _ = legacy_api
    currencies.return_value = []
    entry = _v1_entry(hass)
    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1
    assert dict(entry.options) == {"tracked_assets": [], "tracked_wallets": []}
    assert _price_trackers(hass) == []
