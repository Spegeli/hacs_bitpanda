"""Tests for v1 to v3 config entry migration."""
from contextlib import contextmanager
import json
import logging
from pathlib import Path
import string
from unittest.mock import ANY, AsyncMock, patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda import migration
from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.ecb import EcbRates
from custom_components.bitpanda.migration import (
    UPGRADE_URL,
    async_adopt_legacy_prices,
    async_migrate_entry,
    free_entity_id,
    legacy_prefix,
    legacy_symbol,
)

from tests.conftest import device_names_in_subentry, load_fixture, price_group

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


# --- What the upgrade tells the user ------------------------------------------------
#
# Repair issues (Settings -> Repairs), which the frontend shows in each user's
# own language, and one English WARNING in the log with the full mapping.


def _issues(hass) -> dict[str, ir.IssueEntry]:
    """This integration's repair issues, by issue id."""
    return {
        issue_id: issue
        for (domain, issue_id), issue in ir.async_get(hass).issues.items()
        if domain == DOMAIN
    }


def _listed(hass, issue_id: str) -> str:
    """The Markdown list an entity issue carries, "" without the issue."""
    issue = _issues(hass).get(issue_id)
    return "" if issue is None else issue.translation_placeholders["entities"]


def _renamed(hass) -> str:
    return _listed(hass, "renamed_entities")


def _not_migrated(hass) -> str:
    return _listed(hass, "entities_not_migrated")


def _migration_warnings(caplog) -> list[str]:
    return [
        record.getMessage() for record in caplog.records
        if record.name == "custom_components.bitpanda.migration"
        and record.levelno == logging.WARNING
    ]


def _logged(caplog) -> str:
    """The migration's report: its one English WARNING about the upgrade.
    (The adoption may warn besides, about an entity it leaves alone.)"""
    [logged] = [
        message for message in _migration_warnings(caplog)
        if message.startswith("Bitpanda is now two services")
    ]
    return logged


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


@contextmanager
def _home_assistant(major: int, minor: int, version: str):
    """Run the migration as if on Home Assistant `version`."""
    with patch(f"{_MIGRATION}.MAJOR_VERSION", major), patch(
        f"{_MIGRATION}.MINOR_VERSION", minor
    ), patch(f"{_MIGRATION}.HA_VERSION", version):
        yield


@pytest.mark.parametrize("minor", [3, 4])
async def test_home_assistant_before_2025_5_leaves_the_entry_alone(
    hass, legacy_api, no_setup, caplog, minor
):
    """Only from Home Assistant 2025.5 on does the recorder move history along
    with an entity-ID rename made while Home Assistant starts -- when this
    migration runs. Before, every migrated entity would lose its history, so
    the migration refuses and changes nothing, not even with an API call.
    Nothing was upgraded, so nothing is reported as changed: the one repair
    issue asks to update Home Assistant."""
    currencies, assets = legacy_api
    entry = _v1_entry(hass, assets=["BTC"], wallets=["cryptocoin_BTC"])
    eid = entry.entry_id
    wallet = _legacy_entity(
        hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet"
    )
    with _home_assistant(2025, minor, f"2025.{minor}.0"):
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
    assert set(_issues(hass)) == {"home_assistant_too_old"}
    assert _migration_warnings(caplog) == []
    assert "Home Assistant 2025.5 or newer" in caplog.text
    assert "legacy-key" not in caplog.text


async def test_home_assistant_2025_5_migrates(hass, legacy_api, no_setup):
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    with _home_assistant(2025, 5, "2025.5.0"):
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


async def test_a_language_chosen_before_the_upgrade_is_kept(hass, legacy_api, no_setup):
    """Home Assistant offers Configure on every entry -- a version 1 entry
    still waiting for its migration too, which opens the Portfolio's form.
    A language saved there survives the migration; the tracked lists of
    version 1 do not."""
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "portfolio"
    await hass.config_entries.options.async_configure(result["flow_id"], {"language": "de"})
    assert dict(entry.options) == {
        "tracked_assets": [], "tracked_wallets": ["cryptocoin_BTC"], "language": "de",
    }

    assert await async_migrate_entry(hass, entry)

    assert dict(entry.options) == {"language": "de"}


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


async def test_a_rate_limit_changes_nothing(hass, legacy_api, no_setup, caplog):
    currencies, _ = legacy_api
    currencies.side_effect = BitpandaRateLimitError("Rate limited on /currencies")
    entry = _v1_entry(hass)
    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1
    assert (
        "Cannot migrate the Bitpanda config entry: rate limited by the Bitpanda API. "
        "Nothing has been changed; migration will be retried on the next restart."
    ) in caplog.text
    assert "legacy-key" not in caplog.text


