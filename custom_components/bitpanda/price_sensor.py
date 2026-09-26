"""Sensors of the Price Tracker: one per tracked asset and currency.

EUR comes straight from Bitpanda's ticker. Every other currency is the EUR
price times the ECB reference rate of that currency. Every sensor keeps
long-term statistics as `total`, the only state class Home Assistant allows
for the monetary device class; each sensor's currency never changes.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .assets import asset_attributes
from .const import (
    CHANGE_24H_UPDATE_INTERVAL,
    CONF_ASSETS,
    CONF_EXTRA_CURRENCIES,
    DOMAIN,
    SUBENTRY_TYPE_PRICE_GROUP,
)
from .devices import device_identifiers
from .groups import groups_of_type, tracked_assets
from .naming import (
    price_device_asset_id,
    price_device_identifier,
    price_device_name,
    price_entity_id,
    price_key,
    price_unique_id,
)
from .ecb import EcbRates
from .price_coordinator import (
    EcbCoordinator,
    PriceTrackerConfigEntry,
    PriceTrackerRuntime,
    TickerCoordinator,
    convert_price,
)

_LOGGER = logging.getLogger(__name__)


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


def price_device_info(entry_id: str, asset: dict[str, Any]) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, price_device_identifier(entry_id, asset["id"]))},
        name=price_device_name(asset),
        manufacturer="Bitpanda",
        model="Price Tracker",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://www.bitpanda.com",
    )


def tracked_currencies(entry: ConfigEntry) -> list[str]:
    """EUR, always, then the configured extras."""
    return ["EUR", *entry.options.get(CONF_EXTRA_CURRENCIES, [])]


class PriceSensor(CoordinatorEntity[TickerCoordinator], SensorEntity):
    """Price of one asset in one currency.

    Named by its currency after its device, so it reads "Bitcoin (BTC) Price
    Tracker EUR" on every Home Assistant version.
    """

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_translation_key = "price"

    def __init__(
        self,
        tickers: TickerCoordinator,
        ecb: EcbCoordinator | None,
        entry_id: str,
        asset: dict[str, Any],
        currency: str,
    ) -> None:
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
    def _rates(self) -> EcbRates | None:
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

    async def _async_update_24h_change(self, _: datetime | None = None) -> None:
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
                # States, not dicts: neither minimal_response nor
                # compressed_state_format is asked for.
                self._price_24h_ago = float(cast(State, states[-1]).state)
        except Exception as err:  # noqa: BLE001 - optional data, never fatal
            _LOGGER.debug(
                "No 24 h history for %s: %s", self.entity_id, type(err).__name__
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            **asset_attributes(self._asset),
            "trading_pair": f"{self._asset.get('symbol')}/{self._currency}",
        }
        if self._currency != "EUR":
            rate = self._rate
            if rate is None:
                # A status key, translated through state_attributes.conversion.state
                # (entity.sensor.price in strings.json) -- never a raw sentence.
                attrs["conversion"] = "no_rate"
            else:
                attrs["conversion_rate"] = rate
                # The rate came from these rates.
                attrs["rate_date"] = cast(EcbRates, self._rates).date
                attrs["rate_source"] = "ECB"
        current = self.native_value
        if self._price_24h_ago and current is not None:
            attrs["change_24h_pct"] = round(
                (current - self._price_24h_ago) / self._price_24h_ago * 100, 2
            )
            attrs["price_24h_ago"] = self._price_24h_ago
        return attrs


def _remove_untracked(hass: HomeAssistant, entry: ConfigEntry, currencies: list[str]) -> None:
    """Remove the price sensors of a currency or asset no longer tracked, and
    the devices of assets no longer tracked.

    Their history is kept: tracking the asset or currency again brings back
    the same entity IDs. Only UUID-based IDs of this entry are touched, and
    a device goes only when no asset it names -- judged by every identifier
    it carries -- is tracked any more.
    """
    tracked = tracked_assets(entry)
    ent_reg = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        key = price_key(entry.entry_id, reg_entry.unique_id)
        if key is not None and (key[0] not in tracked or key[1] not in currencies):
            ent_reg.async_remove(reg_entry.entity_id)
    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        named = {
            asset_id
            for identifier in device_identifiers(device)
            if (asset_id := price_device_asset_id(entry.entry_id, identifier)) is not None
        }
        if named and named.isdisjoint(tracked):
            dev_reg.async_remove_device(device.id)


async def async_setup_price_entities(
    hass: HomeAssistant,
    entry: PriceTrackerConfigEntry,
    add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """One sensor per tracked asset and currency, bound to the asset's group.

    Whatever is no longer tracked is removed first (_remove_untracked).
    """
    runtime: PriceTrackerRuntime = entry.runtime_data
    currencies = tracked_currencies(entry)
    _remove_untracked(hass, entry, currencies)
    for group in groups_of_type(entry, SUBENTRY_TYPE_PRICE_GROUP):
        add_entities(
            [
                PriceSensor(runtime.tickers, runtime.ecb, entry.entry_id, asset, currency)
                for asset in group.data[CONF_ASSETS].values()
                for currency in currencies
            ],
            config_subentry_id=group.subentry_id,
        )
