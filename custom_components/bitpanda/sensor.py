"""Sensor platform for Bitpanda."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CHANGE_24H_UPDATE_INTERVAL, DOMAIN
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


def display_precision(value: float | None) -> int:
    """Return decimals to display for a price.

    Derived from magnitude, never from the price string. Every price the API
    returns has exactly 8 decimals — `90.93000000` for a stock, `0.00000032`
    for a micro-cap — so counting them yields 8 for everything.
    """
    if value is None or value == 0:
        return 2
    magnitude = abs(value)
    if magnitude >= 10:
        return 2
    if magnitude >= 1:
        return 4
    if magnitude >= 0.1:
        return 5
    if magnitude >= 0.001:
        return 6
    if magnitude >= 0.0001:
        return 7
    return 8


class BitpandaPriceSensor(CoordinatorEntity, SensorEntity):
    """Live price of one asset in the display currency."""

    _attr_has_entity_name = True

    def __init__(
        self, price_coordinator, portfolio_coordinator, config_entry,
        asset: dict, currency: str,
    ) -> None:
        super().__init__(price_coordinator)
        self._portfolio = portfolio_coordinator
        self._asset = asset
        self._asset_id = asset["id"]
        self._currency = currency
        self._attr_name = f"{asset['symbol']}/{currency}"
        self._attr_unique_id = (
            f"{config_entry.entry_id}_{self._asset_id}_price_{currency}"
        )
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = currency
        self._attr_icon = "mdi:chart-line"
        self._attr_device_info = _price_tracker_device_info(config_entry)
        self._price_24h_ago: float | None = None

    async def async_added_to_hass(self) -> None:
        """Start 24h change tracking after entity is added."""
        await super().async_added_to_hass()
        # Initial query
        await self._async_update_24h_change()
        # Schedule recurring update
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_update_24h_change,
                CHANGE_24H_UPDATE_INTERVAL,
            )
        )

    async def _async_update_24h_change(self, _=None) -> None:
        """Query the recorder for this sensor's value from ~24h ago."""
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.history import (
                get_significant_states,
            )

            now = dt_util.utcnow()
            start = now - timedelta(hours=24, minutes=5)
            end = now - timedelta(hours=23, minutes=55)

            instance = get_instance(self.hass)
            history = await instance.async_add_executor_job(
                get_significant_states,
                self.hass,
                start,
                end,
                [self.entity_id],
            )
            entity_states = history.get(self.entity_id, [])
            if entity_states:
                self._price_24h_ago = float(entity_states[-1].state)
        except Exception as err:
            _LOGGER.debug(
                "Could not fetch 24h history for %s: %s", self.entity_id, err
            )

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get(self._asset_id)

    @property
    def suggested_display_precision(self) -> int:
        return display_precision(self.native_value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "asset": self._asset.get("symbol"),
            "asset_name": self._asset.get("name"),
            "trading_pair": f"{self._asset.get('symbol')}/{self._currency}",
        }
        # Branch on the currency alone. Gating on `portfolio` as well would
        # drop the whole block while the coordinator still has no data — which
        # is every startup, before its first refresh — and a non-EUR user
        # would see an unconverted EUR price with nothing saying so.
        if self._currency != "EUR":
            portfolio = self._portfolio.data
            rate = portfolio.rate if portfolio else None
            if rate is None:
                attrs["conversion"] = (
                    "unavailable - price shown in EUR because no holding "
                    "exists to derive a rate from"
                )
            else:
                attrs["conversion_rate"] = round(rate, 8)
                attrs["conversion_source"] = "bitpanda-portfolio"

        if self._price_24h_ago is not None:
            current = self.native_value
            if current is not None and self._price_24h_ago > 0:
                attrs["change_24h_pct"] = round(
                    (current - self._price_24h_ago) / self._price_24h_ago * 100, 2
                )
                attrs["price_24h_ago"] = self._price_24h_ago

        return attrs
