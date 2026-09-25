"""Sensors of the Portfolio service.

Every value is in the Portfolio currency, as Bitpanda reports it. Units of an
asset are attributes, never states.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .naming import (
    asset_display_label,
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
from .portfolio_model import DECIMALS, Holding, PortfolioData

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
            attrs["apr_percent"] = round(apr * 100, 2)
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
