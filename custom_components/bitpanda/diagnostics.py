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
    history,
) -> dict[str, Any]:
    """Assemble the diagnostics payload. The API key never appears."""
    holdings = portfolio.data.holdings if portfolio.data else {}
    # Explicit `is not None`, not `bool(...)`: a derived rate of exactly 0.0
    # is falsy, so `bool(portfolio.data and portfolio.data.rate)` would report
    # "not derived" for a rate that had, in fact, been derived. `derive_rate`
    # (fx.py) rejects zero and negative amounts, so it never returns 0.0, but
    # that guarantee lives in another module and this diagnostic must not
    # silently depend on it.
    rate_derived = portfolio.data.rate is not None if portfolio.data else False
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
                "rate_derived": rate_derived,
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
            },
            "history": {
                "last_update_success": history.last_update_success,
                "timeframes_covered": len(history.data or {}),
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
        history=store["history_coordinator"],
    )
