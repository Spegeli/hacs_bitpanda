"""Sensor platform for Bitpanda."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PortfolioData, RewardTotals

_LOGGER = logging.getLogger(__name__)


def _price_tracker_device_info(config_entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{config_entry.entry_id}_price_tracker")},
        name="Bitpanda Price Tracker",
        manufacturer="Bitpanda",
        model="Price Tracker",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://www.bitpanda.com",
    )


def _wallet_device_info(config_entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{config_entry.entry_id}_wallets")},
        name="Bitpanda Wallets",
        manufacturer="Bitpanda",
        model="Wallet Monitor",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://www.bitpanda.com",
    )


def wallet_value(data: PortfolioData | None, asset_id: str) -> float | None:
    """Return the fiat value of a holding.

    `currency_balance` was computed server-side in the requested currency, so
    it is used as given. No balance is ever multiplied by a price here: that
    is what produced issue #7, where an index wallet reported 9,251,679 EUR
    instead of 431.44.

    Returns None when the asset is absent, which happens after the position is
    sold. The entity then goes unavailable rather than raising.
    """
    if data is None:
        return None
    holding = data.holdings.get(asset_id)
    return None if holding is None else holding.value


def wallet_attributes(
    data: PortfolioData | None,
    asset_id: str,
    *,
    asset: dict | None,
    apr: float | None,
    rewards: RewardTotals | None,
) -> dict[str, Any]:
    """Build the attribute dict for a wallet sensor."""
    attrs: dict[str, Any] = {}
    if asset:
        attrs["asset"] = asset.get("symbol")
        attrs["asset_name"] = asset.get("name")

    holding = data.holdings.get(asset_id) if data else None
    if holding is None:
        return attrs

    attrs["balance"] = holding.balance
    attrs["available"] = holding.available
    attrs["staked"] = holding.staked

    for key, value in (
        ("invested_amount", holding.invested),
        ("average_buy_price", holding.avg_buy_price),
        ("total_return", holding.total_return),
        ("total_return_percent", holding.total_return_pct),
    ):
        if value is not None:
            attrs[key] = value

    if apr is not None:
        # The API reports a fraction: 0.041 means 4.1 %.
        attrs["earn_apr_percent"] = round(apr * 100, 2)

    if rewards is not None and rewards.count:
        attrs["rewards_gross"] = rewards.gross
        attrs["rewards_fee"] = rewards.fee
        attrs["rewards_net"] = rewards.net
        attrs["rewards_count"] = rewards.count
        attrs["rewards_last_at"] = rewards.last_at

    return attrs


class BitpandaWalletSensor(CoordinatorEntity, SensorEntity):
    """Value of one Bitpanda holding in the display currency."""

    _attr_has_entity_name = True

    def __init__(
        self,
        portfolio_coordinator,
        earn_coordinator,
        rewards_coordinator,
        config_entry,
        asset: dict,
        currency: str,
    ) -> None:
        super().__init__(portfolio_coordinator)
        self._earn = earn_coordinator
        self._rewards = rewards_coordinator
        self._asset = asset
        self._asset_id = asset["id"]
        self._attr_name = f"{asset['symbol']} Wallet"
        self._attr_unique_id = f"{config_entry.entry_id}_wallet_{self._asset_id}"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = currency
        self._attr_icon = "mdi:wallet"
        self._attr_suggested_display_precision = 2
        self._attr_device_info = _wallet_device_info(config_entry)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        for coordinator in (self._earn, self._rewards):
            self.async_on_remove(
                coordinator.async_add_listener(self._handle_coordinator_update, None)
            )

    @property
    def available(self) -> bool:
        return (
            super().available
            and wallet_value(self.coordinator.data, self._asset_id) is not None
        )

    @property
    def native_value(self) -> float | None:
        return wallet_value(self.coordinator.data, self._asset_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return wallet_attributes(
            self.coordinator.data,
            self._asset_id,
            asset=self._asset,
            apr=(self._earn.data or {}).get(self._asset_id),
            rewards=(self._rewards.data or {}).get(self._asset_id),
        )
