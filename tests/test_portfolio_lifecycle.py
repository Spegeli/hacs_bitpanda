"""Wallet devices appear and disappear with the holdings, in groups by asset type."""
from datetime import timedelta
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockEntityPlatform,
    async_fire_time_changed,
)

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.groups import async_get_or_create_wallet_group
from custom_components.bitpanda.naming import asset_display_label, wallet_entity_id
from custom_components.bitpanda.portfolio_coordinator import PortfolioRuntime
from custom_components.bitpanda.portfolio_model import EarnData, Holding, PortfolioData
from custom_components.bitpanda.portfolio_sensor import (
    PortfolioEntityManager,
    async_setup_portfolio_entities,
)

from tests.conftest import device_names_in_subentry

VSN = {"id": "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb", "symbol": "VSN", "name": "Vision",
       "type": "cryptocoin", "group": "token"}
BTC = {"id": "b86c034b-efe3-11eb-b56f-0691764446a7", "symbol": "BTC", "name": "Bitcoin",
       "type": "cryptocoin", "group": "coin"}
GOLD = {"id": "b86c88d4-efe3-11eb-b56f-0691764446a7", "symbol": "XAU", "name": "Gold",
        "type": "commodity", "group": "metal"}
BCPEUR = {"id": "1edf9721-e545-644c-9796-ae5b69a774d7", "symbol": "BCPEUR",
          "name": "Bitpanda Cash Plus EUR", "type": "security", "group": "fiat_earn"}
_LOG = logging.getLogger(__name__)

# The group titles of an English Home Assistant, as setup loads them.
_TITLES = json.loads(
    (
        Path(__file__).parent.parent / "custom_components" / "bitpanda" / "translations" / "en.json"
    ).read_text(encoding="utf-8")
)["selector"]["asset_group"]["options"]

VSN_WALLET = "sensor.bitpanda_vision_vsn_wallet"
VSN_ENTITIES = {VSN_WALLET, f"{VSN_WALLET}_staking", f"{VSN_WALLET}_total"}
GOLD_WALLET = "sensor.bitpanda_gold_xau_wallet"


def _holding(asset, staked=0.0) -> Holding:
    return Holding(asset_id=asset["id"], balance=10.0, available=10.0 - staked, value=100.0)


def _data(*holdings, unnamed=()) -> PortfolioData:
    data = PortfolioData(holdings={h.asset_id: h for h in holdings})
    records = {a["id"]: a for a in (VSN, BTC, GOLD, BCPEUR)}
    data.assets = {h.asset_id: records[h.asset_id] for h in holdings if h.asset_id not in unnamed}
    return data


