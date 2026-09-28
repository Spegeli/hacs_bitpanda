"""Coordinators of the Portfolio service.

Every request here carries the API key, except the asset lookups, which the
AssetDirectory makes keyless. Every 401 raises ConfigEntryAuthFailed, which
Home Assistant turns into the reauth dialog.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er
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
    PORTFOLIO_TIMEFRAMES,
    PORTFOLIO_UPDATE_INTERVAL,
    REWARDS_UPDATE_INTERVAL,
)
from .naming import managed_asset_id
from .portfolio_model import (
    EarnData,
    PortfolioData,
    PortfolioReturns,
    RewardTotals,
    confirmed,
    lists_nothing,
    parse_earn_configs,
    parse_portfolio,
    sum_rewards,
    tolerate_failed_timeframes,
)
from .streaks import FailureStreak
from .tolerance import TolerantCoordinator

_LOGGER = logging.getLogger(__name__)

# What the check of empty /portfolio answers (see PortfolioCoordinator)
# keeps per Portfolio entry: the empty answers in a row since the last one
# taken as the truth, an _EmptyStreak, and whether the last answer taken as
# the truth listed anything. In hass.data rather than on the coordinator, so
# both outlive a reload -- a currency change's included -- or a failed setup,
# but not the entry itself (async_forget_empty_answers). Nor a restart:
# hass.data starts empty, and until the first answer taken as the truth the
# registered wallets alone tell whether the account listed something.
_EMPTY_ANSWERS = f"{DOMAIN}_empty_portfolio_answers"
_LISTED = f"{DOMAIN}_portfolio_listed"


@dataclass
class _EmptyStreak:
    """Empty answers in a row, and when the first of them was asked for."""

    count: int
    since: datetime


@callback
def async_forget_empty_answers(hass: HomeAssistant, entry_id: str) -> None:
    """Drop what the check of empty answers keeps of an entry that is being
    removed: its count of empty answers, and whether its account listed
    anything."""
    hass.data.get(_EMPTY_ANSWERS, {}).pop(entry_id, None)
    hass.data.get(_LISTED, {}).pop(entry_id, None)


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

    A completely empty answer -- no asset and no fiat entry at all -- from
    an account that listed something before is far more likely a glitch at
    Bitpanda than a sale of everything. Such an answer fails the update
    instead: a failed refresh the tolerance covers like any other
    (tolerance.py), so the sensors keep the last figures, and the wallet
    manager, which acts only on successful refreshes, counts no miss and
    removes nothing. Only an empty answer that makes WALLET_REMOVAL_MISSES
    of them in a row, WALLET_REMOVAL_TIME after the first was asked for
    (portfolio_model.confirmed), is taken as the truth: Total 0, and from
    then on every empty answer is too, and the wallets count as missing as
    usual. At the regular pace the third answer confirms -- the refresh that
    would otherwise end the tolerance -- so the figures go from the last
    ones to 0, never unavailable; with a failed request among the empty
    answers the tolerance can end first, and the sensors are unavailable
    until an answer is taken as the truth. Refreshes by hand or a reload
    bring answers sooner, and they count, but never confirm sooner. A
    failed request neither counts nor resets the streak; any answer taken
    as the truth clears it.

    Listed something before: the last answer taken as the truth for this
    entry listed holdings or fiat. That and the streak are kept in
    hass.data, so a reload -- a currency change's too, whose purge has just
    removed the wallets -- or a setup that is retried goes on where the last
    coordinator stopped. hass.data does not survive a restart, though: until
    the first answer taken as the truth after one, the registered wallets of
    this entry stand in, and an account that listed fiat alone has none. An
    empty answer from an account that never listed anything -- a new, empty
    account -- is the truth at once, so its setup works.

    Every answer carries the time it was asked for (PortfolioData.
    requested_at, Home Assistant's clock), by which the wallet manager times
    its misses the same way.
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

    async def _async_fetch(self, requested_at: datetime) -> PortfolioData:
        try:
            entries = await self._client.async_get_portfolio(
                equivalent_currency_id=self._currency_id
            )
        except BitpandaAuthError:
            raise _auth_failed() from None
        except BitpandaApiError as err:
            raise _update_failed(err) from None
        self._check_empty_answer(entries, requested_at)
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
        return data

    def _check_empty_answer(
        self, entries: list[dict[str, Any]], requested_at: datetime
    ) -> None:
        """Raise UpdateFailed for an empty answer not confirmed yet; count
        or clear the empty answers in a row, and remember whether the answer
        taken as the truth listed anything (see the class docstring)."""
        streaks: dict[str, _EmptyStreak] = self.hass.data.setdefault(_EMPTY_ANSWERS, {})
        listed: dict[str, bool] = self.hass.data.setdefault(_LISTED, {})
        entry_id = self.config_entry.entry_id
        empty = lists_nothing(entries)
        # None before the first answer taken as the truth since Home
        # Assistant started -- hass.data does not survive a restart -- when
        # the registered wallets stand in.
        remembered = listed.get(entry_id)
        if empty and (remembered if remembered is not None else self._has_wallets()):
            streak = streaks.get(entry_id) or _EmptyStreak(count=0, since=requested_at)
            streak.count += 1
            if not confirmed(streak.count, streak.since, requested_at):
                streaks[entry_id] = streak
                raise UpdateFailed(
                    translation_domain=DOMAIN, translation_key="portfolio_empty"
                )
        streaks.pop(entry_id, None)
        listed[entry_id] = not empty

    def _has_wallets(self) -> bool:
        """Whether wallets of this entry are registered -- wallet, staking
        or total sensors: the account listed something before."""
        entry_id = self.config_entry.entry_id
        return any(
            managed_asset_id(entry_id, reg_entry.unique_id) is not None
            for reg_entry in er.async_entries_for_config_entry(er.async_get(self.hass), entry_id)
        )


class EarnCoordinator(DataUpdateCoordinator[EarnData]):
    """Polls the Earn product catalogue once a day."""

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
            return parse_earn_configs(await self._client.async_get_earn_configs())
        except BitpandaAuthError:
            raise _auth_failed() from None
        except BitpandaApiError as err:
            raise _update_failed(err) from None


class RewardsCoordinator(TimestampDataUpdateCoordinator[dict[str, RewardTotals]]):
    """Aggregates Earn rewards from the operation history.

    /operations needs the Transaktion (Transaction) scope. Setup already
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

    async def _async_update_data(self) -> dict[str, RewardTotals]:
        try:
            operations = await self._client.async_get_operations()
        except BitpandaAuthError:
            raise _auth_failed() from None
        except BitpandaApiError as err:
            raise _update_failed(err) from None
        return sum_rewards(operations)

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


# A Portfolio config entry, its runtime data typed.
type PortfolioConfigEntry = ConfigEntry[PortfolioRuntime]
