"""Tests for v1 to v2 config entry migration."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda import (
    async_migrate_entry,
    legacy_prefix,
    legacy_symbol,
    v2_unique_id,
)
from custom_components.bitpanda.api import BitpandaAuthError, BitpandaRateLimitError
from custom_components.bitpanda.const import DOMAIN

from tests.conftest import load_fixture

_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"


def _asset(
    symbol: str, asset_id: str, type_: str = "cryptocoin", group: str = "coin"
) -> dict:
    return {
        "id": asset_id,
        "symbol": symbol,
        "name": symbol,
        "type": type_,
        "group": group,
    }


def _index_asset(symbol: str, asset_id: str) -> dict:
    return _asset(symbol, asset_id, type_="index", group="index")


def _v1_entry(**option_overrides) -> MockConfigEntry:
    """A config entry shaped like a genuine pre-migration install.

    Version 1 never had an asset_cache or a currency_id -- both are new in
    version 2, so this deliberately leaves them out rather than pre-filling
    them the way `tests/test_config_flow.py`'s v2 helper does.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={"api_key": "key", "currency": "EUR"},
        options={
            "tracked_assets": [],
            "tracked_wallets": [],
            **option_overrides,
        },
    )


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
    than being misparsed into a wrong symbol (see task-16-report.md, check 3).
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


# --- v2_unique_id --------------------------------------------------------------
#
# Pure mapping from a version 1 entity unique_id to its version 2 form. No
# Home Assistant object involved, so these pin the string surgery directly:
# the wallet check must run before the price check, `rpartition` must survive
# a symbol containing an underscore, and anything that is not a price or
# wallet unique_id -- notably the portfolio sensor's -- must come back as
# None so the caller leaves it alone.


def test_v2_unique_id_maps_crypto_wallet():
    assert (
        v2_unique_id(
            "eid_wallet_cryptocoin_BTC", "eid", {}, {"cryptocoin_BTC": "uuid-btc"}
        )
        == "eid_wallet_uuid-btc"
    )


def test_v2_unique_id_maps_index_wallet():
    assert (
        v2_unique_id(
            "eid_wallet_index_index_BCI5",
            "eid",
            {},
            {"index_index_BCI5": "uuid-bci5"},
        )
        == "eid_wallet_uuid-bci5"
    )


def test_v2_unique_id_maps_price_sensor():
    assert (
        v2_unique_id("eid_BTC_price_EUR", "eid", {"BTC": "uuid-btc"}, {})
        == "eid_uuid-btc_price_EUR"
    )


def test_v2_unique_id_of_portfolio_sensor_is_none():
    """The portfolio sensor's unique_id is unchanged across versions -- there
    is nothing to map it to, so it must come back None rather than being
    mistaken for an unresolvable price or wallet id.
    """
    assert v2_unique_id("eid_portfolio_total", "eid", {}, {}) is None


def test_v2_unique_id_of_wallet_not_in_map_is_none():
    assert (
        v2_unique_id(
            "eid_wallet_fiat_EUR", "eid", {}, {"cryptocoin_BTC": "uuid-btc"}
        )
        is None
    )


def test_v2_unique_id_of_other_config_entry_is_none():
    assert (
        v2_unique_id("othereid_BTC_price_EUR", "eid", {"BTC": "uuid-btc"}, {}) is None
    )


def test_v2_unique_id_wallet_prefix_miss_falls_through_to_price_pattern():
    """Carried from task-18-fix1-review.md, finding 1: a wallet-prefix match
    is not proof the id was ever a wallet. A price sensor whose asset symbol
    itself begins with the literal substring "wallet_" forms a unique_id that
    also starts with "{entry_id}_wallet_" -- the wallet branch used to return
    None outright on a wallet_map miss, silently dropping this price sensor
    from migration instead of falling through to the price pattern that
    actually resolves it. Real-world likelihood is nil (Bitpanda's tickers
    are short and uppercase), but correct by construction costs two lines.
    """
    assert (
        v2_unique_id(
            "eid_wallet_XYZ_price_EUR", "eid", {"wallet_XYZ": "uuid-x"}, {}
        )
        == "eid_uuid-x_price_EUR"
    )


