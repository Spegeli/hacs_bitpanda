"""Coordinators of the Price Tracker service. Nothing here uses an API key."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
import math
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BitpandaApiClient, BitpandaApiError, BitpandaRateLimitError
from .const import (
    DOMAIN,
    ECB_UPDATE_INTERVAL,
    ERROR_CONNECTION,
    ERROR_HTTP_STATUS,
    ERROR_TIMEOUT,
    ERROR_UNREADABLE,
    PRICE_UPDATE_INTERVAL_BASE,
    TICKER_HOURLY_BUDGET,
)
from .ecb import EcbError, EcbRates, async_fetch_ecb_rates
from .portfolio_model import DECIMALS

_LOGGER = logging.getLogger(__name__)

# Past this the prices are stale enough to tell the user about. A warning
# threshold, never a cap -- see price_interval.
_SLOW_INTERVAL = timedelta(minutes=30)

# The repair issue while the interval is past _SLOW_INTERVAL; its id is also
# its translation key (`issues` in strings.json).
ISSUE_SLOW_PRICE_INTERVAL = "slow_price_interval"

# Each 429 in a row doubles the interval, up to this factor; the first
# success returns to the budgeted interval.
_MAX_BACKOFF = 16

# Retry for ECB rates that were never loaded: until then the other
# currencies have no value at all.
_ECB_RETRY = timedelta(minutes=15)

# The text of each kind of failed ECB fetch (const.API_ERROR_KINDS). The ECB
# answers no listing and has no rate limit of its own -- a 429 from it is an
# HTTP status -- so never ERROR_INCOMPLETE_LISTING or ERROR_RATE_LIMITED.
# Looked up by EcbError.kind, which may be None.
_ECB_FAILED_KEYS: dict[str | None, str] = {
    ERROR_TIMEOUT: "ecb_rates_failed_timeout",
    ERROR_CONNECTION: "ecb_rates_failed_connection",
    ERROR_HTTP_STATUS: "ecb_rates_failed_http_status",
    ERROR_UNREADABLE: "ecb_rates_failed_unreadable",
}


def _ecb_failed(err: EcbError) -> UpdateFailed:
    """A failed ECB fetch, translated by what failed: an HTTP status is its
    only placeholder, so the whole message is in the reader's language; the
    English message is for the log alone. A failure that does not say
    enough to fill its text in gets the plain `ecb_rates_failed`."""
    key = _ECB_FAILED_KEYS.get(err.kind)
    placeholders: dict[str, int | None] = {}
    if err.kind == ERROR_HTTP_STATUS:
        placeholders["status"] = err.status
    if key is None or None in placeholders.values():
        return UpdateFailed(translation_domain=DOMAIN, translation_key="ecb_rates_failed")
    return UpdateFailed(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders={name: str(value) for name, value in placeholders.items()}
        or None,
    )


def price_interval(ticker_count: int) -> timedelta:
    """Poll interval that keeps ticker requests within TICKER_HOURLY_BUDGET.

    There is no batch ticker: each tracked asset costs one request per poll.
    60 s up to 30 assets, then stretched linearly. Deliberately uncapped: a
    cap would silently break the budget for large tracker counts, and a slow
    sensor is a visible annoyance where a rate-limited one fails in ways
    nobody can diagnose.
    """
    if ticker_count <= 0:
        return PRICE_UPDATE_INTERVAL_BASE
    seconds = ticker_count * 3600 / TICKER_HOURLY_BUDGET
    return timedelta(seconds=max(PRICE_UPDATE_INTERVAL_BASE.total_seconds(), seconds))


@callback
def async_report_price_interval(hass: HomeAssistant, ticker_count: int) -> None:
    """Raise the slow-interval repair issue while the interval `ticker_count`
    tracked assets need is past _SLOW_INTERVAL; delete it once it is not.

    Called at every setup of the Price Tracker, which follows every change
    to what it tracks. A warning: the prices still come, only slowly. It
    names the number of assets and the interval in whole minutes, rounded
    up so that it never reads as the 30 it is past. Not kept across
    restarts -- every start raises it again while it lasts -- and not
    deleted when the Price Tracker is merely unloaded: deleting would also
    forget that the user chose to ignore it.
    """
    interval = price_interval(ticker_count)
    if interval <= _SLOW_INTERVAL:
        async_delete_price_interval_issue(hass)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_SLOW_PRICE_INTERVAL,
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_SLOW_PRICE_INTERVAL,
        translation_placeholders={
            "count": str(ticker_count),
            "minutes": str(math.ceil(interval.total_seconds() / 60)),
        },
    )


@callback
def async_delete_price_interval_issue(hass: HomeAssistant) -> None:
    """Delete the slow-interval repair issue -- for when the Price Tracker
    goes, or tracks few enough assets."""
    ir.async_delete_issue(hass, DOMAIN, ISSUE_SLOW_PRICE_INTERVAL)


def convert_price(price: Any, rate: float | None) -> float | None:
    """An EUR ticker price, times an ECB rate when given, rounded to 8 decimals.

    /tickers always answers in EUR. `rate` is units of the target currency
    per EUR. Anything that is not a finite number is no price: "inf" and
    "nan" parse as floats, but Home Assistant refuses them as a sensor value.
    """
    try:
        value = float(price)
    except (TypeError, ValueError):
        return None
    if rate is not None:
        value *= rate
    if not math.isfinite(value):
        return None
    return round(value, DECIMALS)


class TickerCoordinator(DataUpdateCoordinator[dict[str, float]]):
    """EUR prices of the tracked assets, one keyless /tickers request each.

    A failing or delisted asset is left out of the data, so only its own
    sensors go unavailable. It is warned about once, and its return is
    logged once at INFO. The update fails as a whole only when every request
    fails, or on a 429, which also stops the round and backs off -- warned
    about once when the backoff starts, logged once at INFO when a round
    succeeds again and ends it. The whole update's own failure and recovery
    DataUpdateCoordinator logs itself.
    """

    config_entry: PriceTrackerConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PriceTrackerConfigEntry,
        client: BitpandaApiClient,
        tracked: dict[str, str],
    ) -> None:
        self._base_interval = price_interval(len(tracked))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_tickers",
            update_interval=self._base_interval,
            config_entry=entry,
        )
        self._client = client
        self._tracked = dict(tracked)
        self._failing: set[str] = set()
        self._backoff = 1
        if self._base_interval > _SLOW_INTERVAL:
            _LOGGER.warning(
                "%s price trackers need one request each; prices refresh every "
                "%s to stay within the request budget. Track fewer assets for "
                "faster updates.",
                len(tracked),
                self._base_interval,
            )

    async def _async_update_data(self) -> dict[str, float]:
        prices: dict[str, float] = {}
        failed: set[str] = set()
        for asset_id in self._tracked:
            try:
                ticker = await self._client.async_get_ticker(asset_id)
            except BitpandaRateLimitError:
                if self._backoff == 1:
                    _LOGGER.warning(
                        "Bitpanda rate-limited the price requests; slowing down "
                        "until they succeed again"
                    )
                self._backoff = min(self._backoff * 2, _MAX_BACKOFF)
                self.update_interval = self._base_interval * self._backoff
                raise UpdateFailed(
                    translation_domain=DOMAIN, translation_key="prices_rate_limited"
                ) from None
            except BitpandaApiError:
                failed.add(asset_id)
                continue
            price = convert_price(ticker.get("price"), None)
            if price is None:
                failed.add(asset_id)
                continue
            prices[asset_id] = price

        if self._tracked and not prices:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="no_prices")

        if self._backoff != 1:
            self._backoff = 1
            self.update_interval = self._base_interval
            _LOGGER.info(
                "Bitpanda answers the price requests again; back to polling every %s",
                self._base_interval,
            )

        for asset_id in failed - self._failing:
            _LOGGER.warning(
                "No price for %s; its price sensors are unavailable until it "
                "returns",
                self._tracked[asset_id],
            )
        # Every tracked asset was asked for in this round: one that failed
        # before and not now has its price back.
        for asset_id in self._failing - failed:
            _LOGGER.info(
                "Price for %s is back; its price sensors are available again",
                self._tracked[asset_id],
            )
        self._failing = failed
        return prices


class EcbCoordinator(DataUpdateCoordinator[EcbRates]):
    """ECB reference rates. Created only when extra currencies are configured.

    A failed fetch leaves `data` at the last rates -- DataUpdateCoordinator
    keeps them -- and the price sensors keep converting with those, showing
    their `rate_date`. While no rates were ever loaded, the other currencies
    show nothing, so a failure then is retried after _ECB_RETRY instead of
    the 6 hours the rates themselves need.
    """

    config_entry: PriceTrackerConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PriceTrackerConfigEntry,
        session: aiohttp.ClientSession,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_ecb",
            update_interval=ECB_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._session = session

    async def _async_update_data(self) -> EcbRates:
        try:
            rates = await async_fetch_ecb_rates(self._session)
        except EcbError as err:
            if self.data is None:
                self.update_interval = _ECB_RETRY
            raise _ecb_failed(err) from None
        self.update_interval = ECB_UPDATE_INTERVAL
        return rates


@dataclass
class PriceTrackerRuntime:
    """What a loaded Price Tracker entry keeps in `entry.runtime_data`."""

    tickers: TickerCoordinator
    ecb: EcbCoordinator | None


# A Price Tracker config entry, its runtime data typed.
type PriceTrackerConfigEntry = ConfigEntry[PriceTrackerRuntime]
