"""Sensors of the Portfolio service.

Every value is in the Portfolio currency, as Bitpanda reports it. Units of an
asset are attributes, never states.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CURRENCY,
    DEFAULT_CURRENCY,
    DOMAIN,
    PORTFOLIO_TIMEFRAMES,
    WALLET_REMOVAL_MISSES,
)
from .naming import (
    asset_display_label,
    managed_asset_id,
    portfolio_device_identifier,
    portfolio_entity_id,
    portfolio_unique_id,
    return_key,
    staking_entity_id,
    staking_unique_id,
    total_entity_id,
    total_unique_id,
    wallet_device_identifier,
    wallet_entity_id,
    wallet_unique_id,
)
from .portfolio_coordinator import PortfolioRuntime
from .portfolio_model import DECIMALS, EarnData, Holding, PortfolioData, staking_applies

_CONFIGURATION_URL = "https://www.bitpanda.com"


def portfolio_device_info(entry_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, portfolio_device_identifier(entry_id))},
        name="Portfolio",
        manufacturer="Bitpanda",
        model="Portfolio",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=_CONFIGURATION_URL,
    )


def wallet_device_info(entry_id: str, asset: dict) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, wallet_device_identifier(entry_id, asset["id"]))},
        name=f"{asset_display_label(asset)} Wallet",
        manufacturer="Bitpanda",
        model="Wallet",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=_CONFIGURATION_URL,
    )


# --- Portfolio device ------------------------------------------------------------


class _PortfolioFigure(CoordinatorEntity, SensorEntity):
    """One figure of the whole account."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
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

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None


class PortfolioTotalSensor(_PortfolioFigure):
    """Every holding, Cash Plus included, plus all fiat."""

    _key = "total"
    _attr_translation_key = "total_value"
    _attr_icon = "mdi:chart-pie"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {"wallet_count": len(data.wallet_ids) if data else 0}


class PortfolioCashSensor(_PortfolioFigure):
    """Sum of the fiat balances (`balance`: locked fiat is still cash)."""

    _key = "cash"
    _attr_translation_key = "cash"
    _attr_icon = "mdi:cash"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.cash


class PortfolioCashPlusSensor(_PortfolioFigure):
    """Value of the Cash Plus holdings. Unknown while any holding is unnamed."""

    _key = "cash_plus"
    _attr_translation_key = "cash_plus"
    _attr_icon = "mdi:piggy-bank"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.cash_plus