def _portfolio_set_up_before(hass) -> MockConfigEntry:
    """A Portfolio the user set up while the version 1 entry still waited for
    its migration."""
    portfolio = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio"},
    )
    portfolio.add_to_hass(hass)
    return portfolio


async def test_an_existing_portfolio_blocks_the_migration(hass, legacy_api, no_setup):
    _portfolio_set_up_before(hass)
    entry = _v1_entry(hass)
    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1


# --- What blocks the upgrade ----------------------------------------------------------
#
# A version 1 entry is not upgraded while Home Assistant is older than 2025.5,
# or while a Portfolio is set up beside it. Each cause the user can remove is a
# repair issue: an error -- the entry stays as it was while it lasts -- raised
# again at every start while it lasts (not kept across restarts), and deleted
# as soon as it is gone. "Learn more" leads to the README's upgrade section.


def _blocker_attributes(issue: ir.IssueEntry) -> tuple:
    return (
        issue.severity, issue.is_fixable, issue.is_persistent, issue.learn_more_url,
        issue.issue_domain,
    )


_BLOCKER = (ir.IssueSeverity.ERROR, False, False, UPGRADE_URL, None)


@pytest.mark.parametrize("minor", [3, 4])
async def test_home_assistant_before_2025_5_asks_to_be_updated(
    hass, legacy_api, no_setup, minor
):
    """Naming the version needed and the version running -- nothing secret."""
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    with _home_assistant(2025, minor, f"2025.{minor}.2"):
        assert not await async_migrate_entry(hass, entry)
    issue = _issues(hass)["home_assistant_too_old"]
    assert (issue.translation_key, issue.translation_placeholders) == (
        "home_assistant_too_old", {"minimum": "2025.5", "version": f"2025.{minor}.2"}
    )
    assert _blocker_attributes(issue) == _BLOCKER


async def test_the_update_issue_goes_once_home_assistant_is_new_enough(
    hass, legacy_api, no_setup
):
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    with _home_assistant(2025, 4, "2025.4.2"):
        assert not await async_migrate_entry(hass, entry)
    assert "home_assistant_too_old" in _issues(hass)
    with _home_assistant(2025, 5, "2025.5.0"):
        assert await async_migrate_entry(hass, entry)
    assert "home_assistant_too_old" not in _issues(hass)


async def test_the_update_issue_goes_with_the_entry_it_is_about(hass, legacy_api, no_setup):
    """Deleted instead of upgraded: nothing is left to upgrade."""
    entry = _v1_entry(hass)
    with _home_assistant(2025, 4, "2025.4.2"):
        assert not await async_migrate_entry(hass, entry)
    entry.mock_state(hass, ConfigEntryState.MIGRATION_ERROR)
    await hass.config_entries.async_remove(entry.entry_id)
    assert _issues(hass) == {}


async def test_an_existing_portfolio_asks_to_delete_one_of_the_two_entries(
    hass, legacy_api, no_setup
):
    """Both named by their titles, as the integration page shows them --
    nothing secret. Nothing was upgraded, so nothing is reported as changed."""
    _portfolio_set_up_before(hass)
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    assert not await async_migrate_entry(hass, entry)
    issue = _issues(hass)["portfolio_exists"]
    assert (issue.translation_key, issue.translation_placeholders) == (
        "portfolio_exists", {"entry": "Bitpanda", "portfolio": "Bitpanda Portfolio"}
    )
    assert _blocker_attributes(issue) == _BLOCKER
    assert set(_issues(hass)) == {"portfolio_exists"}


@pytest.mark.parametrize("removed", ["old entry", "portfolio"])
async def test_deleting_either_entry_ends_the_portfolio_issue(
    hass, legacy_api, no_setup, removed
):
    """Either way one Portfolio is left, and the issue goes at once. The old
    entry, when kept, is upgraded at the next start -- as the issue says:
    Home Assistant cannot retry a failed migration before."""
    portfolio = _portfolio_set_up_before(hass)
    entry = _v1_entry(hass)
    assert not await async_migrate_entry(hass, entry)
    entry.mock_state(hass, ConfigEntryState.MIGRATION_ERROR)

    await hass.config_entries.async_remove(
        entry.entry_id if removed == "old entry" else portfolio.entry_id
    )

    assert "portfolio_exists" not in _issues(hass)