class _Harness:
    """A manager wired to a real entity platform, registry and coordinators.

    `eager_add=False` lets the platform add entities only once the manager's
    refresh has returned, rather than starting at once as Home Assistant does.
    """

    def __init__(self, hass, *, eager_add=True):
        self.hass = hass
        self.entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
        self.entry.add_to_hass(hass)
        self.platform = MockEntityPlatform(hass, domain="sensor", platform_name=DOMAIN)
        self.platform.config_entry = self.entry

        def _coordinator(name):
            return DataUpdateCoordinator(
                hass, _LOG, config_entry=self.entry, name=name, update_interval=None
            )

        self.runtime = PortfolioRuntime(
            portfolio=_coordinator("portfolio"),
            history=_coordinator("history"),
            earn=_coordinator("earn"),
            rewards=_coordinator("rewards"),
            group_titles=_TITLES,
            data_at_setup=dict(self.entry.data),
            options_at_setup={},
        )
        self.runtime.earn.data = EarnData(apr={}, offered=frozenset())
        self.manager = PortfolioEntityManager(
            hass, self.entry, self.runtime, "EUR",
            lambda entities, **kwargs: hass.async_create_task(
                self.platform.async_add_entities(entities, **kwargs), eager_start=eager_add
            ),
        )

    async def refresh(self, data=None, success=True):
        self.runtime.portfolio.data = data
        self.runtime.portfolio.last_update_success = success
        self.manager.async_reconcile()
        await self.hass.async_block_till_done()

    def entity_ids(self) -> set[str]:
        return {
            e.entity_id
            for e in er.async_entries_for_config_entry(er.async_get(self.hass), self.entry.entry_id)
        }

    def devices(self) -> set[str]:
        return {
            d.name
            for d in dr.async_entries_for_config_entry(dr.async_get(self.hass), self.entry.entry_id)
        }

    def groups(self) -> dict[str, str]:
        """Category -> title of every wallet group."""
        return {
            sub.unique_id: sub.title
            for sub in self.entry.subentries.values()
            if sub.subentry_type == "wallet_group"
        }

    def group(self, category: str) -> ConfigSubentry:
        [group] = [sub for sub in self.entry.subentries.values() if sub.unique_id == category]
        return group

    def group_devices(self, category: str) -> set[str]:
        return device_names_in_subentry(
            self.hass, self.entry.entry_id, self.group(category).subentry_id
        )

    def subentry_of(self, entity_id: str) -> str | None:
        return er.async_get(self.hass).async_get(entity_id).config_subentry_id

    def register_wallet(self, asset: dict, category: str) -> ConfigSubentry:
        """A wallet left from before a restart: its device and Wallet sensor,
        registered in the group of `category`, which is returned."""
        eid = self.entry.entry_id
        group = async_get_or_create_wallet_group(self.hass, self.entry, category, _TITLES)
        device = dr.async_get(self.hass).async_get_or_create(
            config_entry_id=eid,
            config_subentry_id=group.subentry_id,
            identifiers={(DOMAIN, f"{eid}_wallet_{asset['id']}")},
            name=f"{asset_display_label(asset)} Wallet",
        )
        er.async_get(self.hass).async_get_or_create(
            "sensor", DOMAIN, f"{eid}_wallet_{asset['id']}", config_entry=self.entry,
            config_subentry_id=group.subentry_id, device_id=device.id,
            suggested_object_id=wallet_entity_id(asset).split(".", 1)[1],
        )
        return group


async def test_a_held_asset_gets_its_wallet_device(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN)))
    assert harness.entity_ids() == {"sensor.bitpanda_vision_vsn_wallet"}
    assert harness.devices() == {"Vision (VSN) Wallet"}


async def test_cash_plus_and_unnamed_holdings_get_no_wallet(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(BCPEUR), _holding(BTC), unnamed={BTC["id"]}))
    assert harness.entity_ids() == set()
    assert harness.groups() == {}


async def test_something_staked_adds_staking_and_total(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN, staked=4.0)))
    assert harness.entity_ids() == {
        "sensor.bitpanda_vision_vsn_wallet",
        "sensor.bitpanda_vision_vsn_wallet_staking",
        "sensor.bitpanda_vision_vsn_wallet_total",
    }
    assert harness.manager.has_total(VSN["id"])


async def test_an_offered_product_adds_staking_even_with_nothing_staked(hass):
    harness = _Harness(hass)
    harness.runtime.earn.data = EarnData(apr={}, offered=frozenset({VSN["id"]}))
    await harness.refresh(_data(_holding(VSN)))
    assert "sensor.bitpanda_vision_vsn_wallet_staking" in harness.entity_ids()


async def test_staking_leaves_when_nothing_is_staked_and_no_product_is_offered(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN, staked=4.0)))
    await harness.refresh(_data(_holding(VSN)))
    assert harness.entity_ids() == {"sensor.bitpanda_vision_vsn_wallet"}
    assert not harness.manager.has_total(VSN["id"])


async def test_unknown_earn_never_creates_staking(hass):
    """Nothing staked and no current Earn catalogue: whether the asset is
    offered cannot be told, and unknown never creates. A catalogue from an
    earlier success does not count once the last refresh failed."""
    harness = _Harness(hass)
    harness.runtime.earn.data = EarnData(apr={}, offered=frozenset({VSN["id"]}))
    harness.runtime.earn.last_update_success = False
    await harness.refresh(_data(_holding(VSN)))
    assert harness.entity_ids() == {"sensor.bitpanda_vision_vsn_wallet"}
    assert not harness.manager.has_total(VSN["id"])


async def test_staking_stays_while_the_earn_catalogue_is_unknown(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN, staked=4.0)))
    harness.runtime.earn.last_update_success = False
    await harness.refresh(_data(_holding(VSN)))
    assert "sensor.bitpanda_vision_vsn_wallet_staking" in harness.entity_ids()


