"""Diagnostics of both services. The API key never appears.

Only named fields are copied out of an entry -- a field added to it later
cannot leak by default.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ASSET,
    CONF_CURRENCY,
    CONF_EXTRA_CURRENCIES,
    ENTRY_TYPE_PRICE_TRACKER,
    SUBENTRY_TYPE_ASSET,
    entry_type,
)

_REDACTED = "**REDACTED**"


def _health(coordinator) -> dict[str, Any]:
    return {"last_update_success": coordinator.last_update_success}


def _portfolio(entry: ConfigEntry, runtime) -> dict[str, Any]:
    out: dict[str, Any] = {
        "service": "portfolio",
        "config": {"api_key": _REDACTED, "currency": entry.data.get(CONF_CURRENCY)},
    }
    if runtime is None:
        return out
    data = runtime.portfolio.data
    earn = runtime.earn.data
    out["coordinators"] = {
        "portfolio": {
            **_health(runtime.portfolio),
            "holdings": len(data.holdings) if data else 0,
            "wallets": len(data.wallet_ids) if data else 0,
            "unnamed_holdings": len(data.holdings) - len(data.assets) if data else 0,
        },
        "history": {**_health(runtime.history), "timeframes": len(runtime.history.data or {})},
        "earn": {**_health(runtime.earn), "offered_assets": len(earn.offered) if earn else 0},
        "rewards": {
            **_health(runtime.rewards),
            "assets_with_rewards": len(runtime.rewards.data or {}),
        },
    }
    return out


def _price_tracker(entry: ConfigEntry, runtime) -> dict[str, Any]:
    assets = [
        subentry.data[CONF_ASSET]
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_ASSET
    ]
    out: dict[str, Any] = {
        "service": "price_tracker",
        "assets": sorted(f"{a.get('symbol')} ({a.get('id')})" for a in assets),
        "currencies": ["EUR", *entry.options.get(CONF_EXTRA_CURRENCIES, [])],
    }
    if runtime is None:
        return out
    tickers = runtime.tickers
    out["tickers"] = {
        **_health(tickers),
        "priced_assets": len(tickers.data or {}),
        "update_interval_seconds": (
            tickers.update_interval.total_seconds() if tickers.update_interval else None
        ),
    }
    ecb = runtime.ecb
    out["ecb"] = (
        None
        if ecb is None
        else {**_health(ecb), "rate_date": ecb.data.date if ecb.data else None}
    )
    return out


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """An entry that is not loaded -- setup failed, or reauth is pending,
    which is exactly when diagnostics are wanted -- has no runtime data and
    reports its configuration only."""
    runtime = entry.runtime_data if entry.state is ConfigEntryState.LOADED else None
    if entry_type(entry) == ENTRY_TYPE_PRICE_TRACKER:
        return _price_tracker(entry, runtime)
    return _portfolio(entry, runtime)