async def test_the_portfolio_issue_stays_while_both_entries_do(hass, legacy_api, no_setup):
    """Deleting another entry -- the Price Tracker -- leaves the conflict."""
    _portfolio_set_up_before(hass)
    tracker = _price_tracker_set_up_before(hass)
    entry = _v1_entry(hass)
    assert not await async_migrate_entry(hass, entry)

    await hass.config_entries.async_remove(tracker.entry_id)

    assert "portfolio_exists" in _issues(hass)


async def test_an_upgrade_that_runs_leaves_no_blocker_issue(hass, legacy_api, no_setup):
    """For example once the Portfolio was deleted and Home Assistant
    restarted: whatever blocked the upgrade before is gone."""
    for issue_id in migration.BLOCKER_ISSUES:
        ir.async_create_issue(
            hass, DOMAIN, issue_id, is_fixable=False, severity=ir.IssueSeverity.ERROR,
            translation_key=issue_id,
        )
    assert await async_migrate_entry(hass, _v1_entry(hass))
    assert _issues(hass) == {}


async def test_a_currency_no_longer_offered_falls_back_to_eur(hass, legacy_api, no_setup):
    entry = _v1_entry(hass, currency="JPY")
    assert await async_migrate_entry(hass, entry)
    assert entry.data["currency"] == "EUR"
    assert entry.data["currency_id"] == _EUR_ID


async def test_a_listed_currency_the_integration_does_not_support_falls_back_to_eur(
    hass, legacy_api, no_setup, caplog
):
    """Being on /currencies is not enough: the Portfolio reports only in the
    currencies it supports. The fallback is a repair issue of its own."""
    currencies, _ = legacy_api
    currencies.return_value = [*load_fixture("currencies.json"), {"symbol": "JPY", "id": "jpy"}]
    entry = _v1_entry(hass, currency="JPY")
    assert await async_migrate_entry(hass, entry)
    assert (entry.data["currency"], entry.data["currency_id"]) == ("EUR", _EUR_ID)
    issue = _issues(hass)["currency_dropped"]
    assert issue.translation_placeholders == {"currency": "JPY"}
    assert "JPY is not available for the Bitpanda Portfolio; it now reports in EUR." in _logged(
        caplog
    )


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


# --- Registry, adoption and what the user is told --------------------------------


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


async def test_wallets_are_rekeyed_and_default_ids_renamed(hass, legacy_api, no_setup):
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
    renamed = _renamed(hass)
    assert "- `sensor.bitpanda_wallets_btc_wallet` → `sensor.bitpanda_bitcoin_btc_wallet`" in renamed
    assert "sensor.my_index" not in renamed


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


async def test_a_migrated_install_ends_with_its_wallets_in_groups(hass, legacy_api):
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
    assert device_names_in_subentry(hass, eid, groups["crypto"].subentry_id) == {
        "Bitcoin (BTC) Wallet"
    }
    assert device_names_in_subentry(hass, eid, groups["metal"].subentry_id) == {
        "Gold (XAU) Wallet"
    }
    assert device_names_in_subentry(hass, eid, None) == {"Portfolio", "Bitpanda Wallets"}


