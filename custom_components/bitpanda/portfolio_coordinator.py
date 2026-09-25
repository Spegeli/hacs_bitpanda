"""Coordinators of the Portfolio service.

Every request here carries the API key, except the asset lookups, which the
AssetDirectory makes keyless. Every 401 raises ConfigEntryAuthFailed, which
Home Assistant turns into the reauth dialog.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
import math

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BitpandaApiClient, BitpandaApiError, BitpandaAuthError
from .assets import AssetDirectory
from .const import (
    DOMAIN,
    EARN_UPDATE_INTERVAL,
    PORTFOLIO_TIMEFRAMES,
    PORTFOLIO_UPDATE_INTERVAL,
    REWARDS_UPDATE_INTERVAL,
)
from .portfolio_model import (
    EarnData,
    PortfolioData,
    RewardTotals,
    parse_earn_configs,
    parse_portfolio,
    sum_rewards,
)

_LOGGER = logging.getLogger(__name__)

_AUTH_FAILED = "Bitpanda rejected the API key"


class PortfolioCoordinator(DataUpdateCoordinator[PortfolioData]):
    """Polls /portfolio in the Portfolio currency and names the holdings.

    Values arrive converted by Bitpanda (`equivalent_currency_id`): no
    exchange rate is derived or applied here.
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

    async def _async_update_data(self) -> PortfolioData:
        try:
            entries = await self._client.async_get_portfolio(
                equivalent_currency_id=self._currency_id
            )
        except BitpandaAuthError:
            raise ConfigEntryAuthFailed(_AUTH_FAILED) from None
        except BitpandaApiError as err:
            raise UpdateFailed(str(err)) from None
        data = parse_portfolio(entries)
        # Never raises: a lookup that fails leaves that one holding unnamed
        # until the next refresh instead of failing the portfolio.
        await self._directory.async_resolve(data.holdings)
        data.assets = {
            asset_id: record
            for asset_id in data.holdings
            if (record := self._directory.get(asset_id)) is not None
        }
        return data


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
            raise ConfigEntryAuthFailed(_AUTH_FAILED) from None
        except BitpandaApiError as err:
            raise UpdateFailed(str(err)) from None


class RewardsCoordinator(DataUpdateCoordinator[dict]):
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
            raise ConfigEntryAuthFailed(_AUTH_FAILED) from None
        except BitpandaApiError as err:
            raise UpdateFailed(str(err)) from None
        return sum_rewards(operations)


async def collect_returns(
    client: BitpandaApiClient, currency_id: str | None
) -> dict[str, float]:
    """Fetch return_percentage for every timeframe.

    One request per timeframe — there is no combined call. A failure on one
    window is logged and skipped so the others still report. An auth error is
    different: it will not resolve by trying the next timeframe, so it
    propagates immediately instead of being counted as one of five failures --
    otherwise five 401s would read as "No portfolio history could be
    fetched" (an UpdateFailed) and the caller would never see the
    BitpandaAuthError it needs to start reauth.

    The API sends return_percentage as a JSON string today (observed
    2026-09-25); plain numbers are still accepted in case that changes back.
    Either way the value must parse to a finite float or it is dropped, same
    as any other unusable value -- a missing timeframe, not a bad one.
    """
    out: dict[str, float] = {}
    failures = 0
    for timeframe in PORTFOLIO_TIMEFRAMES:
        try:
            body = await client.async_get_portfolio_history(
                timeframe=timeframe, equivalent_currency_id=currency_id
            )
        except BitpandaAuthError:
            raise
        except BitpandaApiError:
            failures += 1
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

    # Raise only when every *request* failed. Returning {} normally would
    # leave last_update_success True, making a dead endpoint indistinguishable
    # from "no data yet" — forever, at any log level. But an account whose
    # history is genuinely empty answers all five requests successfully with
    # no usable return_percentage, and that must not be reported as an
    # outage, or it would fail on every cycle.
    if failures == len(PORTFOLIO_TIMEFRAMES):
        raise UpdateFailed("No portfolio history could be fetched")

    return out


class HistoryCoordinator(DataUpdateCoordinator[dict]):
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

    async def _async_update_data(self) -> dict[str, float]:
        try:
            return await collect_returns(self._client, self._currency_id)
        except BitpandaAuthError:
            raise ConfigEntryAuthFailed(_AUTH_FAILED) from None


@dataclass
class PortfolioRuntime:
    """What a loaded Portfolio entry keeps in `entry.runtime_data`."""

    portfolio: PortfolioCoordinator
    history: HistoryCoordinator
    earn: EarnCoordinator
    rewards: RewardsCoordinator