# --- async_migrate_entry -----------------------------------------------------
#
# async_migrate_entry runs once against a real installation's only copy of
# its configuration. These pin: symbols resolving to ids, an unresolvable
# entry being dropped rather than aborting the whole migration, the version
# actually reaching 2, a wallet id that was already a bare symbol, and -- the
# dangerous part -- that an auth or rate-limit error during resolution aborts
# with the entry completely untouched instead of partially rewriting it.


async def test_migrate_entry_is_a_noop_at_current_version(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={"api_key": "key", "currency": "EUR", "currency_id": _EUR_ID},
        options={"tracked_assets": [], "tracked_wallets": [], "asset_cache": {}},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(side_effect=AssertionError("must not call the API")),
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert entry.version == 2


async def test_migrate_entry_resolves_ids_drops_unresolvable_and_bumps_version(hass):
    entry = _v1_entry(
        tracked_assets=["BTC"],
        tracked_wallets=["cryptocoin_ETH", "fiat_EUR"],
    )
    entry.add_to_hass(hass)

    def _get_assets(*, symbol=None, asset_id=None, page_size=100):
        return {
            "BTC": [_asset("BTC", "uuid-btc")],
            "ETH": [_asset("ETH", "uuid-eth")],
            # EUR is a currency, not a tradable asset -- the real API has no
            # /assets record for it, so this stays unresolved on purpose.
        }.get(symbol, [])

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        AsyncMock(side_effect=_get_assets),
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert entry.version == 2
    assert entry.data["currency_id"] == _EUR_ID
    assert entry.options["tracked_assets"] == ["uuid-btc"]
    # fiat_EUR could not be resolved and was dropped; ETH still made it
    # through -- one bad entry must not abort the others.
    assert entry.options["tracked_wallets"] == ["uuid-eth"]
    assert entry.options["asset_cache"]["uuid-btc"]["id"] == "uuid-btc"
    assert entry.options["asset_cache"]["uuid-eth"]["id"] == "uuid-eth"
    # EUR is a currency, not a tradable asset -- it was never resolved, so
    # nothing about it was ever cached.
    assert all(
        a.get("symbol") != "EUR" for a in entry.options["asset_cache"].values()
    )


async def test_migrate_entry_resolves_a_wallet_already_stored_as_bare_symbol(hass):
    """`legacy_symbol` returns an already-bare id unchanged, so a v1
    `tracked_wallets` entry with no recognised prefix resolves exactly like a
    `tracked_assets` entry would (see task-16-report.md, check 3).
    """
    entry = _v1_entry(tracked_wallets=["BTC"])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        AsyncMock(return_value=[_asset("BTC", "uuid-btc")]),
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert entry.options["tracked_wallets"] == ["uuid-btc"]


async def test_migrate_entry_aborts_on_auth_error_and_leaves_entry_untouched(hass):
    entry = _v1_entry(tracked_assets=["BTC"])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(side_effect=BitpandaAuthError("nope")),
    ):
        assert await async_migrate_entry(hass, entry) is False

    assert entry.version == 1
    assert "currency_id" not in entry.data
    assert entry.options["tracked_assets"] == ["BTC"]


async def test_migrate_entry_aborts_on_rate_limit_mid_resolution_and_leaves_entry_untouched(
    hass,
):
    entry = _v1_entry(tracked_assets=["BTC", "ETH"])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        AsyncMock(
            side_effect=[
                [_asset("BTC", "uuid-btc")],
                BitpandaRateLimitError("slow down"),
            ]
        ),
    ):
        assert await async_migrate_entry(hass, entry) is False

    # BTC would have resolved (its call already succeeded in-memory) but
    # ETH's rate limit aborts the whole attempt -- nothing is persisted, not
    # even the part that already succeeded. There is no second attempt if
    # this drops something it should have kept, so a half-written entry is
    # worse than an untouched one.
    assert entry.version == 1
    assert "currency_id" not in entry.data
    assert entry.options["tracked_assets"] == ["BTC", "ETH"]


# --- async_migrate_entry: entity registry -------------------------------------
#
# async_migrate_entry rewrites the config entry's stored identifiers, but the
# entity registry's unique_ids are a separate copy of the same identifiers
# (see task-18-fix1-brief.md). Left alone, every price and wallet entity would
# fail to match its version-2 unique_id on the next setup and Home Assistant
# would create a duplicate `_2` entity instead of reusing the existing one.
# These tests go through the real entity registry, not a mock, because the
# behaviour under test -- an entity_id surviving a unique_id change, and a
# collision being detected -- lives in Home Assistant's own registry code.