async def test_the_fiat_wallet_of_the_entry_currency_becomes_portfolio_cash(
    hass, legacy_api, no_setup, caplog
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
    assert _not_migrated(hass) == f"- `{usd}`"
    assert f"- `{usd}`: Portfolio Cash now covers every fiat balance" in _logged(caplog)


async def test_the_only_fiat_wallet_becomes_portfolio_cash_whatever_its_currency(
    hass, legacy_api, no_setup
):
    entry = _v1_entry(hass, wallets=["fiat_USD"])
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_fiat_USD", "bitpanda_wallets_usd_wallet")
    assert await async_migrate_entry(hass, entry)
    assert er.async_get(hass).async_get("sensor.bitpanda_portfolio_cash").unique_id == f"{eid}_portfolio_cash"


async def test_portfolio_total_keeps_its_unique_id_and_gets_the_new_id(hass, legacy_api, no_setup):
    entry = _v1_entry(hass)
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_portfolio_total", "bitpanda_wallets_portfolio_total")
    assert await async_migrate_entry(hass, entry)
    total = er.async_get(hass).async_get("sensor.bitpanda_portfolio_total")
    assert total.unique_id == f"{eid}_portfolio_total"


async def test_an_unresolvable_wallet_is_left_alone_and_listed(
    hass, legacy_api, no_setup, caplog
):
    """Listed in the repair issue by its entity ID alone -- no English prose
    in a placeholder; the log names the reason."""
    entry = _v1_entry(hass, wallets=["cryptocoin_GONE"])
    eid = entry.entry_id
    gone = _legacy_entity(hass, entry, f"{eid}_wallet_cryptocoin_GONE", "bitpanda_wallets_gone_wallet")
    assert await async_migrate_entry(hass, entry)
    assert er.async_get(hass).async_get(gone).unique_id == f"{eid}_wallet_cryptocoin_GONE"
    assert _not_migrated(hass) == f"- `{gone}`"
    assert f"- `{gone}`: GONE no longer exists at Bitpanda" in _logged(caplog)


async def test_a_legacy_wallet_whose_asset_already_has_a_wallet_is_left_and_listed(
    hass, legacy_api, no_setup, caplog
):
    """Its new unique_id is taken already -- by an entity an earlier run
    re-keyed, say: the legacy wallet is left alone rather than collide."""
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    eid = entry.entry_id
    legacy = _legacy_entity(
        hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet"
    )
    _legacy_entity(hass, entry, f"{eid}_wallet_{BTC_ID}", "bitpanda_bitcoin_btc_wallet")

    assert await async_migrate_entry(hass, entry)

    left = er.async_get(hass).async_get(legacy)
    assert (left.unique_id, left.entity_id) == (
        f"{eid}_wallet_cryptocoin_BTC", "sensor.bitpanda_wallets_btc_wallet",
    )
    assert _not_migrated(hass) == f"- `{legacy}`"
    assert f"- `{legacy}`: another entity already stands for the same asset" in _logged(caplog)


async def test_a_wallet_prefix_decides_between_legacy_types(hass, legacy_api, no_setup):
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


async def test_legacy_price_sensors_move_to_the_price_tracker(hass, legacy_api, price_api):
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
        "- `sensor.bitpanda_price_tracker_btc_usd` → `sensor.bitpanda_bitcoin_btc_usd`"
        in _renamed(hass)
    )


def _adoption_preceded_by(prepare):
    """async_adopt_legacy_prices, with `prepare(hass, tracker)` run first:
    something that happens between the migration's plan and the adoption
    in the new Price Tracker's first setup."""
    adopt = migration.async_adopt_legacy_prices

    def _adopt(hass, tracker):
        prepare(hass, tracker)
        adopt(hass, tracker)

    return patch(f"{_MIGRATION}.async_adopt_legacy_prices", _adopt)


async def test_the_renamed_issue_reports_the_id_the_adoption_gave(hass, legacy_api, price_api):
    """The migration plans the new IDs; the Price Tracker adopts the
    entities later, in its own setup. Should the planned ID be taken by
    then, the entity gets the next free one -- and the repair issue names
    that one, not the plan."""
    entry = _v1_entry(hass, assets=["BTC"])
    legacy = _legacy_entity(
        hass, entry, f"{entry.entry_id}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur"
    )

    def _take_the_planned_id(hass, tracker):
        er.async_get(hass).async_get_or_create(
            "sensor", "other", "x", suggested_object_id="bitpanda_bitcoin_btc_eur"
        )

    with _adoption_preceded_by(_take_the_planned_id):
        assert await async_migrate_entry(hass, entry)
        await hass.async_block_till_done()

    [tracker] = _price_trackers(hass)
    adopted = er.async_get(hass).async_get("sensor.bitpanda_bitcoin_btc_eur_2")
    assert adopted.unique_id == f"{tracker.entry_id}_{BTC_ID}_price_EUR"
    assert _renamed(hass) == f"- `{legacy}` → `sensor.bitpanda_bitcoin_btc_eur_2`"


async def test_the_issues_list_a_price_entity_the_adoption_left(
    hass, legacy_api, price_api, caplog
):
    """Another entity already stands for the same price when the Price
    Tracker adopts: the legacy entity stays where it is, and it is listed
    as not migrated instead of renamed."""
    entry = _v1_entry(hass, assets=["BTC"])
    legacy = _legacy_entity(
        hass, entry, f"{entry.entry_id}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur"
    )

    def _take_the_price(hass, tracker):
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"{tracker.entry_id}_{BTC_ID}_price_EUR", config_entry=tracker,
            suggested_object_id="bitpanda_btc_elsewhere",
        )

    with _adoption_preceded_by(_take_the_price):
        assert await async_migrate_entry(hass, entry)
        await hass.async_block_till_done()

    left = er.async_get(hass).async_get(legacy)
    assert (left.config_entry_id, left.unique_id) == (entry.entry_id, f"{entry.entry_id}_BTC_price_EUR")
    assert "renamed_entities" not in _issues(hass)
    assert _not_migrated(hass) == f"- `{legacy}`"
    logged = _logged(caplog)
    assert f"`{legacy}` →" not in logged
    assert f"- `{legacy}`: another entity already stands for the same asset" in logged


