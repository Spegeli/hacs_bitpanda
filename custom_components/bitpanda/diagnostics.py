"""Diagnostics support for Bitpanda."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_API_KEY,
    CONF_CURRENCY,
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DOMAIN,
)

_REDACTED = "**REDACTED**"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator_data = hass.data[DOMAIN][entry.entry_id]
    price_coordinator = coordinator_data["price_coordinator"]
    wallet_coordinator = coordinator_data["wallet_coordinator"]

    tracked_assets = entry.options.get(CONF_TRACKED_ASSETS, [])
    tracked_wallets = entry.options.get(CONF_TRACKED_WALLETS, [])

    return {
        "config": {
            CONF_API_KEY: _REDACTED,
            CONF_CURRENCY: entry.data.get(CONF_CURRENCY),
        },
        "options": {
            "tracked_assets_count": len(tracked_assets),
            "tracked_assets": tracked_assets,
            "tracked_wallets_count": len(tracked_wallets),
            "tracked_wallets": tracked_wallets,
        },
        "coordinators": {
            "prices": {
                "last_update_success": price_coordinator.last_update_success,
                "last_update": str(price_coordinator.last_update_success_time),
                "asset_count": len(price_coordinator.data) if price_coordinator.data else 0,
            },
            "wallets": {
                "last_update_success": wallet_coordinator.last_update_success,
                "last_update": str(wallet_coordinator.last_update_success_time),
            },
        },
    }
