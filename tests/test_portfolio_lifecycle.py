"""Wallet devices appear and disappear with the holdings."""
from datetime import timedelta
import logging
from unittest.mock import AsyncMock

from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockEntityPlatform,
    async_fire_time_changed,
)

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.portfolio_coordinator import PortfolioRuntime
from custom_components.bitpanda.portfolio_model import EarnData, Holding, PortfolioData
from custom_components.bitpanda.portfolio_sensor import (
    PortfolioEntityManager,
    async_setup_portfolio_entities,
)

VSN = {"id": "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb", "symbol": "VSN", "name": "Vision", "group": "token"}
BTC = {"id": "b86c034b-efe3-11eb-b56f-0691764446a7", "symbol": "BTC", "name": "Bitcoin", "group": "coin"}
BCPEUR = {"id": "1edf9721-e545-644c-9796-ae5b69a774d7", "symbol": "BCPEUR",
          "name": "Bitpanda Cash Plus EUR", "group": "fiat_earn"}
_LOG = logging.getLogger(__name__)


def _holding(asset, staked=0.0) -> Holding:
    return Holding(asset_id=asset["id"], balance=10.0, available=10.0 - staked, value=100.0)


def _data(*holdings, unnamed=()) -> PortfolioData:
    data = PortfolioData(holdings={h.asset_id: h for h in holdings})
    records = {a["id"]: a for a in (VSN, BTC, BCPEUR)}
    data.assets = {h.asset_id: records[h.asset_id] for h in holdings if h.asset_id not in unnamed}
    return data


class _Harness:
    """A manager wired to a real entity platform, registry and coordinators."""

    def __init__(self, hass):
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
        )
        self.runtime.earn.data = EarnData(apr={}, offered=frozenset())
        self.manager = PortfolioEntityManager(
            hass, self.entry, self.runtime, "EUR",
            lambda entities: hass.async_create_task(self.platform.async_add_entities(entities)),
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


async def test_a_held_asset_gets_its_wallet_device(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(VSN)))
    assert harness.entity_ids() == {"sensor.bitpanda_vision_vsn_wallet"}
    assert harness.devices() == {"Vision (VSN) Wallet"}


async def test_cash_plus_and_unnamed_holdings_get_no_wallet(hass):
    harness = _Harness(hass)
    await harness.refresh(_data(_holding(BCPEUR), _holding(BTC), unnamed={BTC["id"]}))
    assert harness.entity_ids() == set()


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
    """Task 3 ruling: an asset in `unparsed_assets` is still held, so it must
    not count towards the 3-miss removal even though it is absent from
    `data.holdings` (its record could not be read this refresh)."""
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
    later becomes offered still needs to gain Staking/Total (spec §2.4)."""
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
    )
    runtime.portfolio.data = _data(_holding(VSN))  # nothing staked
    runtime.portfolio.last_update_success = True
    entry.runtime_data = runtime

    await async_setup_portfolio_entities(
        hass, entry,
        lambda entities: hass.async_create_task(platform.async_add_entities(entities)),
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
