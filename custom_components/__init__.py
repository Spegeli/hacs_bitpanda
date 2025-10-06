"""The Bitpanda integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BitpandaApiClient
from .const import (
    CONF_API_KEY,
    CONF_CURRENCY,
    DOMAIN,
    PRICE_UPDATE_INTERVAL,
    WALLET_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bitpanda from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    currency = entry.data[CONF_CURRENCY]
    
    session = async_get_clientsession(hass)
    client = BitpandaApiClient(api_key, session)

    # Create coordinators for different update intervals
    async def async_update_prices():
        """Fetch price data from API."""
        try:
            return await client.async_get_ticker()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def async_update_wallets():
        """Fetch wallet data from API."""
        try:
            asset_wallets = await client.async_get_asset_wallets()
            fiat_wallets = await client.async_get_fiat_wallets()
            crypto_wallets = await client.async_get_crypto_wallets()
            
            return {
                "asset_wallets": asset_wallets,
                "fiat_wallets": fiat_wallets,
                "crypto_wallets": crypto_wallets,
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    price_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_prices",
        update_method=async_update_prices,
        update_interval=PRICE_UPDATE_INTERVAL,
        config_entry=entry,
    )

    wallet_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_wallets",
        update_method=async_update_wallets,
        update_interval=WALLET_UPDATE_INTERVAL,
        config_entry=entry,
    )

    # Fetch initial data
    await price_coordinator.async_refresh()
    await wallet_coordinator.async_refresh()
    
    # Check if first refresh was successful
    if price_coordinator.last_update_success is False:
        raise ConfigEntryNotReady("Failed to fetch initial price data")
    if wallet_coordinator.last_update_success is False:
        raise ConfigEntryNotReady("Failed to fetch initial wallet data")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "price_coordinator": price_coordinator,
        "wallet_coordinator": wallet_coordinator,
        "currency": currency,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # GEÄNDERT: Verwende async_update_options statt async_reload_entry
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # GEÄNDERT: Reload nur die Sensor-Plattform, nicht die ganze Integration
    await hass.config_entries.async_reload(entry.entry_id)
