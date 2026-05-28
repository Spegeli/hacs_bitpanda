"""Sensor platform for Bitpanda."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CHANGE_24H_UPDATE_INTERVAL,
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _parse_wallet_id(wallet_id: str) -> tuple[str, str]:
    """Parse wallet_id into (category, symbol)."""
    parts = wallet_id.split("_")
    if len(parts) >= 3:
        return f"{parts[0]}_{parts[1]}", "_".join(parts[2:])
    return parts[0], "_".join(parts[1:])


def _get_wallet_balance(coordinator_data: dict, category: str, symbol: str) -> str | None:
    """Get balance from wallet coordinator data."""
    if not coordinator_data:
        return None

    if category == "fiat":
        fiat_data = coordinator_data.get("fiat_wallets", {})
        if "data" in fiat_data:
            for wallet in fiat_data["data"]:
                if wallet["attributes"].get("fiat_symbol") == symbol:
                    return wallet["attributes"].get("balance")
        return None

    asset_data = coordinator_data.get("asset_wallets", {})
    if "data" not in asset_data or "attributes" not in asset_data["data"]:
        return None

    parts = category.split("_", 1)
    parent_category = parts[0]
    sub_category = parts[1] if len(parts) > 1 else None
    category_data = asset_data["data"]["attributes"].get(parent_category)

    if not category_data:
        return None

    if sub_category and isinstance(category_data, dict):
        sub_data = category_data.get(sub_category)
        if sub_data and "attributes" in sub_data and "wallets" in sub_data["attributes"]:
            for wallet in sub_data["attributes"]["wallets"]:
                if wallet["attributes"].get("cryptocoin_symbol") == symbol:
                    return wallet["attributes"].get("balance")
    elif isinstance(category_data, dict) and "attributes" in category_data:
        for wallet in category_data["attributes"].get("wallets", []):
            if wallet["attributes"].get("cryptocoin_symbol") == symbol:
                return wallet["attributes"].get("balance")

    return None


def _get_asset_price(price_data: dict | None, symbol: str, currency: str) -> str | None:
    """Get price from price coordinator data."""
    if price_data and symbol in price_data:
        return price_data[symbol].get(currency)
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Bitpanda sensors based on a config entry."""
    coordinator_data = hass.data[DOMAIN][config_entry.entry_id]
    price_coordinator = coordinator_data["price_coordinator"]
    wallet_coordinator = coordinator_data["wallet_coordinator"]
    currency = coordinator_data["currency"]

    entities: list[SensorEntity] = []

    tracked_assets = config_entry.options.get(CONF_TRACKED_ASSETS, [])
    for asset in tracked_assets:
        entities.append(
            BitpandaPriceSensor(price_coordinator, config_entry, asset, currency)
        )

    tracked_wallets = config_entry.options.get(CONF_TRACKED_WALLETS, [])
    for wallet_id in tracked_wallets:
        entities.append(
            BitpandaWalletSensor(
                wallet_coordinator, price_coordinator, config_entry, wallet_id, currency
            )
        )

    if tracked_wallets:
        entities.append(
            BitpandaPortfolioSensor(
                wallet_coordinator, price_coordinator, config_entry, tracked_wallets, currency
            )
        )

    async_add_entities(entities)


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


class BitpandaPriceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Bitpanda price sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, asset, currency):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._asset = asset
        self._currency = currency
        self._attr_name = f"{asset}/{currency}"
        self._attr_unique_id = f"{config_entry.entry_id}_{asset}_price_{currency}"
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
        # Schedule recurring update every 15 minutes
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
            from homeassistant.components.recorder.history import get_significant_states

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
        """Return the state of the sensor."""
        if self.coordinator.data and self._asset in self.coordinator.data:
            price_data = self.coordinator.data[self._asset]
            if self._currency in price_data:
                try:
                    return float(price_data[self._currency])
                except (ValueError, TypeError):
                    return None
        return None

    @property
    def suggested_display_precision(self) -> int:
        """Return the suggested display precision based on actual decimal places."""
        value = self.native_value
        if value is None or value == 0:
            return 2

        if self.coordinator.data and self._asset in self.coordinator.data:
            price_data = self.coordinator.data[self._asset]
            if self._currency in price_data:
                original_value = str(price_data[self._currency])
                if '.' in original_value:
                    decimal_places = len(original_value.split('.')[1])
                    return min(decimal_places, 8)

        if value >= 10:
            return 2
        elif value >= 1:
            return 4
        elif value >= 0.1:
            return 5
        elif value >= 0.001:
            return 6
        elif value >= 0.0001:
            return 7
        else:
            return 8

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not (self.coordinator.data and self._asset in self.coordinator.data):
            return {}

        attrs: dict[str, Any] = {
            "asset": self._asset,
            "trading_pair": f"{self._asset}/{self._currency}",
            "all_prices": self.coordinator.data[self._asset],
        }

        if self._price_24h_ago is not None:
            current = self.native_value
            if current is not None and self._price_24h_ago > 0:
                attrs["change_24h_pct"] = round(
                    (current - self._price_24h_ago) / self._price_24h_ago * 100, 2
                )
                attrs["price_24h_ago"] = self._price_24h_ago

        return attrs


class BitpandaWalletSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Bitpanda wallet sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        wallet_coordinator,
        price_coordinator,
        config_entry,
        wallet_id,
        currency,
    ):
        """Initialize the sensor."""
        super().__init__(wallet_coordinator)
        self._price_coordinator = price_coordinator
        self._currency = currency
        self._category, self._symbol = _parse_wallet_id(wallet_id)
        self._attr_name = f"{self._symbol} Wallet"
        self._attr_unique_id = f"{config_entry.entry_id}_wallet_{wallet_id}"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = currency
        self._attr_icon = "mdi:wallet"
        self._attr_suggested_display_precision = 2
        self._attr_device_info = _wallet_device_info(config_entry)

    async def async_added_to_hass(self) -> None:
        """Subscribe to wallet coordinator and price coordinator."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._price_coordinator.async_add_listener(
                self._handle_coordinator_update, None,
            )
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        balance = _get_wallet_balance(self.coordinator.data, self._category, self._symbol)
        if balance is None:
            return None

        if self._category == "fiat":
            try:
                return float(balance)
            except (ValueError, TypeError):
                return None

        price = _get_asset_price(self._price_coordinator.data, self._symbol, self._currency)
        if price is None:
            return balance

        try:
            return float(balance) * float(price)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        balance = _get_wallet_balance(self.coordinator.data, self._category, self._symbol)
        price = _get_asset_price(self._price_coordinator.data, self._symbol, self._currency)

        attributes: dict[str, Any] = {
            "asset": self._symbol,
            "balance": balance,
        }

        if self._category != "fiat":
            attributes["price"] = price

        return attributes


class BitpandaPortfolioSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing the total value of all tracked wallets."""

    _attr_has_entity_name = True

    def __init__(
        self,
        wallet_coordinator,
        price_coordinator,
        config_entry,
        tracked_wallets: list[str],
        currency: str,
    ):
        """Initialize the portfolio sensor."""
        super().__init__(wallet_coordinator)
        self._price_coordinator = price_coordinator
        self._tracked_wallets = tracked_wallets
        self._currency = currency
        self._attr_name = "Portfolio Total"
        self._attr_unique_id = f"{config_entry.entry_id}_portfolio_total"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = currency
        self._attr_icon = "mdi:chart-pie"
        self._attr_suggested_display_precision = 2
        self._attr_device_info = _wallet_device_info(config_entry)

    async def async_added_to_hass(self) -> None:
        """Subscribe to both coordinators."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._price_coordinator.async_add_listener(
                self._handle_coordinator_update, None,
            )
        )

    @property
    def native_value(self) -> float | None:
        """Return the total portfolio value across all tracked wallets."""
        total = 0.0
        has_value = False

        for wallet_id in self._tracked_wallets:
            category, symbol = _parse_wallet_id(wallet_id)
            balance = _get_wallet_balance(self.coordinator.data, category, symbol)

            if balance is None:
                continue

            try:
                if category == "fiat":
                    total += float(balance)
                    has_value = True
                else:
                    price = _get_asset_price(
                        self._price_coordinator.data, symbol, self._currency
                    )
                    if price is not None:
                        total += float(balance) * float(price)
                        has_value = True
            except (ValueError, TypeError):
                continue

        return round(total, 2) if has_value else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return breakdown of wallet values as attributes."""
        breakdown: dict[str, float] = {}

        for wallet_id in self._tracked_wallets:
            category, symbol = _parse_wallet_id(wallet_id)
            balance = _get_wallet_balance(self.coordinator.data, category, symbol)

            if balance is None:
                continue

            try:
                if category == "fiat":
                    breakdown[symbol] = round(float(balance), 2)
                else:
                    price = _get_asset_price(
                        self._price_coordinator.data, symbol, self._currency
                    )
                    if price is not None:
                        breakdown[symbol] = round(float(balance) * float(price), 2)
            except (ValueError, TypeError):
                continue

        return {
            "wallet_count": len(self._tracked_wallets),
            "breakdown": breakdown,
        }