async def test_a_sold_asset_leaves_after_three_successful_refreshes_only(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN, staked=4.0), _holding(BTC)))
    for _ in range(2):
        await harness.refresh(_data(_holding(BTC)))
    # A failed refresh neither counts nor resets.
    await harness.refresh(_data(_holding(BTC)), success=False)
    assert "sensor.bitpanda_vision_vsn_wallet" in harness.entity_ids()
    await harness.refresh(_data(_holding(BTC)))
    assert harness.entity_ids() == {"sensor.bitpanda_bitcoin_btc_wallet"}
    assert harness.devices() == {"Bitcoin (BTC) Wallet"}


async def test_a_returning_holding_resets_the_count(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN), _holding(BTC)))
    await harness.refresh(_data(_holding(BTC)))
    await harness.refresh(_data(_holding(BTC)))
    await harness.refresh(_data(_holding(VSN), _holding(BTC)))
    await harness.refresh(_data(_holding(BTC)))
    await harness.refresh(_data(_holding(BTC)))
    assert "sensor.bitpanda_vision_vsn_wallet" in harness.entity_ids()


async def test_an_unnamed_holding_is_not_a_miss(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN)))
    for _ in range(3):
        await harness.refresh(_data(_holding(VSN), unnamed={VSN["id"]}))
    assert "sensor.bitpanda_vision_vsn_wallet" in harness.entity_ids()


async def test_an_unparsable_holding_is_not_a_miss(hass):
    """An asset in `unparsed_assets` is still held, so it must not count
    towards the 3-miss removal even though it is absent from `data.holdings`
    (its /portfolio entry could not be read this refresh)."""
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN)))
    for _ in range(3):
        data = _data()
        data.unparsed_assets = {VSN["id"]}
        await harness.refresh(data)
    assert "sensor.bitpanda_vision_vsn_wallet" in harness.entity_ids()


async def test_a_rebought_asset_reclaims_its_entity_id(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN)))
    for _ in range(3):
        await harness.refresh(_data())
    assert harness.entity_ids() == set()
    await harness.refresh(_data(_holding(VSN)))
    assert harness.entity_ids() == {"sensor.bitpanda_vision_vsn_wallet"}


async def test_a_migrated_wallet_for_a_sold_asset_leaves_after_three_refreshes(hass):
    harness = _Harness(hass)
    ent_reg = er.async_get(hass)
    ent_reg.async_get_or_create(
        "sensor", DOMAIN, f"{harness.entry.entry_id}_wallet_{VSN['id']}",
        config_entry=harness.entry, suggested_object_id="bitpanda_vision_vsn_wallet",
    )
    unresolved = ent_reg.async_get_or_create(
        "sensor", DOMAIN, f"{harness.entry.entry_id}_wallet_cryptocoin_XYZ",
        config_entry=harness.entry, suggested_object_id="bitpanda_wallets_xyz_wallet",
    )
    for _ in range(3):
        await harness.refresh(_data())
    # The UUID-keyed one is managed and goes; the unresolved legacy one is
    # never touched.
    assert harness.entity_ids() == {unresolved.entity_id}


async def test_wallets_are_grouped_by_asset_type(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN, staked=4.0), _holding(GOLD)))
    assert harness.groups() == {"crypto": "Cryptocurrencies", "metal": "Precious metals"}
    crypto, metal = harness.group("crypto"), harness.group("metal")
    assert dict(crypto.data) == {"category": "crypto"}
    assert dict(metal.data) == {"category": "metal"}
    # Wallet, Staking and Total of an asset share its group, device included.
    assert {entity_id: harness.subentry_of(entity_id) for entity_id in VSN_ENTITIES} == {
        entity_id: crypto.subentry_id for entity_id in VSN_ENTITIES
    }
    assert harness.subentry_of(GOLD_WALLET) == metal.subentry_id
    assert harness.group_devices("crypto") == {"Vision (VSN) Wallet"}
    assert harness.group_devices("metal") == {"Gold (XAU) Wallet"}