async def test_the_issues_claim_no_rename_for_an_entity_gone_before_adoption(
    hass, legacy_api, price_api
):
    """The Price Tracker then creates its sensor afresh under the planned
    ID: nothing was renamed, and nothing is left to list."""
    entry = _v1_entry(hass, assets=["BTC"])
    legacy = _legacy_entity(
        hass, entry, f"{entry.entry_id}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur"
    )

    def _delete_it(hass, tracker):
        er.async_get(hass).async_remove(legacy)

    with _adoption_preceded_by(_delete_it):
        assert await async_migrate_entry(hass, entry)
        await hass.async_block_till_done()

    assert er.async_get(hass).async_get("sensor.bitpanda_bitcoin_btc_eur") is not None
    assert _issues(hass) == {}


async def test_each_legacy_price_sensor_moves_into_the_group_of_its_asset(
    hass, legacy_api, price_api
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


def _tracker_adopting(hass, source_id: str, *items: dict) -> MockConfigEntry:
    """A Price Tracker tracking BTC, set to adopt `items` on its first setup."""
    tracker = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={"entry_type": "price_tracker",
              "legacy_adopt": {"source_entry_id": source_id, "entities": list(items)}},
        options={"extra_currencies": []},
        subentries_data=[price_group("crypto", *_by_symbol(symbol="BTC"))],
    )
    tracker.add_to_hass(hass)
    return tracker


async def test_adoption_skips_an_entity_that_no_longer_exists(hass):
    """Deleted since the migration planned it: nothing to move, no error."""
    source = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    source.add_to_hass(hass)
    sid = source.entry_id
    tracker = _tracker_adopting(
        hass, sid,
        {"entity_id": "sensor.bitpanda_price_tracker_btc_eur", "unique_id": f"{sid}_BTC_price_EUR",
         "asset_id": BTC_ID, "currency": "EUR", "new_entity_id": "sensor.bitpanda_bitcoin_btc_eur"},
    )

    async_adopt_legacy_prices(hass, tracker)

    assert er.async_entries_for_config_entry(er.async_get(hass), tracker.entry_id) == []
    assert "legacy_adopt" not in tracker.data


async def test_adoption_leaves_a_legacy_entity_whose_price_is_already_taken(hass, caplog):
    """Another entity already stands for the same asset and currency: the
    legacy one stays where it is, and the log says so."""
    source = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    source.add_to_hass(hass)
    sid = source.entry_id
    legacy = _legacy_entity(hass, source, f"{sid}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur")
    tracker = _tracker_adopting(
        hass, sid,
        {"entity_id": legacy, "unique_id": f"{sid}_BTC_price_EUR", "asset_id": BTC_ID,
         "currency": "EUR", "new_entity_id": "sensor.bitpanda_bitcoin_btc_eur"},
    )
    taken = er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{tracker.entry_id}_{BTC_ID}_price_EUR", config_entry=tracker,
        suggested_object_id="bitpanda_bitcoin_btc_eur",
    ).entity_id

    async_adopt_legacy_prices(hass, tracker)

    left = er.async_get(hass).async_get(legacy)
    assert (left.config_entry_id, left.unique_id, left.entity_id) == (
        sid, f"{sid}_BTC_price_EUR", "sensor.bitpanda_price_tracker_btc_eur",
    )
    assert er.async_get(hass).async_get(taken).unique_id == f"{tracker.entry_id}_{BTC_ID}_price_EUR"
    assert f"Not adopting {legacy}" in caplog.text


async def test_an_unresolvable_price_is_left_alone_and_listed(hass, legacy_api, no_setup):
    entry = _v1_entry(hass, assets=["GONE"])
    old = _legacy_entity(hass, entry, f"{entry.entry_id}_GONE_price_EUR", "bitpanda_price_tracker_gone_eur")
    assert await async_migrate_entry(hass, entry)
    assert _price_trackers(hass) == []
    assert er.async_get(hass).async_get(old).config_entry_id == entry.entry_id
    assert _not_migrated(hass) == f"- `{old}`"


