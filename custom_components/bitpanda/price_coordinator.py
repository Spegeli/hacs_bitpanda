"""Coordinators of the Price Tracker service. Nothing here uses an API key."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BitpandaApiClient, BitpandaApiError, BitpandaRateLimitError
from .const import (
    DOMAIN,
    ECB_UPDATE_INTERVAL,
    PRICE_UPDATE_INTERVAL_BASE,
    TICKER_HOURLY_BUDGET,
)
from .ecb import EcbError, EcbRates, async_fetch_ecb_rates
from .portfolio_model import DECIMALS

_LOGGER = logging.getLogger(__name__)

# Past this the prices are stale enough to tell the user about. A warning
# threshold, never a cap -- see price_interval.
_SLOW_INTERVAL = timedelta(minutes=30)

# Each 429 in a row doubles the interval, up to this factor; the first
# success returns to the budgeted interval.
_MAX_BACKOFF = 16

# Retry for ECB rates that were never loaded: until then the other
# currencies have no value at all.
_ECB_RETRY = timedelta(minutes=15)


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


def convert_price(price, rate: float | None) -> float | None:
    """An EUR ticker price, times an ECB rate when given, rounded to 8 decimals.

    /tickers always answers in EUR. `rate` is units of the target currency
    per EUR.
    """
    try:
        value = float(price)
    except (TypeError, ValueError):
        return None
    return round(value if rate is None else value * rate, DECIMALS)


class TickerCoordinator(DataUpdateCoordinator[dict[str, float]]):
    """EUR prices of the tracked assets, one keyless /tickers request each.

    A failing or delisted asset is left out of the data, so only its own
    sensors go unavailable, and is warned about once until it recovers. The
    update fails as a whole only when every request fails, or on a 429,
    which also stops the round and backs off.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
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
                raise UpdateFailed("Rate limited by Bitpanda") from None
            except BitpandaApiError:
                failed.add(asset_id)
                continue
            price = convert_price(ticker.get("price"), None)
            if price is None:
                failed.add(asset_id)
                continue
            prices[asset_id] = price

        if self._tracked and not prices:
            raise UpdateFailed("No prices could be fetched")

        if self._backoff != 1:
            self._backoff = 1
            self.update_interval = self._base_interval

        for asset_id in failed - self._failing:
            _LOGGER.warning(
                "No price for %s; its price sensors are unavailable until it "
                "returns",
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

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
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
            raise UpdateFailed(str(err)) from None
        self.update_interval = ECB_UPDATE_INTERVAL
        return rates


@dataclass
class PriceTrackerRuntime:
    """What a loaded Price Tracker entry keeps in `entry.runtime_data`."""

    tickers: TickerCoordinator
    ecb: EcbCoordinator | None