async def test_a_second_wallet_of_a_type_joins_its_group(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN)))
    crypto = harness.group("crypto")
    await harness.refresh(_data(_holding(VSN), _holding(BTC)))
    assert harness.groups() == {"crypto": "Cryptocurrencies"}
    assert harness.group("crypto").subentry_id == crypto.subentry_id
    assert harness.subentry_of("sensor.bitpanda_bitcoin_btc_wallet") == crypto.subentry_id
    assert harness.group_devices("crypto") == {"Vision (VSN) Wallet", "Bitcoin (BTC) Wallet"}


async def test_staking_that_starts_later_joins_the_group_of_its_wallet(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN)))
    await harness.refresh(_data(_holding(VSN, staked=4.0)))
    crypto = harness.group("crypto").subentry_id
    assert {entity_id: harness.subentry_of(entity_id) for entity_id in VSN_ENTITIES} == {
        entity_id: crypto for entity_id in VSN_ENTITIES
    }


async def test_the_last_wallet_of_a_type_takes_its_group_along(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN), _holding(GOLD)))
    for _ in range(2):
        await harness.refresh(_data(_holding(VSN)))
    assert set(harness.groups()) == {"crypto", "metal"}
    await harness.refresh(_data(_holding(VSN)))
    assert harness.groups() == {"crypto": "Cryptocurrencies"}
    assert harness.devices() == {"Vision (VSN) Wallet"}


async def test_a_new_group_stays_while_its_wallets_are_still_being_added(hass):
    """A group created in this refresh may hold no device yet when the
    refresh ends: the wallet it was created for keeps it."""
    harness = _Harness(hass, eager_add=False)
    await harness.refresh(_data(_holding(VSN)))
    assert harness.groups() == {"crypto": "Cryptocurrencies"}
    assert harness.group_devices("crypto") == {"Vision (VSN) Wallet"}


async def test_a_group_stays_while_it_holds_a_wallet(hass):
    """After a restart the manager tracks only the wallets it added itself.
    One from before -- here of an asset sold since -- still sits in its
    group, and the group stays until that wallet is gone."""
    harness = _Harness(hass)
    harness.register_wallet(GOLD, "metal")
    for _ in range(2):
        await harness.refresh(_data(_holding(VSN)))
    assert set(harness.groups()) == {"crypto", "metal"}
    await harness.refresh(_data(_holding(VSN)))
    assert set(harness.groups()) == {"crypto"}
    assert harness.devices() == {"Vision (VSN) Wallet"}


async def test_a_wallet_stays_in_the_group_it_sits_in(hass, caplog):
    """VSN's wallet sits in the metal group from before a restart, while its
    record now says crypto -- as when Bitpanda files an asset under another
    type. It stays where it is: its device never moves between groups, no
    crypto group appears for it, and the metal group is kept."""
    harness = _Harness(hass)
    metal = harness.register_wallet(VSN, "metal")

    for _ in range(2):
        await harness.refresh(_data(_holding(VSN, staked=4.0)))

    assert harness.groups() == {"metal": "Precious metals"}
    assert {entity_id: harness.subentry_of(entity_id) for entity_id in VSN_ENTITIES} == {
        entity_id: metal.subentry_id for entity_id in VSN_ENTITIES
    }
    assert harness.group_devices("metal") == {"Vision (VSN) Wallet"}
    assert "assigns an existing device to a different config subentry" not in caplog.text


async def test_the_wallets_of_a_deleted_group_come_back_in_a_new_group(hass):
    """Deleting a group deletes its devices and entities. Assets still held
    come back with the next refresh, in a new group, under the same IDs."""
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN, staked=4.0), _holding(GOLD)))
    crypto = harness.group("crypto")
    hass.config_entries.async_remove_subentry(harness.entry, crypto.subentry_id)
    await hass.async_block_till_done()
    assert harness.entity_ids() == {GOLD_WALLET}

    await harness.refresh(_data(_holding(VSN, staked=4.0), _holding(GOLD)))

    regrouped = harness.group("crypto")
    assert regrouped.subentry_id != crypto.subentry_id
    assert harness.entity_ids() == VSN_ENTITIES | {GOLD_WALLET}
    assert {entity_id: harness.subentry_of(entity_id) for entity_id in VSN_ENTITIES} == {
        entity_id: regrouped.subentry_id for entity_id in VSN_ENTITIES
    }
    assert harness.group_devices("crypto") == {"Vision (VSN) Wallet"}
    assert harness.manager.has_total(VSN["id"])


