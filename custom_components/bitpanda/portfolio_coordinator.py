"""Coordinators of the Portfolio service.

Every request here carries the API key, except the asset lookups, which the
AssetDirectory makes keyless. Every 401 raises ConfigEntryAuthFailed, which
Home Assistant turns into the reauth dialog.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import BitpandaApiClient, BitpandaApiError, BitpandaAuthError
from .assets import AssetDirectory
from .const import (
    DOMAIN,
    EARN_UPDATE_INTERVAL,
    ERROR_CONNECTION,
    ERROR_HTTP_STATUS,
    ERROR_INCOMPLETE_LISTING,
    ERROR_RATE_LIMITED,
    ERROR_TIMEOUT,
    ERROR_UNREADABLE,
    FIRST_LOAD_RETRY_INTERVAL,
    PORTFOLIO_TIMEFRAMES,
    PORTFOLIO_UPDATE_INTERVAL,
    REWARDS_UPDATE_INTERVAL,
)
from .portfolio_store import KnownWallets, RewardMarks
from .portfolio_model import (
    PORTFOLIO_FIGURES,
    EarnData,
    FigureWatch,
    PortfolioData,
    PortfolioReturns,
    RewardTotals,
    parse_earn_configs,
    parse_portfolio,
    sum_rewards,
    tolerate_failed_timeframes,
)
from .streaks import FailureStreak
from .tolerance import TolerantCoordinator

_LOGGER = logging.getLogger(__name__)


def _auth_failed() -> ConfigEntryAuthFailed:
    """The key was rejected: Home Assistant asks for a new one. Translated,
    so the integration page gives the reason in the user's language; nothing
    of the request reaches the message."""
    return ConfigEntryAuthFailed(translation_domain=DOMAIN, translation_key="api_key_rejected")


# The text of each kind of failed request (const.API_ERROR_KINDS), looked up
# by BitpandaApiError.kind, which is None for an error raised outside the
# client.
_UPDATE_FAILED_KEYS: dict[str | None, str] = {
    ERROR_TIMEOUT: "update_failed_timeout",
    ERROR_CONNECTION: "update_failed_connection",
    ERROR_HTTP_STATUS: "update_failed_http_status",
    ERROR_RATE_LIMITED: "update_failed_rate_limited",
    ERROR_UNREADABLE: "update_failed_unreadable",
    ERROR_INCOMPLETE_LISTING: "update_failed_incomplete_listing",
}


def _update_failed(err: BitpandaApiError) -> UpdateFailed:
    """A failed request, translated by what failed: its placeholders carry
    no words -- the request path, and the HTTP status of a failed status --
    so the whole message is in the reader's language; the client's English
    message is for the log alone. A rate limit (429) has a text of its own,
    with the path alone. A failure that does not say enough to fill its text
    in (no kind, path or status) gets the plain `update_failed`."""
    key = _UPDATE_FAILED_KEYS.get(err.kind)
    placeholders: dict[str, str | int | None] = {"path": err.path}
    if err.kind == ERROR_HTTP_STATUS:
        placeholders["status"] = err.status
    if key is None or None in placeholders.values():
        return UpdateFailed(translation_domain=DOMAIN, translation_key="update_failed")
    return UpdateFailed(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders={name: str(value) for name, value in placeholders.items()},
    )


class PortfolioCoordinator(TolerantCoordinator[PortfolioData]):
    """Polls /portfolio in the Portfolio currency and names the holdings.

    Values arrive converted by Bitpanda (`equivalent_currency_id`): no
    exchange rate is derived or applied here.

    Every successful answer is the truth, an empty one too. Yet what an
    answer no longer lists may be a glitch at Bitpanda rather than a sale,
    so a figure whose entry vanished waits before it shows 0: Total value
    once the answer lists no entry at all, Cash once it lists no fiat entry,
    Cash Plus once it lists no Cash Plus holding (PortfolioData.
    figures_listed). One FigureWatch per figure (PORTFOLIO_FIGURES) counts
    the answers without its entry. While they are too few to confirm it --
    WALLET_REMOVAL_MISSES in a row, the last WALLET_REMOVAL_TIME after the
    first was asked for (portfolio_model.confirmed) -- the figure waits:
    PortfolioData.waiting names it, and its sensor is unavailable. That is
    the pace at which the wallet manager removes a sold asset's wallet;
    refreshes by hand count, but never make it sooner. An answer that lists
    the entry again shows its value and clears the count; one that leaves
    Cash Plus in doubt clears it too, without making Cash Plus there
    (FigureWatch).

    The watches live on this coordinator, so every start -- of Home
    Assistant, or a setup or reload of the entry, a currency change's
    included -- begins them afresh: an entry missing from the first answer
    was never there to vanish, and its figure shows 0 at once. A failed
    request goes through the failure tolerance (tolerance.py) alone: it
    neither counts as an answer without the entry nor clears the count.

    Every answer carries the time it was asked for (PortfolioData.
    requested_at, Home Assistant's clock), by which the watches and the
    wallet manager time their misses.
    """

    config_entry: PortfolioConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PortfolioConfigEntry,
        client: BitpandaApiClient,
        currency_id: str,
        directory: AssetDirectory,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_portfolio",
            update_interval=PORTFOLIO_UPDATE_INTERVAL,
            regular_interval=PORTFOLIO_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._client = client
        self._currency_id = currency_id
        self._directory = directory
        # Figure key -> its wait, which only a successful answer moves on.
        self._watches: dict[str, FigureWatch] = {
            key: FigureWatch() for key in PORTFOLIO_FIGURES
        }
        # The figures that waited after the last successful answer: a change
        # is logged, for whoever wonders why a figure shows unavailable.
        self._waiting: frozenset[str] = frozenset()

    async def _async_fetch(self, requested_at: datetime) -> PortfolioData:
        try:
            entries = await self._client.async_get_portfolio(
                equivalent_currency_id=self._currency_id
            )
        except BitpandaAuthError:
            raise _auth_failed() from None
        except BitpandaApiError as err:
            raise _update_failed(err) from None
        data = parse_portfolio(entries)
        data.requested_at = requested_at
        # Never raises: a failed lookup leaves the holdings not named yet
        # unnamed until the next refresh instead of failing the portfolio.
        await self._directory.async_resolve(data.holdings)
        data.assets = {
            asset_id: record
            for asset_id in data.holdings
            if (record := self._directory.get(asset_id)) is not None
        }
        data.unlisted = {
            asset_id for asset_id in data.holdings if self._directory.is_unlisted(asset_id)
        }
        # After `assets` and `unlisted`: Cash Plus's entry needs the holdings
        # classified.
        listed = data.figures_listed()
        data.waiting = frozenset(
            key for key, watch in self._watches.items() if watch.observe(listed[key], requested_at)
        )
        if data.waiting != self._waiting:
            _LOGGER.debug(
                "Portfolio figures missing from Bitpanda's answer, unavailable until "
                "confirmed: %s",
                ", ".join(sorted(data.waiting)) or "none",
            )
            self._waiting = data.waiting
        return data


class EarnCoordinator(DataUpdateCoordinator[EarnData]):
    """Polls the Earn product catalogue once a day.

    A failed fetch leaves `data` at the last catalogue. While no catalogue
    was ever loaded, no Staking sensor shows its APR, so a failure then is
    retried after FIRST_LOAD_RETRY_INTERVAL instead of a day.
    """

    config_entry: PortfolioConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: PortfolioConfigEntry, client: BitpandaApiClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_earn",
            update_interval=EARN_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._client = client

    async def _async_update_data(self) -> EarnData:
        try:
            configs = await self._client.async_get_earn_configs()
        except BitpandaAuthError:
            raise _auth_failed() from None
        except BitpandaApiError as err:
            if self.data is None:
                self.update_interval = FIRST_LOAD_RETRY_INTERVAL
            raise _update_failed(err) from None
        self.update_interval = EARN_UPDATE_INTERVAL
        return parse_earn_configs(configs)


class RewardsCoordinator(TimestampDataUpdateCoordinator[dict[str, RewardTotals]]):
    """Aggregates Earn rewards from the operation history.

    /operations needs the Transaction scope. Setup already
    checks every required scope, so a 401 here means the key expired, was
    revoked, or predates that requirement (a migrated legacy key) -- each
    case is answered by a new key, so it raises ConfigEntryAuthFailed the
    same as every other coordinator, instead of degrading silently.

    A listing that cannot be paged completely raises too (see
    BitpandaApiClient._paginate) and becomes UpdateFailed: the rewards
    attributes then stay absent, or keep the last complete totals, rather
    than showing a recount over part of the history.

    Like every DataUpdateCoordinator it polls only while something listens,
    and only Staking sensors do: see async_refresh_if_stale.

    After every successful refresh it calls `on_refreshed`, the announcement
    of new payouts (announcements.RewardAnnouncer). That call is no listener:
    a listener would keep the coordinator reading the whole history every
    hour even with every Staking sensor disabled.
    """

    config_entry: PortfolioConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: PortfolioConfigEntry, client: BitpandaApiClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_rewards",
            update_interval=REWARDS_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._client = client
        # Set by the announcer of new payouts; None where nothing announces.
        self.on_refreshed: Callable[[], None] | None = None

    async def _async_update_data(self) -> dict[str, RewardTotals]:
        try:
            operations = await self._client.async_get_operations()
        except BitpandaAuthError:
            raise _auth_failed() from None
        except BitpandaApiError as err:
            raise _update_failed(err) from None
        return sum_rewards(operations)

    @callback
    def _async_refresh_finished(self) -> None:
        """Home Assistant's hook after every refresh, before the listeners
        are told (2025.5.0 and 2026.9.4 alike): the announcer runs after a
        successful one only."""
        super()._async_refresh_finished()
        if self.last_update_success and self.on_refreshed is not None:
            self.on_refreshed()

    @callback
    def async_refresh_if_stale(self) -> None:
        """Refresh in the background when the totals are missing or older
        than REWARDS_UPDATE_INTERVAL.

        Nothing polls this coordinator while no Staking sensor listens, so
        the first one added after setup -- the first time anything is staked
        since -- would show the totals of setup's own refresh, or none if
        that failed, for up to another interval. Each Staking sensor calls
        this as it is added. Current totals request nothing, and a burst of
        new sensors does not multiply the requests: async_request_refresh is
        debounced.
        """
        fetched = self.last_update_success_time
        if (
            self.data is not None
            and fetched is not None
            and dt_util.utcnow() - fetched < REWARDS_UPDATE_INTERVAL
        ):
            return
        self.config_entry.async_create_background_task(
            self.hass, self.async_request_refresh(), f"{DOMAIN} rewards refresh"
        )


async def collect_returns(
    client: BitpandaApiClient, currency_id: str | None
) -> PortfolioReturns:
    """Fetch return_percentage for every timeframe.

    One request per timeframe — there is no combined call. A failure on one
    window is logged and recorded in `failed`, so the others still report
    and its sensor alone is affected (HistoryCoordinator keeps its last
    return until the failure is confirmed). An auth error is different: it
    will not resolve by trying the next timeframe, so it propagates
    immediately instead of being counted as one of five failures --
    otherwise five 401s would read as "No portfolio history could be
    fetched" (an UpdateFailed) and the caller would never see the
    BitpandaAuthError it needs to start reauth.

    The API sends return_percentage as a JSON string today (observed
    2026-09-25); plain numbers are still accepted in case that changes back.
    Either way the value must parse to a finite float or it is dropped, same
    as any other unusable value -- a timeframe answered without a figure,
    whose return is unknown, not a failed one.
    """
    out: dict[str, float] = {}
    failed: set[str] = set()
    for timeframe in PORTFOLIO_TIMEFRAMES:
        try:
            body = await client.async_get_portfolio_history(
                timeframe=timeframe, equivalent_currency_id=currency_id
            )
        except BitpandaAuthError:
            raise
        except BitpandaApiError:
            failed.add(timeframe)
            _LOGGER.debug("No history for timeframe %s this cycle", timeframe)
            continue
        value = body.get("return_percentage")
        if isinstance(value, bool):
            # isinstance(True, int) is True in Python, so a boolean would be
            # stored as 1.0 — data that looks real. A dropped key is honest.
            continue
        if isinstance(value, (int, float)):
            parsed = float(value)
        elif isinstance(value, str):
            try:
                parsed = float(value.strip())
            except ValueError:
                continue
        else:
            continue
        if math.isfinite(parsed):
            out[timeframe] = parsed

    # Raise only when every *request* failed. Returning no figure normally
    # would leave last_update_success True, making a dead endpoint
    # indistinguishable from "no data yet" — forever, at any log level. But
    # an account whose history is genuinely empty answers all five requests
    # successfully with no usable return_percentage, and that must not be
    # reported as an outage, or it would fail on every cycle.
    if len(failed) == len(PORTFOLIO_TIMEFRAMES):
        raise UpdateFailed(
            translation_domain=DOMAIN, translation_key="history_unavailable"
        )

    return PortfolioReturns(values=out, failed=frozenset(failed))


class HistoryCoordinator(TolerantCoordinator[PortfolioReturns]):
    """Portfolio return over each supported timeframe.

    A refresh in which every request fails is a failed refresh like any
    other: the return sensors keep the last data until the failure is
    confirmed (tolerance.py). A timeframe whose own request fails while the
    others answer follows the same rule on its own: it keeps its last return
    until its own streak is confirmed (tolerate_failed_timeframes). Every
    refresh without a fresh return counts for a timeframe, one that fails as
    a whole included: so a return from before a confirmed outage never
    comes back after it, and a timeframe still failing then is unavailable
    at once. A refresh that fails as a whole and confirms a carried
    timeframe's own failure fails it at once, as one that returns data
    would.
    """

    config_entry: PortfolioConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PortfolioConfigEntry,
        client: BitpandaApiClient,
        currency_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_history",
            update_interval=PORTFOLIO_UPDATE_INTERVAL,
            regular_interval=PORTFOLIO_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._client = client
        self._currency_id = currency_id
        # Timeframe -> its refreshes in a row without a fresh return.
        self._streaks: dict[str, FailureStreak] = {}

    @property
    def failing_timeframes(self) -> frozenset[str]:
        """The timeframes whose requests fail now -- carried over, confirmed
        or without a last return alike. The real outcome, which diagnostics
        report: PortfolioReturns.failed holds only the timeframes the
        sensors show as unavailable."""
        return frozenset(self._streaks)

    async def _async_fetch(self, requested_at: datetime) -> PortfolioReturns:
        try:
            result = await collect_returns(self._client, self._currency_id)
        except BitpandaAuthError:
            raise _auth_failed() from None
        except UpdateFailed:
            # Every request failed: no timeframe has a fresh return, and the
            # refresh counts for each of them. A last return whose own
            # failure this confirms is shown no longer -- the data loses it,
            # and tolerance.py tells the listeners.
            shown = tolerate_failed_timeframes(
                PortfolioReturns(values={}, failed=frozenset(PORTFOLIO_TIMEFRAMES)),
                self.data,
                self._streaks,
                requested_at,
                self._regular_interval,
            )
            if self.data is not None and shown != self.data:
                self.data = shown
            raise
        return tolerate_failed_timeframes(
            result, self.data, self._streaks, requested_at, self._regular_interval
        )


@dataclass
class PortfolioRuntime:
    """What a loaded Portfolio entry keeps in `entry.runtime_data`."""

    portfolio: PortfolioCoordinator
    history: HistoryCoordinator
    earn: EarnCoordinator
    rewards: RewardsCoordinator
    # Category -> wallet group title, in the entry's language at setup
    # (groups.async_group_titles). The wallet manager reconciles
    # synchronously and titles the groups it creates from these.
    group_titles: dict[str, str]
    # entry.data and entry.options as they were at setup: the update listener
    # reloads the entry only once either of them differs. entry.data holds
    # the API key, so both fields are excluded from the dataclass's generated
    # repr -- HA's profiler services (dump_log_objects, start_log_object_sources)
    # log object reprs at CRITICAL, and would otherwise write the key into
    # home-assistant.log.
    data_at_setup: dict[str, Any] = field(repr=False)
    options_at_setup: dict[str, Any] = field(repr=False)
    # The assets the Portfolio knows -- announced, or there when the list
    # began -- and when the newest staking payout announced per asset was
    # credited (portfolio_store.py): set at setup, None where a test builds a
    # runtime without them.
    known_wallets: KnownWallets | None = field(default=None, repr=False)
    reward_marks: RewardMarks | None = field(default=None, repr=False)


# A Portfolio config entry, its runtime data typed.
type PortfolioConfigEntry = ConfigEntry[PortfolioRuntime]