def _get_assets_by_symbol(assets: dict[str, dict]):
    """Build an async_get_assets(symbol=...) stand-in from a symbol->asset map."""

    def _get_assets(*, symbol=None, asset_id=None, page_size=100):
        return [assets[symbol]] if symbol in assets else []

    return AsyncMock(side_effect=_get_assets)


async def test_migrate_entry_updates_registry_unique_ids_and_preserves_entity_ids(
    hass,
):
    entry = _v1_entry(
        tracked_assets=["BTC"],
        tracked_wallets=["cryptocoin_BTC", "index_index_BCI5"],
    )
    entry.add_to_hass(hass)
    eid = entry.entry_id

    ent_reg = er.async_get(hass)
    price = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_BTC_price_EUR",
        config_entry=entry,
        suggested_object_id="btc_eur",
    )
    crypto_wallet = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_wallet_cryptocoin_BTC",
        config_entry=entry,
        suggested_object_id="btc_wallet",
    )
    index_wallet = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_wallet_index_index_BCI5",
        config_entry=entry,
        suggested_object_id="bci5_wallet",
    )
    portfolio = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_portfolio_total",
        config_entry=entry,
        suggested_object_id="portfolio_total",
    )
    # Entity_ids captured before migration -- preserving these is the whole
    # point of this test.
    price_entity_id = price.entity_id
    crypto_wallet_entity_id = crypto_wallet.entity_id
    index_wallet_entity_id = index_wallet.entity_id
    portfolio_entity_id = portfolio.entity_id

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        _get_assets_by_symbol(
            {
                "BTC": _asset("BTC", "uuid-btc"),
                "BCI5": _index_asset("BCI5", "uuid-bci5"),
            }
        ),
    ):
        assert await async_migrate_entry(hass, entry) is True

    updated_price = ent_reg.async_get(price_entity_id)
    assert updated_price is not None
    assert updated_price.entity_id == price_entity_id
    assert updated_price.unique_id == f"{eid}_uuid-btc_price_EUR"

    updated_crypto_wallet = ent_reg.async_get(crypto_wallet_entity_id)
    assert updated_crypto_wallet is not None
    assert updated_crypto_wallet.entity_id == crypto_wallet_entity_id
    assert updated_crypto_wallet.unique_id == f"{eid}_wallet_uuid-btc"

    updated_index_wallet = ent_reg.async_get(index_wallet_entity_id)
    assert updated_index_wallet is not None
    assert updated_index_wallet.entity_id == index_wallet_entity_id
    assert updated_index_wallet.unique_id == f"{eid}_wallet_uuid-bci5"

    # The portfolio sensor's unique_id does not change between versions --
    # v2_unique_id returns None for it, and it must be left exactly as is.
    updated_portfolio = ent_reg.async_get(portfolio_entity_id)
    assert updated_portfolio is not None
    assert updated_portfolio.entity_id == portfolio_entity_id
    assert updated_portfolio.unique_id == f"{eid}_portfolio_total"


async def test_migrate_entry_keeps_a_legacy_index_wallet(hass):
    """The issue-#7 users' case, end to end, in the exact form the legacy
    flow stored it: `index_index_BCI5`, from the index -> index nesting of
    the legacy /asset-wallets response. The migration runs once, so a wallet
    it drops here can never be restored by a later release.
    """
    bci5 = next(
        a for a in load_fixture("assets-sample.json") if a["symbol"] == "BCI5"
    )
    entry = _v1_entry(tracked_wallets=["index_index_BCI5"])
    entry.add_to_hass(hass)
    eid = entry.entry_id

    ent_reg = er.async_get(hass)
    wallet = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_wallet_index_index_BCI5",
        config_entry=entry,
        suggested_object_id="bci5_wallet",
    )
    entity_id = wallet.entity_id

    mock_get_assets = _get_assets_by_symbol({"BCI5": bci5})
    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        mock_get_assets,
    ):
        assert await async_migrate_entry(hass, entry) is True

    mock_get_assets.assert_called_once_with(symbol="BCI5")
    assert entry.version == 2
    assert entry.options["tracked_wallets"] == [bci5["id"]]
    assert entry.options["asset_cache"][bci5["id"]]["symbol"] == "BCI5"

    migrated = ent_reg.async_get(entity_id)
    assert migrated is not None
    assert migrated.entity_id == entity_id
    assert migrated.unique_id == f"{eid}_wallet_{bci5['id']}"


