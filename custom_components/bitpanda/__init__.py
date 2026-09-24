"""The Bitpanda integration."""
from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from .assets import AssetResolver
from .const import (
    CONF_API_KEY,
    CONF_ASSET_CACHE,
    CONF_CURRENCY,
    CONF_CURRENCY_ID,
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DOMAIN,
    EUR_CURRENCY_ID,
)
from .coordinator import (
    EarnCoordinator,
    HistoryCoordinator,
    PortfolioCoordinator,
    PriceCoordinator,
    RewardsCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# v1 wallet ids were "{category}_{symbol}", where the category itself could
# contain an underscore, e.g. "commodity_metal_XAU" or "index_wallet_BCI5".
# Order matters: this is checked longest/most-specific first, or a shorter
# prefix that is itself a prefix of a longer one ("index_" / "index_wallet_")
# would strip first and leave a mangled symbol ("wallet_BCI5").
_LEGACY_PREFIXES = (
    "commodity_metal_",
    "index_wallet_",
    "cryptocoin_",
    "fiat_",
    "index_",
    "metal_",
)


def legacy_symbol(wallet_id: str) -> str:
    """Extract the asset symbol from a version 1 wallet id.

    A wallet id with no recognised prefix (already a bare symbol, or an
    unrecognised category) is returned unchanged. Resolution then either
    succeeds outright (a bare symbol) or legitimately fails and gets dropped
    with a warning (an unrecognised category) -- both are safer than
    guessing at a split.
    """
    for prefix in _LEGACY_PREFIXES:
        if wallet_id.startswith(prefix):
            return wallet_id[len(prefix):]
    return wallet_id


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry from version 1 to version 2.

    Version 1 stored asset symbols and "{category}_{symbol}" wallet ids. The
    public API works on UUIDs, so every stored identifier is resolved once
    and replaced.

    This runs once against a real installation's only copy of its
    configuration, so it must never leave an entry partially rewritten.
    Resolution failing for one symbol (delisted, renamed) is expected and
    that entry is dropped with a warning. An auth or rate-limit error means
    something else: it says nothing about whether any particular symbol
    still exists, and would fail every remaining lookup the same way, so
    treating it like "symbol not found" would silently empty out the whole
    list. The whole attempt is aborted instead, with the entry untouched --
    Home Assistant re-checks the version and retries migration on every
    subsequent startup, so nothing is lost by waiting.
    """
    if entry.version >= 2:
        return True

    _LOGGER.info("Migrating Bitpanda config entry to version 2")

    client = BitpandaApiClient(
        entry.data[CONF_API_KEY], async_get_clientsession(hass)
    )
    resolver = AssetResolver(client, {})

    async def _resolve_all(values: list[str], strip_prefix: bool) -> list[str]:
        out: list[str] = []
        for value in values:
            sym = legacy_symbol(value) if strip_prefix else value
            asset = await resolver.async_resolve(sym)
            if asset is None:
                _LOGGER.warning(
                    "Dropping %s during migration: symbol %s no longer resolves",
                    value,
                    sym,
                )
                continue
            out.append(asset["id"])
        return out

    options = dict(entry.options)
    try:
        currencies = await client.async_get_currencies()
        symbol = entry.data.get(CONF_CURRENCY, "EUR")
        currency_id = next(
            (c["id"] for c in currencies if c["symbol"] == symbol), EUR_CURRENCY_ID
        )
        new_tracked_assets = await _resolve_all(
            options.get(CONF_TRACKED_ASSETS, []), strip_prefix=False
        )
        new_tracked_wallets = await _resolve_all(
            options.get(CONF_TRACKED_WALLETS, []), strip_prefix=True
        )
    except BitpandaAuthError:
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: the API key was "
            "rejected. Nothing has been changed; migration will be retried "
            "on the next restart once a valid key is in place."
        )
        return False
    except BitpandaRateLimitError:
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: rate limited by the "
            "Bitpanda API. Nothing has been changed; migration will be "
            "retried on the next restart."
        )
        return False
    except BitpandaApiError:
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: could not reach the "
            "Bitpanda API. Nothing has been changed; migration will be "
            "retried on the next restart."
        )
        return False

    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_CURRENCY_ID: currency_id},
        options={
            CONF_TRACKED_ASSETS: new_tracked_assets,
            CONF_TRACKED_WALLETS: new_tracked_wallets,
            CONF_ASSET_CACHE: resolver.as_dict(),
        },
        version=2,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bitpanda from a config entry."""
    client = BitpandaApiClient(
        entry.data[CONF_API_KEY], async_get_clientsession(hass)
    )
    currency_id = entry.data.get(CONF_CURRENCY_ID, EUR_CURRENCY_ID)
    currency = entry.data.get(CONF_CURRENCY, "EUR")
    resolver = AssetResolver(client, entry.options.get(CONF_ASSET_CACHE, {}))

    portfolio = PortfolioCoordinator(hass, entry, client, currency_id)
    prices = PriceCoordinator(hass, entry, client, portfolio)
    earn = EarnCoordinator(hass, entry, client)
    rewards = RewardsCoordinator(hass, entry, client)
    history = HistoryCoordinator(hass, entry, client, currency_id)

    prices.set_tracked(entry.options.get(CONF_TRACKED_ASSETS, []))

    await portfolio.async_config_entry_first_refresh()
    await prices.async_config_entry_first_refresh()
    # Earn, rewards and history are additive. A failure there must not block
    # setup, so they refresh without raising ConfigEntryNotReady -- unlike
    # async_config_entry_first_refresh(), plain async_refresh() never raises
    # it, even on total failure; it only marks last_update_success False. A
    # rewards key without the required scope is not even a failure here:
    # RewardsCoordinator catches that itself, latches `unauthorized` and
    # returns an empty result, so last_update_success stays True and every
    # other sensor keeps working.
    await earn.async_refresh()
    await rewards.async_refresh()
    await history.async_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "portfolio_coordinator": portfolio,
        "price_coordinator": prices,
        "earn_coordinator": earn,
        "rewards_coordinator": rewards,
        "history_coordinator": history,
        "resolver": resolver,
        "currency": currency,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    if not hass.services.has_service(DOMAIN, "refresh"):
        _last_refresh: dict[str, float] = {"time": 0.0}
        _COOLDOWN = 10.0

        async def handle_refresh(call: ServiceCall) -> None:
            now = time.monotonic()
            if now - _last_refresh["time"] < _COOLDOWN:
                _LOGGER.debug("Refresh cooldown active, ignoring call")
                return
            _last_refresh["time"] = now
            for store in hass.data[DOMAIN].values():
                await store["portfolio_coordinator"].async_request_refresh()
                await store["price_coordinator"].async_request_refresh()

        hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "refresh")
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
