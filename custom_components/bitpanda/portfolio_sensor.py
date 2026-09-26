"""Sensors of the Portfolio service.

Every value is in the Portfolio currency, as Bitpanda reports it. Units of an
asset are attributes, never states.

Every sensor keeps long-term statistics: the money values as `total`, the
only state class Home Assistant allows for the monetary device class, the
returns as `measurement`. They are recorded in the Portfolio currency, so a
currency change clears them with the sensors' history (purge.py).
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .assets import asset_attributes, asset_category
from .const import (
    CONF_CURRENCY,
    DOMAIN,
    PORTFOLIO_TIMEFRAMES,
    SUBENTRY_TYPE_WALLET_GROUP,
)
from .devices import find_entry_device
from .groups import (
    async_get_or_create_wallet_group,
    entities_by_group,
    group_of_category,
    groups_of_type,
)
from .naming import (
    PORTFOLIO_DEVICE_NAME,
    managed_asset_key,
    portfolio_device_identifier,
    portfolio_entity_id,
    portfolio_unique_id,
    return_key,
    staking_entity_id,
    staking_unique_id,
    total_entity_id,
    total_unique_id,
    wallet_device_identifier,
    wallet_device_name,
    wallet_entity_id,
    wallet_unique_id,
)
from .portfolio_coordinator import PortfolioRuntime
from .portfolio_model import (
    DECIMALS,
    EarnData,
    Holding,
    PortfolioData,
    PortfolioReturns,
    confirmed,
    staking_applies,
)

_CONFIGURATION_URL = "https://www.bitpanda.com"


def portfolio_device_info(entry_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, portfolio_device_identifier(entry_id))},
        name=PORTFOLIO_DEVICE_NAME,
        manufacturer="Bitpanda",
        model="Portfolio",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=_CONFIGURATION_URL,
    )


def wallet_device_info(entry_id: str, asset: dict) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, wallet_device_identifier(entry_id, asset["id"]))},
        name=wallet_device_name(asset),
        manufacturer="Bitpanda",
        model="Wallet",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=_CONFIGURATION_URL,
    )


# --- Portfolio device ------------------------------------------------------------


class _PortfolioFigure(CoordinatorEntity, SensorEntity):
    """One figure of the whole account.

    Unavailable only while the update failed -- an empty answer held back
    until it is confirmed included (PortfolioCoordinator). When the answer
    arrived but the figure cannot be told from it -- an entry that could not
    be read, a holding not classified yet, a value Bitpanda did not send --
    the sensor stays available and its state is unknown: never a figure that
    quietly leaves something out.
    """

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2
    _key: str
    _attr_translation_key: str

    def __init__(self, coordinator, entry_id: str, currency: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = portfolio_unique_id(entry_id, self._key)
        self.entity_id = portfolio_entity_id(self._key)
        self._attr_native_unit_of_measurement = currency
        self._attr_device_info = portfolio_device_info(entry_id)

    def _figure(self, data: PortfolioData) -> float | None:
        raise NotImplementedError

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return None if data is None else self._figure(data)


class PortfolioTotalSensor(_PortfolioFigure):
    """Every holding, Cash Plus included, plus all fiat."""

    _key = "total"
    _attr_translation_key = "total_value"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.total


class PortfolioCashSensor(_PortfolioFigure):
    """Sum of the fiat balances (`balance`: locked fiat is still cash)."""

    _key = "cash"
    _attr_translation_key = "cash"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.cash


class PortfolioCashPlusSensor(_PortfolioFigure):
    """Value of the Cash Plus holdings. Unknown while any holding is
    unclassified."""

    _key = "cash_plus"
    _attr_translation_key = "cash_plus"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.cash_plus

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Each held Cash Plus product's own amount, keyed by currency code.

        Empty whenever `cash_plus_amounts` is None -- the state (`cash_plus`
        itself) is unknown for the same reason -- or when nothing is held:
        never a partial mapping.
        """
        data = self.coordinator.data
        if data is None:
            return {}
        return data.cash_plus_amounts or {}