async def test_migrate_entry_leaves_unresolvable_wallet_registry_entry_in_place(hass):
    """Reuses the fiat_EUR case: EUR is a currency, not a tradable asset, so
    it never resolves and is dropped from tracked_wallets. Its registry entry
    must still exist afterwards -- deleting it would throw away the user's
    customisations (renamed entity_id, icon, area, disabled state) instead of
    just leaving the entity unavailable.
    """
    entry = _v1_entry(tracked_wallets=["fiat_EUR"])
    entry.add_to_hass(hass)
    eid = entry.entry_id

    ent_reg = er.async_get(hass)
    fiat_wallet = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_wallet_fiat_EUR",
        config_entry=entry,
        suggested_object_id="eur_wallet",
    )
    entity_id = fiat_wallet.entity_id

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        AsyncMock(return_value=[]),
    ):
        assert await async_migrate_entry(hass, entry) is True

    still_there = ent_reg.async_get(entity_id)
    assert still_there is not None
    assert still_there.entity_id == entity_id
    assert still_there.unique_id == f"{eid}_wallet_fiat_EUR"


async def test_migrate_entry_auth_abort_leaves_registry_byte_for_byte_unchanged(hass):
    entry = _v1_entry(tracked_assets=["BTC"])
    entry.add_to_hass(hass)
    eid = entry.entry_id

    ent_reg = er.async_get(hass)
    price = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_BTC_price_EUR",
        config_entry=entry,
        suggested_object_id="btc_eur",
    )
    entity_id = price.entity_id
    before = ent_reg.async_get(entity_id)

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(side_effect=BitpandaAuthError("nope")),
    ):
        assert await async_migrate_entry(hass, entry) is False

    after = ent_reg.async_get(entity_id)
    # RegistryEntry instances are immutable and replaced wholesale on any
    # update -- if migration had touched this entry, even to leave the
    # unique_id equal, `after` would no longer be the exact same object.
    assert after is before
    assert after.unique_id == f"{eid}_BTC_price_EUR"


async def test_migrate_entry_unique_id_collision_is_skipped_without_raising(hass):
    """Sets the collision up directly, via a pre-existing v2-form entity, as
    the simplest way to pin the guard -- but this is not only a "second
    migration" scenario: two distinct v1 identifiers resolving to the same
    UUID collide the exact same way inside a single, first-ever run, because
    `er.async_migrate_entries` applies each entity's update synchronously, so
    the second entity's collision check sees the first entity's
    just-migrated unique_id (see task-18-fix1-review.md, finding 3, and the
    end-to-end version of that scenario below). Either way,
    `async_update_entity` raises ValueError on a colliding unique_id, and
    letting that escape would crash migration for one odd installation for
    no benefit -- the collision guard must catch it first.
    """
    entry = _v1_entry(tracked_assets=["BTC"])
    entry.add_to_hass(hass)
    eid = entry.entry_id

    ent_reg = er.async_get(hass)
    legacy_price = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_BTC_price_EUR",
        config_entry=entry,
        suggested_object_id="btc_eur",
    )
    colliding = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_uuid-btc_price_EUR",
        config_entry=entry,
        suggested_object_id="btc_eur_2",
    )

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        _get_assets_by_symbol({"BTC": _asset("BTC", "uuid-btc")}),
    ):
        assert await async_migrate_entry(hass, entry) is True

    legacy_after = ent_reg.async_get(legacy_price.entity_id)
    assert legacy_after is not None
    assert legacy_after.unique_id == f"{eid}_BTC_price_EUR"

    colliding_after = ent_reg.async_get(colliding.entity_id)
    assert colliding_after is not None
    assert colliding_after.unique_id == f"{eid}_uuid-btc_price_EUR"


# --- async_migrate_entry: legacy symbol disambiguation ------------------------
#
# The live defect (task-23-brief.md): GET /assets?symbol=XAU returns the
# GoldMoney stock and the Gold metal, in an order that is not stable across
# symbols. The old `async_resolve` took `found[0]` -- sometimes the stock --
# silently pointing a migrated gold wallet at a stock nobody holds. These use
# the real committed fixture records (tests/fixtures/assets-sample.json), not
# synthesised ones, and force the stock first, exactly as measured live.


def _xau_stock() -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == "XAU" and a["type"] == "equity_security"
    )