async def test_a_failed_refresh_neither_brings_back_nor_removes_a_group(hass):
    """Like every other change, healing a deleted group and removing an empty
    one wait for a successful refresh."""
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN), _holding(GOLD)))
    async_get_or_create_wallet_group(hass, harness.entry, "etf", _TITLES)  # holds nothing
    hass.config_entries.async_remove_subentry(harness.entry, harness.group("crypto").subentry_id)
    await hass.async_block_till_done()

    await harness.refresh(_data(_holding(VSN), _holding(GOLD)), success=False)
    assert set(harness.groups()) == {"metal", "etf"}
    assert harness.entity_ids() == {GOLD_WALLET}

    await harness.refresh(_data(_holding(VSN), _holding(GOLD)))
    assert set(harness.groups()) == {"crypto", "metal"}
    assert harness.entity_ids() == {VSN_WALLET, GOLD_WALLET}


async def test_staking_registered_before_a_restart_is_recreated_while_earn_is_unknown(hass):
    harness = _Harness(hass)
    ent_reg = er.async_get(hass)
    for kind, suffix in (("staking", "_staking"), ("total", "_total")):
        ent_reg.async_get_or_create(
            "sensor", DOMAIN, f"{harness.entry.entry_id}_{kind}_{VSN['id']}",
            config_entry=harness.entry, suggested_object_id=f"bitpanda_vision_vsn_wallet{suffix}",
        )
    harness.runtime.earn.last_update_success = False
    await harness.refresh(_data(_holding(VSN)))
    assert harness.manager.has_total(VSN["id"])
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is not None


async def test_the_earn_catalogue_keeps_refreshing_without_staking_sensors(hass):
    """DataUpdateCoordinator only reschedules itself while it has listeners.

    The Earn coordinator's only other listeners are StakingSensors, so an
    entry with none registered (nothing staked, nothing offered) must not
    freeze the catalogue at its setup-time answer forever -- an asset that
    later becomes offered still needs to gain Staking/Total."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, data={"entry_type": "portfolio", "currency": "EUR"},
    )
    entry.add_to_hass(hass)
    platform = MockEntityPlatform(hass, domain="sensor", platform_name=DOMAIN)
    platform.config_entry = entry

    def _coordinator(name):
        return DataUpdateCoordinator(
            hass, _LOG, config_entry=entry, name=name, update_interval=None
        )

    update_method = AsyncMock(return_value=EarnData(apr={}, offered=frozenset()))
    earn = DataUpdateCoordinator(
        hass, _LOG, config_entry=entry, name="earn",
        update_interval=timedelta(hours=24), update_method=update_method,
    )
    runtime = PortfolioRuntime(
        portfolio=_coordinator("portfolio"),
        history=_coordinator("history"),
        earn=earn,
        rewards=_coordinator("rewards"),
        group_titles=_TITLES,
        data_at_setup=dict(entry.data),
        options_at_setup={},
    )
    runtime.portfolio.data = _data(_holding(VSN))  # nothing staked
    runtime.portfolio.last_update_success = True
    entry.runtime_data = runtime

    await async_setup_portfolio_entities(
        hass, entry,
        lambda entities, **kwargs: hass.async_create_task(
            platform.async_add_entities(entities, **kwargs)
        ),
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is None

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=25))
    await hass.async_block_till_done()
    assert update_method.await_count >= 1

    # A successful refresh reschedules the next one as long as `_keep_polling`
    # is still subscribed, which would otherwise leave a pending loop timer at
    # teardown. This entry was never taken through
    # hass.config_entries.async_setup, so it stays ConfigEntryState.NOT_LOADED
    # and hass.config_entries.async_unload(entry.entry_id) would return early
    # without running the `_on_unload` callbacks -- shut the coordinator down
    # directly instead (DataUpdateCoordinator registers this same method with
    # config_entry.async_on_unload itself when given a config_entry).
    await earn.async_shutdown()
