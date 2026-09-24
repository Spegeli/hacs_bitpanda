"""Diagnostics support for Bitpanda."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ASSET_CACHE,
    CONF_CURRENCY,
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DOMAIN,
)

_REDACTED = "**REDACTED**"


def build_diagnostics(
    *,
    entry_data: dict,
    options: dict,
    portfolio,
    prices,
    earn,
    rewards,
    rewards_unauthorized: bool,
) -> dict[str, Any]:
    """Assemble the diagnostics payload. The API key never appears."""
    holdings = portfolio.data.holdings if portfolio.data else {}
    return {
        "config": {
            "api_key": _REDACTED,
            "currency": entry_data.get(CONF_CURRENCY),
        },
        "options": {
            "tracked_assets_count": len(options.get(CONF_TRACKED_ASSETS, [])),
            "tracked_wallets_count": len(options.get(CONF_TRACKED_WALLETS, [])),
            "asset_cache_size": len(options.get(CONF_ASSET_CACHE, {})),
        },
        "coordinators": {
            "portfolio": {
                "last_update_success": portfolio.last_update_success,
                "holdings_count": len(holdings),
                "rate_derived": bool(portfolio.data and portfolio.data.rate),
            },
            "prices": {
                "last_update_success": prices.last_update_success,
                "priced_assets": len(prices.data or {}),
            },
            "earn": {
                "last_update_success": earn.last_update_success,
                "products": len(earn.data or {}),
            },
            "rewards": {
                "last_update_success": rewards.last_update_success,
                "assets_with_rewards": len(rewards.data or {}),
                "unauthorized": rewards_unauthorized,
            },
        },
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    store = hass.data[DOMAIN][entry.entry_id]
    return build_diagnostics(
        entry_data=dict(entry.data),
        options=dict(entry.options),
        portfolio=store["portfolio_coordinator"],
        prices=store["price_coordinator"],
        earn=store["earn_coordinator"],
        rewards=store["rewards_coordinator"],
        rewards_unauthorized=store["rewards_coordinator"].unauthorized,
    )
