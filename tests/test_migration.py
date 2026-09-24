"""Tests for v1 to v2 config entry migration."""
from unittest.mock import AsyncMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda import async_migrate_entry, legacy_symbol
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