class PortfolioReturnSensor(CoordinatorEntity, SensorEntity):
    """The portfolio's return over one timeframe, in percent.

    Unavailable while the history update failed or this timeframe's own
    request did; unknown when Bitpanda answered for it without a usable
    figure (PortfolioReturns).
    """

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry_id: str, timeframe: str) -> None:
        super().__init__(coordinator)
        key = return_key(timeframe)
        self._timeframe = timeframe
        self._attr_translation_key = key
        self._attr_unique_id = portfolio_unique_id(entry_id, key)
        self.entity_id = portfolio_entity_id(key)
        self._attr_device_info = portfolio_device_info(entry_id)

    @property
    def native_value(self) -> float | None:
        data: PortfolioReturns | None = self.coordinator.data
        return None if data is None else data.values.get(self._timeframe)

    @property
    def available(self) -> bool:
        data: PortfolioReturns | None = self.coordinator.data
        return super().available and data is not None and self._timeframe not in data.failed


# --- Wallet devices -----------------------------------------------------------------


def _performance(holding: Holding) -> dict[str, float]:
    """The position performance Bitpanda computes for the whole position."""
    out: dict[str, float] = {}
    for key, value in (
        ("average_buy_price", holding.avg_buy_price),
        ("invested_amount", holding.invested),
        ("total_return", holding.total_return),
        ("total_return_percent", holding.total_return_pct),
    ):
        if value is not None:
            out[key] = round(value, DECIMALS)
    return out


