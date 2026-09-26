"""Coordinators of the Portfolio service.

Every request here carries the API key, except the asset lookups, which the
AssetDirectory makes keyless. Every 401 raises ConfigEntryAuthFailed, which
Home Assistant turns into the reauth dialog.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    WALLET_REMOVAL_MISSES,
)
from .naming import managed_asset_id
from .portfolio_model import (
    EarnData,
    PortfolioData,
    PortfolioReturns,
    RewardTotals,
    lists_nothing,
    parse_earn_configs,
    parse_portfolio,
    sum_rewards,
)

_LOGGER = logging.getLogger(__name__)

# Empty /portfolio answers in a row, per Portfolio entry, since the last one
# taken as the truth (see PortfolioCoordinator). In hass.data rather than on
# the coordinator, so the count outlives a reload or a failed setup -- but
# not the entry itself (async_forget_empty_answers).
_EMPTY_ANSWERS = f"{DOMAIN}_empty_portfolio_answers"


@callback
def async_forget_empty_answers(hass: HomeAssistant, entry_id: str) -> None:
    """Drop the count of empty answers of an entry that is being removed."""
    hass.data.get(_EMPTY_ANSWERS, {}).pop(entry_id, None)


def _auth_failed() -> ConfigEntryAuthFailed:
    """The key was rejected: Home Assistant asks for a new one. Translated,
    so the integration page gives the reason in the user's language; nothing
    of the request reaches the message."""
    return ConfigEntryAuthFailed(translation_domain=DOMAIN, translation_key="api_key_rejected")


# The text of each kind of failed request (const.API_ERROR_KINDS).
_UPDATE_FAILED_KEYS = {
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


class PortfolioCoordinator(DataUpdateCoordinator[PortfolioData]):
    """Polls /portfolio in the Portfolio currency and names the holdings.

    Values arrive converted by Bitpanda (`equivalent_currency_id`): no
    exchange rate is derived or applied here.

    A completely empty answer -- no asset and no fiat entry at all -- from
    an account that listed something before is far more likely a glitch at
    Bitpanda than a sale of everything. Listed something before: the last
    answer this coordinator took as the truth did, or, for its first answer
    -- after a restart or a reload -- wallets of this entry are registered.
    Such an answer fails the update instead: the sensors go unavailable,
    and the wallet manager, which acts only on successful refreshes, counts
    no miss and removes nothing. Only the answer that makes
    WALLET_REMOVAL_MISSES empty ones in a row is taken as the truth: Total
    0, and from then on every empty answer is too, and the wallets count as
    missing as usual. The count lives in hass.data, so a reload -- or a
    setup that is retried -- goes on counting where the last coordinator
    stopped. A failed request neither counts nor resets it; any answer taken
    as the truth clears it. An empty first answer with no wallet registered
    -- a new, empty account -- is the truth at once, so its setup works.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BitpandaApiClient,
        currency_id: str,
        directory: AssetDirectory,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_portfolio",
            update_interval=PORTFOLIO_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._client = client
        self._currency_id = currency_id
        self._directory = directory
        # Whether the last answer this coordinator took as the truth listed
        # anything; None before its first (see the class docstring).
        self._listed: bool | None = None

    async def _async_update_data(self) -> PortfolioData:
        try:
            entries = await self._client.async_get_portfolio(
                equivalent_currency_id=self._currency_id
            )
        except BitpandaAuthError:
            raise _auth_failed() from None
        except BitpandaApiError as err:
            raise _update_failed(err) from None
        self._check_empty_answer(entries)
        data = parse_portfolio(entries)
        # Never raises: a failed lookup leaves the holdings not named yet
        # unnamed until the next refresh instead of failing the portfolio.
        await self._directory.async_resolve(data.holdings)
        data.assets = {
            asset_id: record
            for asset_id in data.holdings
            if (record := self._directory.get(asset_id)) is not None
        }
        return data

    def _check_empty_answer(self, entries: list[dict]) -> None:
        """Raise UpdateFailed for an empty answer not confirmed yet; count
        or clear the empty answers in a row (see the class docstring)."""
        counts: dict[str, int] = self.hass.data.setdefault(_EMPTY_ANSWERS, {})
        entry_id = self.config_entry.entry_id
        empty = lists_nothing(entries)
        if empty and (self._listed if self._listed is not None else self._has_wallets()):
            count = counts.get(entry_id, 0) + 1
            if count < WALLET_REMOVAL_MISSES:
                counts[entry_id] = count
                raise UpdateFailed(
                    translation_domain=DOMAIN, translation_key="portfolio_empty"
                )
        counts.pop(entry_id, None)
        self._listed = not empty

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

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: BitpandaApiClient
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


class RewardsCoordinator(TimestampDataUpdateCoordinator[dict]):
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

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: BitpandaApiClient
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
    and its sensor alone goes unavailable. An auth error is different: it
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


class HistoryCoordinator(DataUpdateCoordinator[PortfolioReturns]):
    """Portfolio return over each supported timeframe."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BitpandaApiClient,
        currency_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_history",
            update_interval=PORTFOLIO_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._client = client
        self._currency_id = currency_id

    async def _async_update_data(self) -> PortfolioReturns:
        try:
            return await collect_returns(self._client, self._currency_id)
        except BitpandaAuthError:
            raise _auth_failed() from None


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
