"""The Bitpanda integration."""
from __future__ import annotations

import logging
from time import monotonic

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import migration
from .api import BitpandaApiClient
from .assets import AssetDirectory
from .const import (
    CONF_API_KEY,
    CONF_ASSET,
    CONF_CURRENCY_ID,
    CONF_EXTRA_CURRENCIES,
    CONF_LEGACY_ADOPT,
    DOMAIN,
    ENTRY_TYPE_PRICE_TRACKER,
    REFRESH_MIN_COOLDOWN,
    SUBENTRY_TYPE_ASSET,
    entry_type,
)
from .naming import asset_display_label
from .portfolio_coordinator import (
    EarnCoordinator,
    HistoryCoordinator,
    PortfolioCoordinator,
    PortfolioRuntime,
    RewardsCoordinator,
)
from .price_coordinator import EcbCoordinator, PriceTrackerRuntime, TickerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Records of held assets, shared across reloads of the Portfolio entry.
_ASSET_DIRECTORY_KEY = f"{DOMAIN}_asset_directory"


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an entry to version 3 (see migration.py)."""
    return await migration.async_migrate_entry(hass, entry)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one of the two services."""
    if entry_type(entry) == ENTRY_TYPE_PRICE_TRACKER:
        entry.runtime_data = await _async_start_price_tracker(hass, entry)
    else:
        entry.runtime_data = await _async_start_portfolio(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Options, subentries and data all change what exists: rebuild on any change.
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    _async_register_refresh_service(hass)
    return True


async def _async_start_portfolio(hass: HomeAssistant, entry: ConfigEntry) -> PortfolioRuntime:
    session = async_get_clientsession(hass)
    client = BitpandaApiClient(entry.data[CONF_API_KEY], session)
    # Asset lookups are public: keyless, and the records outlive reloads.
    directory = AssetDirectory(
        BitpandaApiClient(None, session), hass.data.setdefault(_ASSET_DIRECTORY_KEY, {})
    )
    currency_id = entry.data[CONF_CURRENCY_ID]
    runtime = PortfolioRuntime(
        portfolio=PortfolioCoordinator(hass, entry, client, currency_id, directory),
        history=HistoryCoordinator(hass, entry, client, currency_id),
        earn=EarnCoordinator(hass, entry, client),
        rewards=RewardsCoordinator(hass, entry, client),
    )
    await runtime.portfolio.async_config_entry_first_refresh()
    # Earn, rewards and history are additive: a failure there must not block
    # setup, so they refresh with async_refresh(), which never raises
    # ConfigEntryNotReady. A 401 from any of them still reaches the reauth
    # dialog: DataUpdateCoordinator catches the ConfigEntryAuthFailed each
    # raises and starts reauth itself.
    await runtime.earn.async_refresh()
    await runtime.rewards.async_refresh()
    await runtime.history.async_refresh()
    return runtime


async def _async_start_price_tracker(
    hass: HomeAssistant, entry: ConfigEntry
) -> PriceTrackerRuntime:
    if entry.data.get(CONF_LEGACY_ADOPT):
        # Before any entity exists -- see migration.async_adopt_legacy_prices.
        migration.async_adopt_legacy_prices(hass, entry)
    session = async_get_clientsession(hass)
    tracked = {
        subentry.data[CONF_ASSET]["id"]: asset_display_label(subentry.data[CONF_ASSET])
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_ASSET
    }
    tickers = TickerCoordinator(hass, entry, BitpandaApiClient(None, session), tracked)
    ecb = (
        EcbCoordinator(hass, entry, session)
        if entry.options.get(CONF_EXTRA_CURRENCIES)
        else None
    )
    await tickers.async_config_entry_first_refresh()
    if ecb is not None:
        # Not a first refresh: without rates the EUR sensors still work and
        # the other currencies say why they have no value.
        await ecb.async_refresh()
    return PriceTrackerRuntime(tickers=tickers, ecb=ecb)


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _loaded_runtimes(hass: HomeAssistant) -> list:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _refresh_cooldown(runtimes: list) -> float:
    """Seconds between two accepted `bitpanda.refresh` calls: the ticker
    interval, never below REFRESH_MIN_COOLDOWN. A shorter cooldown would let
    an automation drive ticker requests above the budgeted polling rate."""
    seconds = REFRESH_MIN_COOLDOWN.total_seconds()
    for runtime in runtimes:
        if isinstance(runtime, PriceTrackerRuntime):
            interval = runtime.tickers.update_interval
            if interval is not None:
                seconds = max(seconds, interval.total_seconds())
    return seconds


@callback
def _async_register_refresh_service(hass: HomeAssistant) -> None:
    """Register `bitpanda.refresh` once, shared by both services."""
    if hass.services.has_service(DOMAIN, "refresh"):
        return

    # Empty until the first accepted call: the monotonic clock can start near
    # zero after a boot.
    last_accepted: dict[str, float] = {}

    async def handle_refresh(call: ServiceCall) -> None:
        runtimes = _loaded_runtimes(hass)
        now = monotonic()
        previous = last_accepted.get("time")
        if previous is not None and now - previous < _refresh_cooldown(runtimes):
            _LOGGER.debug("Refresh cooldown active, ignoring call")
            return
        last_accepted["time"] = now
        for runtime in runtimes:
            if isinstance(runtime, PortfolioRuntime):
                await runtime.portfolio.async_request_refresh()
            else:
                await runtime.tickers.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an entry; the refresh service goes with the last one."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and not any(
        other.entry_id != entry.entry_id and other.state is ConfigEntryState.LOADED
        for other in hass.config_entries.async_entries(DOMAIN)
    ):
        hass.services.async_remove(DOMAIN, "refresh")
    return unload_ok