class _WalletPart(CoordinatorEntity, SensorEntity):
    """One value of one holding."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, entry_id: str, currency: str, asset: dict) -> None:
        super().__init__(coordinator)
        self._asset = asset
        self._asset_id = asset["id"]
        self._attr_native_unit_of_measurement = currency
        self._attr_device_info = wallet_device_info(entry_id, asset)

    @property
    def _holding(self) -> Holding | None:
        data = self.coordinator.data
        return None if data is None else data.holdings.get(self._asset_id)

    def _value(self, holding: Holding) -> float | None:
        raise NotImplementedError

    def _units(self, holding: Holding) -> float:
        raise NotImplementedError

    @property
    def native_value(self) -> float | None:
        holding = self._holding
        return None if holding is None else self._value(holding)

    @property
    def available(self) -> bool:
        """Unavailable while the update failed, and once /portfolio no longer
        lists the asset -- until the manager removes the wallet. While it is
        listed (PortfolioData.held, an unreadable entry included), a value
        that cannot be told is unknown."""
        data: PortfolioData | None = self.coordinator.data
        return super().available and data is not None and self._asset_id in data.held

    def _attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = asset_attributes(self._asset)
        holding = self._holding
        if holding is not None:
            attrs["units"] = self._units(holding)
        return attrs


class WalletSensor(_WalletPart):
    """Value of the unstaked units, named like its Staking and Total siblings
    by its part of the balance: "Vision (VSN) Wallet Balance (available)",
    with or without them beside it.

    `has_total` says whether this asset currently has a Total sensor; while it
    has none, the position performance is shown here instead.
    """

    _attr_translation_key = "wallet"

    def __init__(
        self,
        coordinator,
        entry_id: str,
        currency: str,
        asset: dict,
        has_total: Callable[[str], bool],
    ) -> None:
        super().__init__(coordinator, entry_id, currency, asset)
        self._has_total = has_total
        self._attr_unique_id = wallet_unique_id(entry_id, asset["id"])
        self.entity_id = wallet_entity_id(asset)

    def _value(self, holding: Holding) -> float | None:
        return holding.wallet_value

    def _units(self, holding: Holding) -> float:
        return round(min(holding.available, holding.balance), DECIMALS)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = self._attributes()
        holding = self._holding
        if holding is not None and not self._has_total(self._asset_id):
            attrs.update(_performance(holding))
        return attrs


class StakingSensor(_WalletPart):
    """Value of the staked units, with everything about Earn as attributes."""

    _attr_translation_key = "staking"

    def __init__(
        self, coordinator, earn, rewards, entry_id: str, currency: str, asset: dict
    ) -> None:
        super().__init__(coordinator, entry_id, currency, asset)
        self._earn = earn
        self._rewards = rewards
        self._attr_unique_id = staking_unique_id(entry_id, asset["id"])
        self.entity_id = staking_entity_id(asset)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        for coordinator in (self._earn, self._rewards):
            self.async_on_remove(
                coordinator.async_add_listener(self._handle_coordinator_update, None)
            )
        # Staking sensors are all that keeps the rewards polled: a new one
        # catches up on totals that went stale while none was listening.
        self._rewards.async_refresh_if_stale()

    def _value(self, holding: Holding) -> float | None:
        return holding.staking_value

    def _units(self, holding: Holding) -> float:
        return holding.staked

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = self._attributes()
        earn = self._earn.data
        apr = earn.apr.get(self._asset_id) if earn is not None else None
        if apr is not None:
            # The API reports a fraction: 0.0544 means 5.44 %.
            attrs["apr_percent"] = round(apr * 100, DECIMALS)
        # After a failed refresh `data` still holds the last complete totals;
        # a listing that could not be paged completely never replaces them.
        # Gross, fee and net are units of the asset; `count` counts payouts.
        rewards = (self._rewards.data or {}).get(self._asset_id)
        if rewards is not None and rewards.count:
            attrs["rewards_gross"] = rewards.gross
            attrs["rewards_fee"] = rewards.fee
            attrs["rewards_net"] = rewards.net
            # What the net units are worth today, in the Portfolio currency,
            # at the price this /portfolio answer implies -- as the Bitpanda
            # app shows it. Never their value when paid out: no endpoint
            # prices a past date.
            holding = self._holding
            price = None if holding is None else holding.price
            if price is not None:
                attrs["rewards_net_value"] = round(rewards.net * price, 2)
            attrs["rewards_count"] = rewards.count
            attrs["rewards_last_at"] = rewards.last_at
        return attrs


class WalletTotalSensor(_WalletPart):
    """Value of the whole position, with its performance."""

    _attr_translation_key = "wallet_total"

    def __init__(self, coordinator, entry_id: str, currency: str, asset: dict) -> None:
        super().__init__(coordinator, entry_id, currency, asset)
        self._attr_unique_id = total_unique_id(entry_id, asset["id"])
        self.entity_id = total_entity_id(asset)

    def _value(self, holding: Holding) -> float | None:
        return holding.value

    def _units(self, holding: Holding) -> float:
        return round(holding.balance, DECIMALS)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = self._attributes()
        holding = self._holding
        if holding is not None:
            attrs.update(_performance(holding))
        return attrs


# --- Lifecycle manager ---------------------------------------------------------------


_UNIQUE_IDS = {
    "wallet": wallet_unique_id,
    "staking": staking_unique_id,
    "total": total_unique_id,
}


class PortfolioEntityManager:
    """Adds and removes wallet devices as holdings appear and disappear, and
    keeps them in groups by asset type.

    Runs after every portfolio refresh; a failed refresh changes nothing.
    A holding absent from WALLET_REMOVAL_MISSES consecutive successful
    refreshes, WALLET_REMOVAL_TIME after the first of them was asked for
    (portfolio_model.confirmed), loses its sensors and device -- a wallet
    migrated from version 1 whose asset is no longer held included. At the
    regular pace the third miss removes it; refreshes by hand count, but
    never remove it sooner. Only unique_ids that name an asset UUID are ever
    removed (naming.managed_asset_key): a legacy wallet the migration could
    not resolve is left for the user.

    Each wallet goes, with its Staking and Total sensors, into the wallet
    group (a config subentry) of its asset's category: created when the
    first wallet of that category arrives, removed once no wallet is left in
    it. A wallet already in a group stays there, even when Bitpanda files its
    asset under another type later: a device never moves between groups.
    The Portfolio device stays outside every group. A group the user
    deleted took its devices and entities along; the next refresh brings
    back the wallets of assets still held, in a new group and under the same
    entity IDs, without reloading the entry.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        runtime: PortfolioRuntime,
        currency: str,
        add_entities: Callable[..., None],
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._runtime = runtime
        self._currency = currency
        self._add_entities = add_entities
        # Asset id -> the category of the wallet group its sensors sit in.
        self._wallets: dict[str, str] = {}
        self._staking: set[str] = set()
        # Asset id -> its misses in a row, and when the first was asked for.
        self._misses: dict[str, tuple[int, datetime]] = {}

    def has_total(self, asset_id: str) -> bool:
        return asset_id in self._staking

    def _registered(self) -> dict[str, set[str]]:
        """Asset id -> the kinds ("wallet", "staking", "total") registered for it."""
        entry_id = self._entry.entry_id
        out: dict[str, set[str]] = {}
        ent_reg = er.async_get(self._hass)
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry_id):
            key = managed_asset_key(entry_id, reg_entry.unique_id)
            if key is not None:
                kind, asset_id = key
                out.setdefault(asset_id, set()).add(kind)
        return out

    def _registered_category(self, asset_id: str) -> str | None:
        """The category of the wallet group the sensors of `asset_id` are
        registered in; None while they are in none (a wallet migrated from
        version 1) or not registered at all."""
        entry_id = self._entry.entry_id
        ent_reg = er.async_get(self._hass)
        for unique_id in (make(entry_id, asset_id) for make in _UNIQUE_IDS.values()):
            entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id is None:
                continue
            group = self._entry.subentries.get(ent_reg.async_get(entity_id).config_subentry_id)
            if group is not None and group.subentry_type == SUBENTRY_TYPE_WALLET_GROUP:
                return group.unique_id
        return None

    def _current_earn(self) -> EarnData | None:
        earn = self._runtime.earn
        return earn.data if earn.last_update_success else None

    def _remove(self, asset_id: str, kinds: tuple[str, ...], *, device: bool) -> None:
        entry_id = self._entry.entry_id
        ent_reg = er.async_get(self._hass)
        for kind in kinds:
            entity_id = ent_reg.async_get_entity_id(
                "sensor", DOMAIN, _UNIQUE_IDS[kind](entry_id, asset_id)
            )
            if entity_id is not None:
                ent_reg.async_remove(entity_id)
        if device:
            dev_reg = dr.async_get(self._hass)
            found = find_entry_device(
                dev_reg, entry_id, wallet_device_identifier(entry_id, asset_id)
            )
            if found is not None:
                dev_reg.async_remove_device(found.id)

    @callback
    def async_reconcile(self) -> None:
        portfolio = self._runtime.portfolio
        data: PortfolioData | None = portfolio.data
        if not portfolio.last_update_success or data is None:
            return
        self._forget_wallets_without_group()
        entry_id = self._entry.entry_id
        registered = self._registered()
        earn = self._current_earn()
        # Category -> the sensors to add to its group.
        new: dict[str, list[SensorEntity]] = {}

        for asset_id in data.wallet_ids:
            asset = data.assets[asset_id]
            entities: list[SensorEntity] = []
            if asset_id not in self._wallets:
                # A wallet registered in a group stays in it, whatever its
                # asset's category says now. Moving its device to another
                # group would list it in both on Home Assistant 2025.5;
                # 2026.9 warns about such a move, and 2027.8 will refuse it.
                sits_in = self._registered_category(asset_id)
                self._wallets[asset_id] = asset_category(asset) if sits_in is None else sits_in
                entities.append(
                    WalletSensor(portfolio, entry_id, self._currency, asset, self.has_total)
                )
            applies = staking_applies(data.holdings[asset_id], earn)
            kinds = registered.get(asset_id, set())
            wanted = applies is True or (applies is None and "staking" in kinds)
            if wanted and asset_id not in self._staking:
                self._staking.add(asset_id)
                entities.append(
                    StakingSensor(
                        portfolio, self._runtime.earn, self._runtime.rewards,
                        entry_id, self._currency, asset,
                    )
                )
                entities.append(WalletTotalSensor(portfolio, entry_id, self._currency, asset))
            elif applies is False and (asset_id in self._staking or kinds & {"staking", "total"}):
                self._staking.discard(asset_id)
                self._remove(asset_id, ("staking", "total"), device=False)
            if entities:
                new.setdefault(self._wallets[asset_id], []).extend(entities)

        # An asset whose balances could not be read this refresh has no entry
        # in `data.holdings`, yet counts as held (PortfolioData.held), never
        # as a miss.
        held = data.held
        asked_at = data.requested_at or dt_util.utcnow()
        for asset_id in held:
            self._misses.pop(asset_id, None)
        for asset_id in (set(registered) | set(self._wallets)) - held:
            misses, since = self._misses.get(asset_id, (0, asked_at))
            misses += 1
            if not confirmed(misses, since, asked_at):
                self._misses[asset_id] = (misses, since)
                continue
            self._misses.pop(asset_id, None)
            self._wallets.pop(asset_id, None)
            self._staking.discard(asset_id)
            self._remove(asset_id, ("wallet", "staking", "total"), device=True)

        # One call per group: the group must exist before its sensors are
        # added, and the registry files each sensor and its device under it --
        # moving a sensor that is registered already, such as a migrated one.
        for category, entities in new.items():
            group = async_get_or_create_wallet_group(
                self._hass, self._entry, category, self._runtime.group_titles
            )
            self._add_entities(entities, config_subentry_id=group.subentry_id)
        self._remove_empty_groups()

    def _forget_wallets_without_group(self) -> None:
        """Forget every tracked wallet whose group is gone -- deleted by the
        user, its devices and entities with it -- so that this refresh adds
        the wallet again, as if it were new: its miss count goes too."""
        for asset_id, category in list(self._wallets.items()):
            if group_of_category(self._entry, SUBENTRY_TYPE_WALLET_GROUP, category) is None:
                del self._wallets[asset_id]
                self._staking.discard(asset_id)
                self._misses.pop(asset_id, None)

    def _remove_empty_groups(self) -> None:
        """Remove every wallet group that no tracked wallet belongs to and
        that holds nothing of this entry any more.

        A wallet this manager does not track yet -- one registered before a
        restart, whose asset is unnamed for now or has been sold since --
        still has its sensors in its group, and keeps the group until they go.
        """
        in_use = set(self._wallets.values())
        occupied = entities_by_group(self._hass, self._entry)
        for group in groups_of_type(self._entry, SUBENTRY_TYPE_WALLET_GROUP):
            if group.unique_id in in_use or group.subentry_id in occupied:
                continue
            self._hass.config_entries.async_remove_subentry(self._entry, group.subentry_id)


