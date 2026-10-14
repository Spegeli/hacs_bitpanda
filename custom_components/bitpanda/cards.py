"""The dashboard cards: one built module, served by the integration and added
to every dashboard.

HACS installs only this folder, so the bundle built from cards/ ships in
frontend/ (CONTRIBUTING.md, "Dashboard cards"). Its URL carries a hash of
the file's content: a browser that still holds an older bundle loads the new
one after an update instead of failing on "Custom element doesn't exist". A
module added while a dashboard is open appears there after a browser reload;
Home Assistant writes the list into the page when it loads.

The Portfolio card's line is Bitpanda's own value history, which the
Portfolio's returns arrive with: bitpanda/portfolio_history hands it to them
from memory.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import websocket_command

from homeassistant.components.frontend import add_extra_js_url
# Defined in components.http at 2025.5; newer releases define it in
# helpers.http and import it here without re-exporting it. Only this path
# works on every release from the minimum on; mypy checks the newest.
from homeassistant.components.http import StaticPathConfig  # type: ignore[attr-defined]
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, ENTRY_TYPE_PORTFOLIO, PORTFOLIO_TIMEFRAMES, entry_type
from .portfolio_coordinator import PortfolioRuntime

_LOGGER = logging.getLogger(__name__)

CARDS_FILE = Path(__file__).parent / "frontend" / "bitpanda-cards.js"
CARDS_URL = "/bitpanda_static/bitpanda-cards.js"


def cards_digest(path: Path) -> str:
    """The first 12 hex digits of the SHA-256 of the file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


# The cards' timeframes and /portfolio-history's.
_TIMEFRAMES = {timeframe.lower(): timeframe for timeframe in PORTFOLIO_TIMEFRAMES}


# Newer releases type schemas with probatio; voluptuous works the same at
# runtime on every release from the minimum on, and mypy checks the newest.
@websocket_command(
    {vol.Required("type"): "bitpanda/portfolio_history", vol.Required("timeframe"): vol.In(_TIMEFRAMES)}  # type: ignore[dict-item]
)
@callback
def ws_portfolio_history(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """The Portfolio's value over a timeframe, as [milliseconds, value]
    pairs; none without a loaded Portfolio or a series for the timeframe,
    nor while its sensors are unavailable (a rejected key, a confirmed
    outage), so that the line goes with the figures around it.
    Not admin-only: every dashboard user sees the cards."""
    points: tuple[tuple[int, float], ...] = ()
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED and entry_type(entry) == ENTRY_TYPE_PORTFOLIO:
            runtime = entry.runtime_data
            history = runtime.history if isinstance(runtime, PortfolioRuntime) else None
            if history is not None and history.data_available and history.data is not None:
                points = history.data.series.get(_TIMEFRAMES[msg["timeframe"]], ())
    connection.send_result(msg["id"], {"points": [[time, value] for time, value in points]})


async def async_register_cards(hass: HomeAssistant) -> None:
    """Serve the bundle and add it to every dashboard, and answer the
    cards' requests for the Portfolio line. Called once per run, from
    async_setup, however many entries are set up or reloaded. A failure
    serving the bundle costs the cards only: the sensors set up all the
    same. So does a Home Assistant without its frontend or its websocket
    API, both after-dependencies: set up before the integration when they
    are configured at all."""
    if "websocket_api" in hass.config.components:
        websocket_api.async_register_command(hass, ws_portfolio_history)
    if "frontend" not in hass.config.components:
        _LOGGER.warning(
            "The dashboard cards are not available: Home Assistant's frontend is not loaded"
        )
        return
    try:
        digest = await hass.async_add_executor_job(cards_digest, CARDS_FILE)
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARDS_URL, str(CARDS_FILE), True)]
        )
    except Exception as err:  # noqa: BLE001 - the cards are extra; the sensors are not
        _LOGGER.warning("The dashboard cards are not available: %s", err)
        return
    add_extra_js_url(hass, f"{CARDS_URL}?v={digest}")