def _price_tracker_set_up_before(hass, *groups) -> MockConfigEntry:
    """A Price Tracker the user set up while the version 1 entry still waited
    for its migration."""
    tracker = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="price_tracker",
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": []},
        subentries_data=list(groups),
    )
    tracker.add_to_hass(hass)
    return tracker


async def test_an_existing_price_tracker_does_not_block_the_migration(
    hass, legacy_api, no_setup, caplog
):
    """The migration adopts into a Price Tracker it creates itself: with one
    set up already, the legacy price sensors stay where they are. A repair
    issue of its own names the assets to add there -- by their labels, the
    same in every language -- since the one the user has does not track
    them."""
    _price_tracker_set_up_before(hass)
    entry = _v1_entry(hass, assets=["BTC", "XAU"])
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
    assert _not_migrated(hass) == f"- `{old}`"
    assert _issues(hass)["price_tracker_exists"].translation_placeholders == {
        "assets": "- Bitcoin (BTC)\n- Gold (XAU)"
    }
    logged = _logged(caplog)
    assert f"- `{old}`: a Price Tracker was already set up\n" in logged
    assert (
        "A Bitpanda Price Tracker was already set up, so the prices tracked before the "
        "upgrade were not moved into it. Add these assets there to keep tracking them: "
        "Bitcoin (BTC), Gold (XAU)."
    ) in logged


async def test_an_existing_price_tracker_is_asked_to_add_only_what_it_lacks(
    hass, legacy_api, no_setup
):
    """An asset the Price Tracker tracks already is not named; when it
    tracks them all, there is nothing to add and no such issue."""
    _price_tracker_set_up_before(hass, price_group("crypto", *_by_symbol(symbol="BTC")))
    entry = _v1_entry(hass, assets=["BTC"])
    old = _legacy_entity(
        hass, entry, f"{entry.entry_id}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur"
    )

    assert await async_migrate_entry(hass, entry)

    assert "price_tracker_exists" not in _issues(hass)
    assert _not_migrated(hass) == f"- `{old}`"


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


def _upgrade_with_every_issue(hass) -> tuple[MockConfigEntry, str, str]:
    """A version 1 entry whose migration raises every repair issue there is:
    a renamed wallet; a wallet and a price sensor left alone; the currency
    fallback; and a Price Tracker set up before the upgrade, which does not
    track the asset whose price the entry tracked. Returns the entry and the
    entity IDs of the wallet and the price sensor left alone."""
    _price_tracker_set_up_before(hass)
    entry = _v1_entry(
        hass, currency="JPY", assets=["BTC"], wallets=["cryptocoin_BTC", "cryptocoin_GONE"]
    )
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet")
    gone = _legacy_entity(
        hass, entry, f"{eid}_wallet_cryptocoin_GONE", "bitpanda_wallets_gone_wallet"
    )
    price = _legacy_entity(hass, entry, f"{eid}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur")
    return entry, gone, price


async def test_the_upgrade_raises_exactly_the_repair_issues_that_apply(
    hass, legacy_api, no_setup
):
    """Renamed entity IDs, entities left alone, the currency fallback and the
    assets to add to a Price Tracker set up before, each an issue of its
    own; a list is a language-neutral Markdown list of entity IDs or asset
    labels. Informational (not fixable), kept across restarts until the user
    dismisses it, "Learn more" on the README's upgrade section. Nothing
    else: no persistent notification, and no issue for the new API key --
    Home Assistant's reauthentication dialog asks for it."""
    entry, gone, price = _upgrade_with_every_issue(hass)

    with patch("homeassistant.components.persistent_notification.async_create") as notification:
        assert await async_migrate_entry(hass, entry)

    notification.assert_not_called()
    issues = _issues(hass)
    assert {
        issue_id: (issue.translation_key, issue.translation_placeholders)
        for issue_id, issue in issues.items()
    } == {
        "renamed_entities": (
            "renamed_entities",
            {"entities": "- `sensor.bitpanda_wallets_btc_wallet` → `sensor.bitpanda_bitcoin_btc_wallet`"},
        ),
        "entities_not_migrated": (
            "entities_not_migrated", {"entities": f"- `{gone}`\n- `{price}`"},
        ),
        "currency_dropped": ("currency_dropped", {"currency": "JPY"}),
        "price_tracker_exists": ("price_tracker_exists", {"assets": "- Bitcoin (BTC)"}),
    }
    for issue in issues.values():
        assert (
            issue.severity, issue.is_fixable, issue.is_persistent, issue.learn_more_url,
            issue.issue_domain,
        ) == (ir.IssueSeverity.WARNING, False, True, UPGRADE_URL, None)


