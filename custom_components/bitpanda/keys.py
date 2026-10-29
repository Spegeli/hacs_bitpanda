"""The integration's one API key: the Portfolio's.

Since 2026-10-28 Bitpanda gives prices (/tickers) only to an API key with
Trade (Read) -- asset names (/assets) too on 2026-10-28, and since
2026-10-29 at times. Both services use the key the Bitpanda Portfolio holds
-- whoever has no Bitpanda account cannot create a key, and the Portfolio is
the service that needs one anyway. The Price Tracker borrows it at each
round, so a new key reaches it without a reload, and every refusal asks the
Portfolio's entry for a new key: the one dialog, "New Bitpanda API key
needed", serves both services.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, ENTRY_TYPE_PORTFOLIO

# The states whose entry cannot take a new key: storing one reloads the
# entry, which Home Assistant refuses in them.
_NO_RELOAD = frozenset({ConfigEntryState.MIGRATION_ERROR, ConfigEntryState.FAILED_UNLOAD})


def portfolio_entry(hass: HomeAssistant) -> ConfigEntry | None:
    """The entry whose key both services use, in any state, a disabled one
    included: the Portfolio -- the entry with the Portfolio's unique ID --,
    else a date version's entry waiting for its upgrade (version 1, which
    becomes the Portfolio), else None. An ignored discovery holds no key."""
    waiting: ConfigEntry | None = None
    for entry in hass.config_entries.async_entries(DOMAIN, include_ignore=False):
        if entry.unique_id == ENTRY_TYPE_PORTFOLIO:
            return entry
        if entry.version == 1 and waiting is None:
            waiting = entry
    return waiting


def portfolio_api_key(hass: HomeAssistant) -> str | None:
    """The Portfolio's API key, None without a Portfolio."""
    entry = portfolio_entry(hass)
    if entry is None:
        return None
    key: str | None = entry.data.get(CONF_API_KEY)
    return key


@callback
def async_request_portfolio_reauth(hass: HomeAssistant, refused_key: str) -> None:
    """Ask for a new key on the Portfolio's entry: Bitpanda refused
    `refused_key`.

    Nothing is asked without a Portfolio, while its entry cannot take a new
    key, or once its stored key is another: a request still under way with
    the old key may come back refused after the user entered a new one, and
    Home Assistant aborts an open reauth only as the reload begins. Home
    Assistant opens no second dialog while one is open.
    """
    entry = portfolio_entry(hass)
    if entry is None or entry.state in _NO_RELOAD:
        return
    if entry.data.get(CONF_API_KEY) != refused_key:
        return
    entry.async_start_reauth(hass)
