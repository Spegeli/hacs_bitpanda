"""Coordinators of the Price Tracker service. Nothing here uses an API key."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
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
from .streaks import FailureStreak
from .tolerance import TolerantCoordinator

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

# The kinds of failed request (const.API_ERROR_KINDS) that got no answer at
# all: a timeout, or no connection.
_UNANSWERED = frozenset({ERROR_TIMEOUT, ERROR_CONNECTION})

# Unanswered requests in a row, before any fresh price arrived, that stop a
# round as a whole (TickerCoordinator).
_UNANSWERED_IN_A_ROW = 2

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


class TickerCoordinator(TolerantCoordinator[dict[str, float]]):
    """EUR prices of the tracked assets, one keyless /tickers request each.

    The update fails as a whole when no request brings a fresh price, or on
    a 429, which also stops the round and backs off -- warned about once
    when the backoff starts, logged once at INFO when a round succeeds again
    and ends it. The price sensors keep the last prices until the failure is
    confirmed (tolerance.py). The whole update's own failure and recovery
    DataUpdateCoordinator logs itself.

    An asset whose own request fails, or whose price is unusable, while
    others answer follows the same rule on its own: it keeps its last price
    until its own streak is confirmed, then it is left out of the data, so
    only its own sensors go unavailable -- a delisted asset's after three
    rounds, and at once when there is no last price. Every round without a
    fresh price counts for an asset, one that fails as a whole included: so
    a price from before a confirmed outage never comes back after it, and a
    round that fails as a whole leaves out at once a last price whose own
    failure it confirms. An asset is warned about once its failure is
    confirmed, in a round that returns data, and its return is logged once
    at INFO.

    Every request waits for its own timeout, so a hanging connection would
    stretch the tolerance with the number of tracked assets. A round
    therefore stops as a whole -- it fails, as when no request brings a
    fresh price -- once _UNANSWERED_IN_A_ROW requests in a row get no
    answer at all (a timeout, or no connection) before any fresh price
    arrived. An answer of any kind, an HTTP error status or an unreadable
    body too, breaks such a run, and after a fresh price nothing stops the
    round. Nor does such a run stop a first round, before any data: there is
    no last price to keep yet, and setup must not stall on assets that never
    answer.

    Each round asks for the assets without a fresh price last. An asset is
    marked when its own latest request brings none -- it failed, or the
    price was unusable -- and a fresh price removes the mark. The unmarked
    assets come first, in tracked order, then the marked ones, the oldest
    mark first. So a round that stops moves the assets it asked behind every
    other, and the next round asks different ones first: once Bitpanda
    answers the others again, each pair of assets that keep hanging stops
    one round at the most.
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
            regular_interval=self._base_interval,
            config_entry=entry,
        )
        self._client = client
        self._tracked = dict(tracked)
        # Asset -> its rounds in a row without a fresh price.
        self._streaks: dict[str, FailureStreak] = {}
        # Asset -> its mark: its own latest request brought no fresh price --
        # it failed, or the price was unusable. A mark is a number from
        # _mark_count, which counts up at each mark -- never the clock: a
        # round asks for the marked assets last, the oldest mark first. A
        # fresh price removes the mark; a round that stops before asking an
        # asset leaves its mark as it was.
        self._marks: dict[str, int] = {}
        self._mark_count = 0
        # The assets warned about: their return is logged.
        self._announced: set[str] = set()
        self._backoff = 1
        if self._base_interval > _SLOW_INTERVAL:
            _LOGGER.warning(
                "%s price trackers need one request each; prices refresh every "
                "%s to stay within the request budget. Track fewer assets for "
                "faster updates.",
                len(tracked),
                self._base_interval,
            )

    @property
    def failing_assets(self) -> frozenset[str]:
        """The assets without a fresh price in the latest round -- carried
        over, confirmed or without a last price alike. The real outcome,
        which diagnostics report: `data` holds the prices the sensors show,
        carried ones included."""
        return frozenset(self._streaks)

    async def _async_fetch(self, requested_at: datetime) -> dict[str, float]:
        prices: dict[str, float] = {}
        # Requests in a row that got no answer at all.
        unanswered = 0
        # A first round, before any data, never stops for requests without an
        # answer: there is no last price whose tolerance they could stretch,
        # and setup must not stall on assets that never answer.
        first_round = self.data is None
        # The assets without a mark first, in tracked order (a stable sort),
        # then the marked ones, the oldest mark first. Not by streak: a round
        # that stops counts for every asset, the ones it never asked
        # included, so a streak cannot tell which ones hang.
        order = sorted(self._tracked, key=lambda asset: self._marks.get(asset, 0))
        for asset_id in order:
            # Marked, behind every asset marked before, unless a fresh price
            # comes.
            self._mark_count += 1
            self._marks[asset_id] = self._mark_count
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
                self._count_for_every_asset(requested_at)
                raise UpdateFailed(
                    translation_domain=DOMAIN, translation_key="prices_rate_limited"
                ) from None
            except BitpandaApiError as err:
                unanswered = unanswered + 1 if err.kind in _UNANSWERED else 0
                if not first_round and not prices and unanswered >= _UNANSWERED_IN_A_ROW:
                    # Bitpanda is out of reach, and every further request
                    # would wait for its own timeout: the round fails as a
                    # whole, below.
                    break
                continue
            unanswered = 0
            price = convert_price(ticker.get("price"), None)
            if price is not None:
                prices[asset_id] = price
                # A round that overlapped this one may have removed the mark
                # while this request was under way: Home Assistant 2025.5
                # lets a refresh by hand run during a scheduled one.
                self._marks.pop(asset_id, None)

        # Fresh prices only: last prices carried over never keep a round from
        # failing as a whole.
        if self._tracked and not prices:
            self._count_for_every_asset(requested_at)
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="no_prices")

        if self._backoff != 1:
            self._backoff = 1
            self.update_interval = self._base_interval
            _LOGGER.info(
                "Bitpanda answers the price requests again; back to polling every %s",
                self._base_interval,
            )
        return self._tolerate_failed_assets(prices, requested_at)

    def _count_for_every_asset(self, requested_at: datetime) -> None:
        """Add a round that fails as a whole to every asset's streak,
        creating the missing ones: it brought no fresh price for any of
        them. A last price whose own failure this confirms is shown no
        longer -- the data loses it, and tolerance.py tells the listeners.
        It warns about no asset -- the whole update's outage is warned about
        once confirmed (tolerance.py) -- so the next round that returns data
        warns about each asset still failing whose streak is confirmed.
        """
        shown = self._tolerate_failed_assets({}, requested_at, announce=False)
        if self.data is not None and shown != self.data:
            self.data = shown

    def _tolerate_failed_assets(
        self, prices: dict[str, float], requested_at: datetime, *, announce: bool = True
    ) -> dict[str, float]:
        """The round's data: the fresh `prices`, and the last price of each
        asset whose failure is not confirmed yet.

        A tracked asset missing from `prices` had no fresh price in this
        round -- its request failed, its price was unusable, or the round
        failed as a whole -- and adds a failure, asked for at `requested_at`,
        to its streak. Until FailureStreak's rule confirms the streak at the
        regular pace, the asset keeps the price `data` still holds for it,
        if any. Once confirmed, it is left out and warned about once. A
        fresh price ends the streak, and the return of an asset warned about
        is logged once. With `announce` False -- a round that fails as a
        whole -- nothing is logged per asset, and none is marked as warned
        about.
        """
        data: dict[str, float] = {}
        last = self.data or {}
        for asset_id, label in self._tracked.items():
            if asset_id in prices:
                data[asset_id] = prices[asset_id]
                self._streaks.pop(asset_id, None)
                if asset_id in self._announced:
                    self._announced.remove(asset_id)
                    _LOGGER.info(
                        "Price for %s is back; its price sensors are available again",
                        label,
                    )
                continue
            streak = self._streaks.setdefault(asset_id, FailureStreak())
            streak.add(requested_at)
            if not streak.confirmed(self._regular_interval):
                if asset_id in last:
                    data[asset_id] = last[asset_id]
                if announce:
                    _LOGGER.debug(
                        "No price for %s: failure %s in a row, not confirmed yet",
                        label,
                        streak.count,
                    )
            elif announce and asset_id not in self._announced:
                self._announced.add(asset_id)
                _LOGGER.warning(
                    "No price for %s; its price sensors are unavailable until it "
                    "returns",
                    label,
                )
        return data


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