class PortfolioReturnSensor(CoordinatorEntity, SensorEntity):
    """The portfolio's return over one timeframe, in percent."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:chart-line"

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
        return (self.coordinator.data or {}).get(self._timeframe)

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None


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
        return super().available and self.native_value is not None

    def _attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "asset": self._asset.get("symbol"),
            "asset_name": self._asset.get("name"),
        }
        holding = self._holding
        if holding is not None:
            attrs["units"] = self._units(holding)
        return attrs


class WalletSensor(_WalletPart):
    """Value of the unstaked units. Takes its device's name: "Vision (VSN) Wallet".

    `has_total` says whether this asset currently has a Total sensor; while it
    has none, the position performance is shown here instead.
    """

    _attr_name = None
    _attr_icon = "mdi:wallet"

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
    _attr_icon = "mdi:sprout"

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
        rewards = (self._rewards.data or {}).get(self._asset_id)
        if rewards is not None and rewards.count:
            attrs["rewards_gross"] = rewards.gross
            attrs["rewards_fee"] = rewards.fee
            attrs["rewards_net"] = rewards.net
            attrs["rewards_count"] = rewards.count
            attrs["rewards_last_at"] = rewards.last_at
        return attrs


class WalletTotalSensor(_WalletPart):
    """Value of the whole position, with its performance."""

    _attr_translation_key = "wallet_total"
    _attr_icon = "mdi:sigma"

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
    """Adds and removes wallet devices as holdings appear and disappear.

    Runs after every portfolio refresh; a failed refresh changes nothing.
    A holding absent from WALLET_REMOVAL_MISSES consecutive successful
    refreshes loses its sensors and device -- a wallet migrated from version
    1 whose asset is no longer held included. Only unique_ids that name an
    asset UUID are ever removed (naming.managed_asset_id): a legacy wallet
    the migration could not resolve is left for the user.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        runtime: PortfolioRuntime,
        currency: str,
        add_entities: Callable[[list[SensorEntity]], None],
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._runtime = runtime
        self._currency = currency
        self._add_entities = add_entities
        self._wallets: set[str] = set()
        self._staking: set[str] = set()
        self._misses: dict[str, int] = {}

    def has_total(self, asset_id: str) -> bool:
        return asset_id in self._staking

    def _registered(self) -> dict[str, set[str]]:
        """Asset id -> the kinds ("wallet", "staking", "total") registered for it."""
        entry_id = self._entry.entry_id
        out: dict[str, set[str]] = {}
        ent_reg = er.async_get(self._hass)
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry_id):
            asset_id = managed_asset_id(entry_id, reg_entry.unique_id)
            if asset_id is not None:
                kind = reg_entry.unique_id[len(entry_id) + 1 :].split("_", 1)[0]
                out.setdefault(asset_id, set()).add(kind)
        return out

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
            found = dev_reg.async_get_device(
                identifiers={(DOMAIN, wallet_device_identifier(entry_id, asset_id))}
            )
            if found is not None:
                dev_reg.async_remove_device(found.id)

    @callback
    def async_reconcile(self) -> None:
        portfolio = self._runtime.portfolio
        data: PortfolioData | None = portfolio.data
        if not portfolio.last_update_success or data is None:
            return
        entry_id = self._entry.entry_id
        registered = self._registered()
        earn = self._current_earn()
        new: list[SensorEntity] = []

        for asset_id in data.wallet_ids:
            asset = data.assets[asset_id]
            if asset_id not in self._wallets:
                self._wallets.add(asset_id)
                new.append(
                    WalletSensor(portfolio, entry_id, self._currency, asset, self.has_total)
                )
            applies = staking_applies(data.holdings[asset_id], earn)
            kinds = registered.get(asset_id, set())
            wanted = applies is True or (applies is None and "staking" in kinds)
            if wanted and asset_id not in self._staking:
                self._staking.add(asset_id)
                new.append(
                    StakingSensor(
                        portfolio, self._runtime.earn, self._runtime.rewards,
                        entry_id, self._currency, asset,
                    )
                )
                new.append(WalletTotalSensor(portfolio, entry_id, self._currency, asset))
            elif applies is False and (asset_id in self._staking or kinds & {"staking", "total"}):
                self._staking.discard(asset_id)
                self._remove(asset_id, ("staking", "total"), device=False)

        # An asset in `unparsed_assets` is still held -- its record just did
        # not resolve this refresh -- so it counts as present here even
        # though it has no entry in `data.holdings` (Task 3 ruling).
        held = set(data.holdings) | data.unparsed_assets
        for asset_id in held:
            self._misses.pop(asset_id, None)
        for asset_id in (set(registered) | self._wallets) - held:
            misses = self._misses.get(asset_id, 0) + 1
            if misses < WALLET_REMOVAL_MISSES:
                self._misses[asset_id] = misses
                continue
            self._misses.pop(asset_id, None)
            self._wallets.discard(asset_id)
            self._staking.discard(asset_id)
            self._remove(asset_id, ("wallet", "staking", "total"), device=True)

        if new:
            self._add_entities(new)


async def async_setup_portfolio_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    add_entities: Callable[[list[SensorEntity]], None],
) -> None:
    """The Portfolio device's sensors, then the wallets the manager keeps current."""
    runtime: PortfolioRuntime = entry.runtime_data
    currency = entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY)
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