def _xau_metal() -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == "XAU" and a["type"] == "commodity"
    )


async def test_migrate_entry_disambiguates_xau_wallet_and_price_stock_returned_first(
    hass,
):
    """A v1 entry tracking wallet `commodity_metal_XAU` and price tracker
    `XAU` must migrate both to the metal's UUID -- never the stock's -- even
    though the API hands back the stock first, and the registry step must
    rewrite both entities to that same UUID.
    """
    stock = _xau_stock()
    metal = _xau_metal()

    entry = _v1_entry(
        tracked_assets=["XAU"],
        tracked_wallets=["commodity_metal_XAU"],
    )
    entry.add_to_hass(hass)
    eid = entry.entry_id

    ent_reg = er.async_get(hass)
    price = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_XAU_price_EUR",
        config_entry=entry,
        suggested_object_id="xau_eur",
    )
    wallet = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_wallet_commodity_metal_XAU",
        config_entry=entry,
        suggested_object_id="xau_wallet",
    )
    price_entity_id = price.entity_id
    wallet_entity_id = wallet.entity_id

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        # Stock first -- the order that bit us live. Real /assets?symbol=
        # ignores the symbol filter argument in this stand-in and always
        # returns both XAU records, which is exactly what the real endpoint
        # does for this symbol.
        AsyncMock(return_value=[stock, metal]),
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert entry.options["tracked_assets"] == [metal["id"]]
    assert entry.options["tracked_wallets"] == [metal["id"]]
    assert entry.options["asset_cache"][metal["id"]]["id"] == metal["id"]
    assert stock["id"] not in entry.options["tracked_assets"]
    assert stock["id"] not in entry.options["tracked_wallets"]
    # Only the chosen (metal) record is persisted -- the unchosen stock
    # candidate must not ride along into the cache (task-23-review.md,
    # finding 9).
    assert stock["id"] not in entry.options["asset_cache"]

    updated_price = ent_reg.async_get(price_entity_id)
    assert updated_price.unique_id == f"{eid}_{metal['id']}_price_EUR"

    updated_wallet = ent_reg.async_get(wallet_entity_id)
    assert updated_wallet.unique_id == f"{eid}_wallet_{metal['id']}"


# --- async_migrate_entry: request budget (task-23-review.md, finding 9) ------


async def test_migrate_entry_memoises_candidates_for_a_symbol_tracked_twice(hass):
    """A symbol tracked as both a price tracker and a wallet must cost one
    /assets?symbol= request, not two.
    """
    entry = _v1_entry(
        tracked_assets=["BTC"],
        tracked_wallets=["cryptocoin_BTC"],
    )
    entry.add_to_hass(hass)

    mock_get_assets = AsyncMock(return_value=[_asset("BTC", "uuid-btc")])
    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        mock_get_assets,
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert entry.options["tracked_assets"] == ["uuid-btc"]
    assert entry.options["tracked_wallets"] == ["uuid-btc"]
    mock_get_assets.assert_called_once_with(symbol="BTC")


async def test_migrate_entry_never_requests_assets_for_a_fiat_wallet(hass):
    """A currency is not an /assets record -- pick_legacy always returns None
    for a fiat_ wallet -- so asking the API at all is a wasted request and a
    needless rate-limit exposure for a run that aborts on 429.
    """
    entry = _v1_entry(tracked_wallets=["fiat_EUR"])
    entry.add_to_hass(hass)

    mock_get_assets = AsyncMock(
        side_effect=AssertionError("must not call the API for a fiat wallet")
    )
    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        mock_get_assets,
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert entry.options["tracked_wallets"] == []


async def test_migrate_entry_wallet_prefix_narrows_a_synthetic_crypto_metal_collision(
    hass,
):
    """Synthetic collision (task-23-review.md, finding 12, mutation b3): the
    real catalogue has zero symbols shared between two legacy-supported
    types, so this pins that migration passes the wallet id's OWN category
    prefix, not `None`. Passing `None` here would see two legacy-supported
    survivors (the coin and the metal) and drop the wallet as ambiguous
    instead of resolving it to the coin.
    """
    entry = _v1_entry(tracked_wallets=["cryptocoin_DUP"])
    entry.add_to_hass(hass)

    crypto = _asset("DUP", "id-crypto", "cryptocoin", "coin")
    metal = _asset("DUP", "id-metal", "commodity", "metal")

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        AsyncMock(return_value=[crypto, metal]),
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert entry.options["tracked_wallets"] == ["id-crypto"]