async def test_an_upgrade_with_nothing_to_report_raises_no_issue(
    hass, legacy_api, no_setup, caplog
):
    """Nothing renamed, nothing left alone, the currency kept: Repairs stays
    empty. The log still records the upgrade and asks for the new key."""
    assert await async_migrate_entry(hass, _v1_entry(hass))
    assert _issues(hass) == {}
    logged = _logged(caplog)
    assert logged.startswith("Bitpanda is now two services")
    assert "https://app.bitpanda.com/my-account/apikey" in logged
    assert "Earn (Read)" in logged


async def test_the_full_mapping_is_logged_once_in_english(
    hass, legacy_api, no_setup, caplog
):
    """Repair issues can be dismissed, and list the entities left alone
    without the reason for each: one WARNING keeps the whole mapping, with
    every reason -- in English like every log line, also where Home
    Assistant runs in another language."""
    hass.config.language = "de"
    entry, gone, price = _upgrade_with_every_issue(hass)

    assert await async_migrate_entry(hass, entry)

    assert _logged(caplog) == (
        "Bitpanda is now two services: Bitpanda Portfolio and Bitpanda Price Tracker.\n\n"
        "Renamed entity IDs. Check dashboards, automations and scripts that use them:\n"
        "- `sensor.bitpanda_wallets_btc_wallet` → `sensor.bitpanda_bitcoin_btc_wallet`\n\n"
        "Not migrated (left unchanged; delete them when you no longer need them):\n"
        f"- `{gone}`: GONE no longer exists at Bitpanda\n"
        f"- `{price}`: a Price Tracker was already set up\n\n"
        "JPY is not available for the Bitpanda Portfolio; it now reports in EUR.\n\n"
        "A Bitpanda Price Tracker was already set up, so the prices tracked before the "
        "upgrade were not moved into it. Add these assets there to keep tracking them: "
        "Bitcoin (BTC).\n\n"
        "Bitpanda needs a new API key with the permissions Guthaben (Balance), Transaktion "
        "(Transaction) and Earn (Read). Create it at https://app.bitpanda.com/my-account/apikey "
        "and enter it when Home Assistant asks for it."
    )
    assert "legacy-key" not in caplog.text


def test_learn_more_leads_to_the_readmes_upgrade_section():
    """The anchor GitHub gives the upgrade heading -- an arrow emoji (U+2B06
    U+FE0F), then "Upgrading from 2026.06.x" -- as read from the page GitHub
    renders for this README: the variation selector U+FE0F kept, the arrow
    and the dots dropped. Renaming the heading breaks the link -- and fails
    this test first."""
    readme = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
    assert "\n## \u2b06\ufe0f Upgrading from 2026.06.x\n" in readme
    assert UPGRADE_URL == (
        "https://github.com/Spegeli/hacs_bitpanda#%EF%B8%8F-upgrading-from-202606x"
    )


_INTEGRATION = Path(migration.__file__).parent


def _placeholders(template: str) -> frozenset[str]:
    """The {placeholders} of a text, parsed as Home Assistant parses them."""
    return frozenset(
        field for _, field, _, _ in string.Formatter().parse(template) if field is not None
    )


def _raised(hass) -> dict[str, dict[str, str]]:
    """This integration's repair issues, read back from the issue registry:
    translation key -> the placeholders the code supplied."""
    return {
        issue.translation_key: issue.translation_placeholders
        for issue in _issues(hass).values()
    }


