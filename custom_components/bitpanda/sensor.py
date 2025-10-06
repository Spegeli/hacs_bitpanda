"""Sensor platform for Bitpanda."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DOMAIN,
    SENSOR_TYPE_PRICE,
    SENSOR_TYPE_WALLET,
)

_LOGGER = logging.getLogger(__name__)


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

    entities = []

    # Add price sensors for tracked assets
    tracked_assets = config_entry.options.get(CONF_TRACKED_ASSETS, [])
    for asset in tracked_assets:
        entities.append(
            BitpandaPriceSensor(
                price_coordinator,
                config_entry,
                asset,
                currency,
            )
        )

    # Add wallet sensors
    tracked_wallets = config_entry.options.get(CONF_TRACKED_WALLETS, [])
    
    if tracked_wallets:
        for wallet_id in tracked_wallets:
            entities.append(
                BitpandaWalletSensor(
                    wallet_coordinator,
                    price_coordinator,
                    config_entry,
                    wallet_id,
                    currency,
                )
            )

    async_add_entities(entities)


class BitpandaPriceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Bitpanda price sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, asset, currency):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._asset = asset
        self._currency = currency
        self._attr_name = f"Bitpanda Price Tracker {asset}/{currency}"
        self._attr_unique_id = f"{config_entry.entry_id}_{asset}_price_{currency}"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = currency
        self._attr_icon = "mdi:chart-line"

    @property
    def native_value(self) -> Optional[float]:
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
        
        # Hole den Original-String-Wert aus der API
        if self.coordinator.data and self._asset in self.coordinator.data:
            price_data = self.coordinator.data[self._asset]
            if self._currency in price_data:
                original_value = str(price_data[self._currency])
                
                # Zähle die tatsächlichen Dezimalstellen
                if '.' in original_value:
                    decimal_places = len(original_value.split('.')[1])
                    # Maximal 8 Dezimalstellen für sehr kleine Werte
                    return min(decimal_places, 8)
        
        # Fallback: Berechne basierend auf dem Wertbereich
        if value >= 1000:
            return 2
        elif value >= 10:
            return 2
        elif value >= 1:
            return 4
        elif value >= 0.1:
            return 5
        elif value >= 0.01:
            return 5
        elif value >= 0.001:
            return 6
        elif value >= 0.0001:
            return 7
        else:
            return 8

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and self._asset in self.coordinator.data:
            return {
                "asset": self._asset,
                "currency": self._currency,
                "trading_pair": f"{self._asset}/{self._currency}",
                "sensor_type": "price_tracker",
                "all_prices": self.coordinator.data[self._asset],
            }
        return {}


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
        self._wallet_id = wallet_id
        self._currency = currency
        
        # Parse wallet_id (könnte "commodity_metal_XAU" oder "cryptocoin_BTC" sein)
        parts = wallet_id.split("_")
        if len(parts) >= 3:
            # Verschachtelte Kategorie (z.B. commodity_metal_XAU)
            self._category = f"{parts[0]}_{parts[1]}"
            self._symbol = "_".join(parts[2:])
        else:
            # Einfache Kategorie (z.B. cryptocoin_BTC)
            self._category = parts[0]
            self._symbol = "_".join(parts[1:])
        
        self._attr_name = f"Bitpanda {self._symbol} Wallet"
        self._attr_unique_id = f"{config_entry.entry_id}_wallet_{wallet_id}"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = currency
        self._attr_icon = "mdi:wallet"
        self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        balance = self._get_balance()
        if balance is None:
            return None
            
        # Get price from price coordinator
        price = self._get_price()
        if price is None:
            return balance  # Return balance without price conversion
            
        try:
            return float(balance) * float(price)
        except (ValueError, TypeError):
            return None

    def _get_balance(self) -> Optional[str]:
        """Get balance from wallet data."""
        if not self.coordinator.data:
            return None

        # Check fiat wallets
        if self._category == "fiat":
            fiat_data = self.coordinator.data.get("fiat_wallets", {})
            if "data" in fiat_data:
                for wallet in fiat_data["data"]:
                    if wallet["attributes"].get("fiat_symbol") == self._symbol:
                        return wallet["attributes"].get("balance")

        # Check asset wallets
        asset_data = self.coordinator.data.get("asset_wallets", {})
        if "data" in asset_data and "attributes" in asset_data["data"]:
            # Parse category (könnte "commodity_metal" oder "cryptocoin" sein)
            parts = self._category.split("_", 1)
            parent_category = parts[0]
            sub_category = parts[1] if len(parts) > 1 else None
            
            # Hole die Kategorie-Daten
            category_data = asset_data["data"]["attributes"].get(parent_category)
            
            if category_data:
                # Verschachtelte Struktur (z.B. commodity.metal, index.index)
                if sub_category and isinstance(category_data, dict):
                    sub_data = category_data.get(sub_category)
                    if sub_data and "attributes" in sub_data and "wallets" in sub_data["attributes"]:
                        for wallet in sub_data["attributes"]["wallets"]:
                            if wallet["attributes"].get("cryptocoin_symbol") == self._symbol:
                                return wallet["attributes"].get("balance")
                
                # Direkte Struktur (z.B. cryptocoin)
                elif isinstance(category_data, dict) and "attributes" in category_data and "wallets" in category_data["attributes"]:
                    for wallet in category_data["attributes"]["wallets"]:
                        if wallet["attributes"].get("cryptocoin_symbol") == self._symbol:
                            return wallet["attributes"].get("balance")

        return None

    def _get_price(self) -> Optional[str]:
        """Get price from price coordinator."""
        if (
            self._price_coordinator.data
            and self._symbol in self._price_coordinator.data
        ):
            price_data = self._price_coordinator.data[self._symbol]
            return price_data.get(self._currency)
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        balance = self._get_balance()
        price = self._get_price()
        
        return {
            "wallet_id": self._wallet_id,
            "asset": self._symbol,
            "category": self._category,
            "balance": balance,
            "price": price,
            "currency": self._currency,
        }
