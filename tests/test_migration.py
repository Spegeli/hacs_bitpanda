"""Tests for v1 to v3 config entry migration."""
from unittest.mock import ANY, AsyncMock, patch

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.migration import (
    async_migrate_entry,
    legacy_prefix,
    legacy_symbol,
)

from tests.conftest import load_fixture

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
    # XAU is both the GoldMoney stock and the Gold metal; the legacy API only
    # ever tracked the metal.
    assert sorted(s.title for s in tracker.subentries.values()) == ["Bitcoin (BTC)", "Gold (XAU)"]


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
    (moved into migration.py's own `_resolve`, since `AssetResolver` -- which
    used to carry it -- is gone), an empty `symbol` would drop the query
    filter entirely and page through the whole ~14,000-asset catalogue
    instead of finding nothing. Replaces the deleted resolver test's coverage
    of the same guard.
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