@callback
def _keep_polling() -> None:
    """No-op listener that keeps the Earn coordinator's periodic refresh alive.

    DataUpdateCoordinator only schedules its next refresh while it has at
    least one listener, and stops once the last one unsubscribes. The Earn
    coordinator's only other listeners are StakingSensors, so an entry with
    none registered -- nothing staked and nothing offered, or the last
    Staking sensor was just removed -- would freeze its catalogue forever at
    whatever the first refresh returned (or at `None` if that one failed),
    even though the manager reads it on every portfolio refresh: an Earn
    product offered later gives a wallet its Staking and Total sensors even
    with nothing staked yet.
    """


async def async_setup_portfolio_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    add_entities: Callable[..., None],
) -> None:
    """The Portfolio device's sensors, outside every group, then the wallets
    the manager keeps current in their groups."""
    runtime: PortfolioRuntime = entry.runtime_data
    currency = entry.data[CONF_CURRENCY]
    add_entities(
        [
            PortfolioTotalSensor(runtime.portfolio, entry.entry_id, currency),
            PortfolioCashSensor(runtime.portfolio, entry.entry_id, currency),
            PortfolioCashPlusSensor(runtime.portfolio, entry.entry_id, currency),
            *(
                PortfolioReturnSensor(runtime.history, entry.entry_id, timeframe)
                for timeframe in PORTFOLIO_TIMEFRAMES
            ),
        ]
    )
    manager = PortfolioEntityManager(hass, entry, runtime, currency, add_entities)
    manager.async_reconcile()
    entry.async_on_unload(runtime.portfolio.async_add_listener(manager.async_reconcile))
    # Keep Earn polling even without a Staking sensor around (see
    # _keep_polling). Not `manager.async_reconcile` itself: misses are
    # counted once per call, so subscribing it a second time here would
    # remove a holding after fewer than WALLET_REMOVAL_MISSES portfolio
    # refreshes.
    entry.async_on_unload(runtime.earn.async_add_listener(_keep_polling))