def _assert_every_language_renders(raised: dict[str, dict[str, str]]) -> None:
    """Every issue in `raised` has a title and a description in every
    shipped language that use exactly the placeholders the code supplied and
    render with them. A list opens a paragraph of its own, so the frontend
    renders it as a Markdown list. Read from the files themselves: Home
    Assistant would replace a mismatched translation with English, hiding
    it."""
    languages = sorted(path.stem for path in (_INTEGRATION / "translations").glob("*.json"))
    assert len(languages) == 7
    for language in languages:
        texts = json.loads(
            (_INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )["issues"]
        for key, placeholders in raised.items():
            placeholders = placeholders or {}
            title, description = texts[key]["title"], texts[key]["description"]
            assert _placeholders(title) | _placeholders(description) == set(placeholders), (
                language, key,
            )
            rendered = title.format(**placeholders) + description.format(**placeholders)
            assert all(value in rendered for value in placeholders.values()), (language, key)
            for name, value in placeholders.items():
                if value.startswith("- "):
                    assert f"\n\n{{{name}}}" in description, (language, key, name)


async def test_every_issue_text_renders_in_every_language(hass, legacy_api, no_setup):
    """Every repair issue the upgrade raises -- all of them, from one
    migration -- renders in every shipped language."""
    entry, _, _ = _upgrade_with_every_issue(hass)
    assert await async_migrate_entry(hass, entry)
    raised = _raised(hass)
    assert set(raised) == set(migration.UPGRADE_ISSUES)
    _assert_every_language_renders(raised)


async def test_every_blocker_text_renders_in_every_language(hass, legacy_api, no_setup):
    """Both causes, one after the other: Home Assistant too old, then --
    updated -- a Portfolio set up beside the old entry."""
    entry = _v1_entry(hass)
    with _home_assistant(2025, 4, "2025.4.2"):
        assert not await async_migrate_entry(hass, entry)
    raised = _raised(hass)
    _portfolio_set_up_before(hass)
    assert not await async_migrate_entry(hass, entry)
    raised |= _raised(hass)
    assert set(raised) == set(migration.BLOCKER_ISSUES)
    _assert_every_language_renders(raised)


def test_every_issue_text_is_one_the_code_raises():
    """strings.json has no issue text the code never raises: the upgrade's
    reports and what blocks the upgrade."""
    strings = json.loads((_INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    assert set(strings["issues"]) == {*migration.UPGRADE_ISSUES, *migration.BLOCKER_ISSUES}


async def test_the_upgrade_issues_go_with_the_last_bitpanda_entry(hass, legacy_api, no_setup):
    """Once no Bitpanda entry remains, the upgrade's repair issues describe
    entities that are gone -- and after an uninstall Repairs could not even
    show their texts: removing the last entry deletes them. While another
    Bitpanda entry remains they stay; other integrations' issues always do."""
    entry, _, _ = _upgrade_with_every_issue(hass)
    assert await async_migrate_entry(hass, entry)
    [tracker] = _price_trackers(hass)
    ir.async_create_issue(
        hass, "other", "unrelated", is_fixable=False, severity=ir.IssueSeverity.WARNING,
        translation_key="unrelated",
    )
    assert set(_issues(hass)) == set(migration.UPGRADE_ISSUES)

    await hass.config_entries.async_remove(entry.entry_id)
    assert set(_issues(hass)) == set(migration.UPGRADE_ISSUES)

    await hass.config_entries.async_remove(tracker.entry_id)
    assert _issues(hass) == {}
    assert ir.async_get(hass).async_get_issue("other", "unrelated") is not None


async def test_an_interrupted_migration_can_run_again(hass, legacy_api, no_setup):
    """The second run finds the wallet re-keyed already: it lists nothing as
    not migrated, and the first run's renamed issue stays as it was."""
    entry = _v1_entry(hass, wallets=["cryptocoin_BTC"])
    eid = entry.entry_id
    _legacy_entity(hass, entry, f"{eid}_wallet_cryptocoin_BTC", "bitpanda_wallets_btc_wallet")
    assert await async_migrate_entry(hass, entry)
    renamed = _renamed(hass)
    assert renamed
    # As if the version bump had never been saved.
    hass.config_entries.async_update_entry(
        entry, version=1, data={"api_key": "legacy-key", "currency": "EUR"},
        options={"tracked_assets": [], "tracked_wallets": ["cryptocoin_BTC"]},
    )
    assert await async_migrate_entry(hass, entry)
    wallet = er.async_get(hass).async_get("sensor.bitpanda_bitcoin_btc_wallet")
    assert wallet.unique_id == f"{eid}_wallet_{BTC_ID}"
    assert "entities_not_migrated" not in _issues(hass)
    assert _renamed(hass) == renamed


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


async def test_a_currency_list_without_eur_aborts_the_migration(hass, legacy_api, no_setup):
    """Not empty, yet without EUR -- the currency every fallback needs: as
    broken as an empty answer, so nothing changes, not even for a user whose
    own currency is on the list."""
    currencies, _ = legacy_api
    currencies.return_value = [
        currency for currency in load_fixture("currencies.json") if currency["symbol"] != "EUR"
    ]
    entry = _v1_entry(hass, currency="USD")
    assert not await async_migrate_entry(hass, entry)
    assert entry.version == 1
    assert dict(entry.data) == {"api_key": "legacy-key", "currency": "USD"}