# --- async_migrate_entry: partial-failure retry (Step 6b) ---------------------


async def test_migrate_entry_retries_fully_after_a_fault_mid_rewrite(hass):
    """Proves the ordering claim end-to-end with a genuinely half-migrated
    registry (task-23-review.md, finding 4 -- carried from
    task-18-fix1-review.md's finding 4, which this replaces): the fault is
    injected inside `er.async_migrate_entries`'s own per-entity loop, by
    making `EntityRegistry.async_update_entity` succeed once (so the first
    entity it visits really is rewritten to v2 form) and then raise (so the
    second is left genuinely untouched, still in v1 form) -- not by replacing
    `_migrate_entity_registry` wholesale, which would leave nothing migrated
    at all and never exercise retry idempotency for an already-migrated
    entity. The entry must stay at version 1 with nothing persisted, and a
    later, unfaulted call must then migrate every entity to its version-2
    form exactly once -- including the one call that visited an entity
    already in v2 form and had to leave it alone.
    """
    entry = _v1_entry(
        tracked_assets=["BTC"],
        tracked_wallets=["cryptocoin_ETH"],
    )
    entry.add_to_hass(hass)
    eid = entry.entry_id

    ent_reg = er.async_get(hass)
    price = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_BTC_price_EUR",
        config_entry=entry,
        suggested_object_id="btc_eur",
    )
    wallet = ent_reg.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{eid}_wallet_cryptocoin_ETH",
        config_entry=entry,
        suggested_object_id="eth_wallet",
    )
    price_entity_id = price.entity_id
    wallet_entity_id = wallet.entity_id
    v1_forms = {f"{eid}_BTC_price_EUR", f"{eid}_wallet_cryptocoin_ETH"}
    v2_forms = {f"{eid}_uuid-btc_price_EUR", f"{eid}_wallet_uuid-eth"}

    assets_by_symbol = _get_assets_by_symbol(
        {"BTC": _asset("BTC", "uuid-btc"), "ETH": _asset("ETH", "uuid-eth")}
    )

    real_update_entity = er.EntityRegistry.async_update_entity
    calls = {"count": 0}

    def _update_entity_succeeds_once_then_raises(self, entity_id, **changes):
        calls["count"] += 1
        if calls["count"] == 1:
            return real_update_entity(self, entity_id, **changes)
        raise RuntimeError("injected fault mid-rewrite")

    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        assets_by_symbol,
    ), patch.object(
        er.EntityRegistry,
        "async_update_entity",
        _update_entity_succeeds_once_then_raises,
    ):
        with pytest.raises(RuntimeError):
            await async_migrate_entry(hass, entry)

    # Exactly one call got through before the fault: one entity really is in
    # its new, version-2 form; the other is genuinely still in v1 form. Which
    # one depends only on the registry's own iteration order, not asserted.
    after_fault = {
        ent_reg.async_get(price_entity_id).unique_id,
        ent_reg.async_get(wallet_entity_id).unique_id,
    }
    assert len(after_fault & v1_forms) == 1
    assert len(after_fault & v2_forms) == 1

    # Registry runs before the entry is updated specifically so a failure
    # here leaves the entry itself completely untouched.
    assert entry.version == 1
    assert "currency_id" not in entry.data
    assert entry.options["tracked_assets"] == ["BTC"]
    assert entry.options["tracked_wallets"] == ["cryptocoin_ETH"]

    # Retried with no fault: migration completes, each entity exactly once --
    # the already-migrated one is left alone (v2_unique_id no longer matches
    # its v1 patterns), the other one is migrated fresh.
    with patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_currencies",
        AsyncMock(return_value=load_fixture("currencies.json")),
    ), patch(
        "custom_components.bitpanda.BitpandaApiClient.async_get_assets",
        assets_by_symbol,
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert entry.version == 2
    assert entry.options["tracked_assets"] == ["uuid-btc"]
    assert entry.options["tracked_wallets"] == ["uuid-eth"]
    assert ent_reg.async_get(price_entity_id).unique_id == f"{eid}_uuid-btc_price_EUR"
    assert ent_reg.async_get(wallet_entity_id).unique_id == f"{eid}_wallet_uuid-eth"
