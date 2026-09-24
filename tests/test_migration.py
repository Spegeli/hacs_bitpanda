"""Tests for v1 to v2 config entry migration."""
from unittest.mock import AsyncMock, patch

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda import async_migrate_entry, legacy_symbol, v2_unique_id
from custom_components.bitpanda.api import BitpandaAuthError, BitpandaRateLimitError
from custom_components.bitpanda.const import DOMAIN

from tests.conftest import load_fixture

_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"


def _asset(symbol: str, asset_id: str) -> dict:
    return {
        "id": asset_id,
        "symbol": symbol,
        "name": symbol,
        "type": "cryptocoin",
        "group": "coin",
    }


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


def test_legacy_symbol_from_two_part_id():
    assert legacy_symbol("fiat_EUR") == "EUR"
    assert legacy_symbol("index_BCI5") == "BCI5"


def test_legacy_symbol_from_three_part_id():
    assert legacy_symbol("commodity_metal_XAU") == "XAU"
    assert legacy_symbol("index_wallet_BCI5") == "BCI5"


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
        v2_unique_id("eid_wallet_index_BCI5", "eid", {}, {"index_BCI5": "uuid-bci5"})
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
    assert entry.options["asset_cache"]["BTC"]["id"] == "uuid-btc"
    assert entry.options["asset_cache"]["ETH"]["id"] == "uuid-eth"
    assert "EUR" not in entry.options["asset_cache"]


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
        tracked_wallets=["cryptocoin_BTC", "index_BCI5"],
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
        f"{eid}_wallet_index_BCI5",
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
            {"BTC": _asset("BTC", "uuid-btc"), "BCI5": _asset("BCI5", "uuid-bci5")}
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
    """Contrived: version-2 entities are only ever created by setup, which
    runs after migration, so a live installation cannot hit this on its first
    migration. But `async_update_entity` raises ValueError on a colliding
    unique_id, and letting that escape would crash migration for one odd
    installation for no benefit -- the collision guard must catch it first.
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
