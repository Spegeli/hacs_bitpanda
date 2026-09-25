"""Sensors of the Price Tracker: one per tracked asset and currency.

EUR comes straight from Bitpanda's ticker. Every other currency is the EUR
price times the ECB reference rate of that currency.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CHANGE_24H_UPDATE_INTERVAL,
    CONF_ASSET,
    CONF_EXTRA_CURRENCIES,
    DOMAIN,
    SUBENTRY_TYPE_ASSET,
)
from .naming import (
    asset_display_label,
    price_device_identifier,
    price_entity_id,
    price_unique_id,
    price_unique_id_currency,
)
from .price_coordinator import PriceTrackerRuntime, convert_price

_LOGGER = logging.getLogger(__name__)

_NO_RATE = "no ECB exchange rate for this currency has been loaded yet"


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


def price_device_info(entry_id: str, asset: dict) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, price_device_identifier(entry_id, asset["id"]))},
        name=asset_display_label(asset),
        manufacturer="Bitpanda",
        model="Price Tracker",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://www.bitpanda.com",
    )


def tracked_currencies(entry: ConfigEntry) -> list[str]:
    """EUR, always, then the configured extras."""
    return ["EUR", *entry.options.get(CONF_EXTRA_CURRENCIES, [])]


class PriceSensor(CoordinatorEntity, SensorEntity):
    """Price of one asset in one currency.

    Named by its currency and inherits the asset label from its device, so
    it reads "Bitcoin (BTC) EUR" on every Home Assistant version.
    """

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_icon = "mdi:chart-line"

    def __init__(self, tickers, ecb, entry_id: str, asset: dict, currency: str) -> None:
        super().__init__(tickers)
        self._ecb = ecb
        self._asset = asset
        self._asset_id = asset["id"]
        self._currency = currency
        self._attr_name = currency
        self._attr_unique_id = price_unique_id(entry_id, asset["id"], currency)
        self.entity_id = price_entity_id(asset, currency)
        self._attr_native_unit_of_measurement = currency
        self._attr_device_info = price_device_info(entry_id, asset)
        self._price_24h_ago: float | None = None

    @property
    def _rates(self):
        """The last ECB rates, current or not: DataUpdateCoordinator keeps the
        last data after a failed refresh, and `rate_date` shows its age."""
        return None if self._ecb is None else self._ecb.data

    @property
    def _rate(self) -> float | None:
        rates = self._rates
        return None if rates is None else rates.rates.get(self._currency)

    @property
    def available(self) -> bool:
        return super().available and self._asset_id in (self.coordinator.data or {})

    @property
    def native_value(self) -> float | None:
        eur = (self.coordinator.data or {}).get(self._asset_id)
        if eur is None or self._currency == "EUR":
            return eur
        rate = self._rate
        # No rate: no value. An EUR figure under this sensor's unit would be
        # off by the exchange rate.
        return None if rate is None else convert_price(eur, rate)

    @property
    def suggested_display_precision(self) -> int:
        return display_precision(self.native_value)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._ecb is not None and self._currency != "EUR":
            self.async_on_remove(
                self._ecb.async_add_listener(self._handle_coordinator_update, None)
            )
        await self._async_update_24h_change()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_update_24h_change, CHANGE_24H_UPDATE_INTERVAL
            )
        )

    async def _async_update_24h_change(self, _=None) -> None:
        """Read this sensor's own value from about 24 hours ago from the recorder."""
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.history import get_significant_states

            now = dt_util.utcnow()
            history = await get_instance(self.hass).async_add_executor_job(
                get_significant_states,
                self.hass,
                now - timedelta(hours=24, minutes=5),
                now - timedelta(hours=23, minutes=55),
                [self.entity_id],
            )
            states = history.get(self.entity_id, [])
            if states:
                self._price_24h_ago = float(states[-1].state)
        except Exception as err:  # noqa: BLE001 - optional data, never fatal
            _LOGGER.debug(
                "No 24 h history for %s: %s", self.entity_id, type(err).__name__
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        symbol = self._asset.get("symbol")
        attrs: dict[str, Any] = {
            "asset": symbol,
            "asset_name": self._asset.get("name"),
            "trading_pair": f"{symbol}/{self._currency}",
        }
        if self._currency != "EUR":
            rate = self._rate
            if rate is None:
                attrs["conversion"] = _NO_RATE
            else:
                attrs["conversion_rate"] = rate
                attrs["rate_date"] = self._rates.date
                attrs["rate_source"] = "ECB"
        current = self.native_value
        if self._price_24h_ago and current is not None:
            attrs["change_24h_pct"] = round(
                (current - self._price_24h_ago) / self._price_24h_ago * 100, 2
            )
            attrs["price_24h_ago"] = self._price_24h_ago
        return attrs


async def async_setup_price_entities(
    hass: HomeAssistant, entry: ConfigEntry, add_entities: Callable[..., None]
) -> None:
    """One sensor per tracked asset and currency, each bound to its subentry.

    Sensors of a currency no longer configured are removed first. Their
    history is kept: re-adding the currency brings back the same entity ID.
    Sensors of a removed asset are cleared by Home Assistant together with
    its subentry.
    """
    runtime: PriceTrackerRuntime = entry.runtime_data
    currencies = tracked_currencies(entry)

    ent_reg = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        currency = price_unique_id_currency(entry.entry_id, reg_entry.unique_id)
        if currency is not None and currency not in currencies:
            ent_reg.async_remove(reg_entry.entity_id)

    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_ASSET:
            continue
        asset = subentry.data[CONF_ASSET]
        add_entities(
            [
                PriceSensor(runtime.tickers, runtime.ecb, entry.entry_id, asset, currency)
                for currency in currencies
            ],
            config_subentry_id=subentry.subentry_id,
        )
