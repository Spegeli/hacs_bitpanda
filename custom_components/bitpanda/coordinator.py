"""Data update coordinators for the Bitpanda integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BitpandaApiClient, BitpandaApiError, BitpandaAuthError
from .const import (
    DOMAIN,
    EARN_UPDATE_INTERVAL,
    EUR_CURRENCY_ID,
    HOURLY_READ_BUDGET,
    PORTFOLIO_TIMEFRAMES,
    PORTFOLIO_UPDATE_INTERVAL,
    PRICE_BUDGET_SHARE,
    PRICE_UPDATE_INTERVAL_BASE,
    REWARDS_UPDATE_INTERVAL,
)
from .fx import derive_rate

_LOGGER = logging.getLogger(__name__)


def _to_float(container: dict | None, key: str = "value") -> float | None:
    """Read a numeric string out of an API value object."""
    if not isinstance(container, dict):
        return None
    try:
        return float(container[key])
    except (KeyError, TypeError, ValueError):
        return None


@dataclass
class Holding:
    """One asset position, already valued in the display currency."""

    asset_id: str
    balance: float
    available: float
    staked: float
    value: float
    invested: float | None = None
    avg_buy_price: float | None = None
    total_return: float | None = None
    total_return_pct: float | None = None


@dataclass
class PortfolioData:
    """Normalised portfolio response."""

    holdings: dict[str, Holding] = field(default_factory=dict)
    fiat: dict[str, float] = field(default_factory=dict)
    rate: float | None = None
    total: float = 0.0


def parse_portfolio(entries: list[dict], *, rate: float | None) -> PortfolioData:
    """Normalise a /portfolio response.

    The response mixes two shapes and there is no type field, so the split is
    on the presence of `asset_id`.

    `currency_balance` is the fiat value computed server-side. It is used as
    given. Multiplying a balance by a price here is what produced issue #7,
    where an index wallet showed 9,251,679 EUR instead of 431.44.
    """
    data = PortfolioData(rate=rate)
    total = 0.0

    for entry in entries:
        asset_id = entry.get("asset_id")
        if not asset_id:
            currency_id = entry.get("currency_id")
            amount = _to_float(entry.get("available_balance"))
            if currency_id and amount is not None:
                data.fiat[currency_id] = amount
                total += amount
            continue

        balance = _to_float(entry.get("balance"))
        available = _to_float(entry.get("available_balance"))
        if balance is None or available is None:
            _LOGGER.debug("Skipping unparsable holding %s", asset_id)
            continue

        value = _to_float(entry.get("currency_balance")) or 0.0
        try:
            return_pct = float(entry["total_return_percent"])
        except (KeyError, TypeError, ValueError):
            return_pct = None

        data.holdings[asset_id] = Holding(
            asset_id=asset_id,
            balance=balance,
            available=available,
            staked=max(balance - available, 0.0),
            value=value,
            invested=_to_float(entry.get("invested_amount")),
            avg_buy_price=_to_float(entry.get("average_buy_price")),
            total_return=_to_float(entry.get("total_return")),
            total_return_pct=return_pct,
        )
        total += value

    data.total = round(total, 2)
    return data


class PortfolioCoordinator(DataUpdateCoordinator[PortfolioData]):
    """Polls /portfolio and, when converting, derives the currency rate."""

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
            name=f"{DOMAIN}_portfolio",
            update_interval=PORTFOLIO_UPDATE_INTERVAL,
            config_entry=entry,
        )
        self._client = client
        self._currency_id = currency_id

    async def _async_update_data(self) -> PortfolioData:
        try:
            entries = await self._client.async_get_portfolio(
                equivalent_currency_id=self._currency_id
            )
            rate = None
            if self._currency_id != EUR_CURRENCY_ID:
                eur_entries = await self._client.async_get_portfolio(
                    equivalent_currency_id=EUR_CURRENCY_ID
                )
                rate = derive_rate(eur_entries, entries)
        except BitpandaApiError as err:
            raise UpdateFailed(str(err)) from None
        return parse_portfolio(entries, rate=rate)


# Past this the data is stale enough to be worth telling the user about.
# It is a warning threshold, never a cap — see price_interval.
_SLOW_PRICE_INTERVAL = timedelta(minutes=30)


def price_interval(ticker_count: int) -> timedelta:
    """Return a poll interval that keeps ticker calls inside the budget.

    There is no batch ticker, so each tracked-but-unheld asset costs one
    request per poll. The read budget is 3000/hour; PRICE_BUDGET_SHARE of it
    is reserved for prices, leaving room for portfolio, earn and rewards.

    The result is deliberately uncapped. An earlier version clamped it to 30
    minutes, which silently broke the guarantee above once the tracked set
    passed 900 assets: at the clamp, 900 assets exactly exhaust the
    allowance, and 5000 would issue 10000 requests an hour against a total
    budget of 3000. A slow sensor is a visible annoyance; a rate-limited one
    fails in ways nobody can diagnose.
    """
    if ticker_count <= 0:
        return PRICE_UPDATE_INTERVAL_BASE

    allowance = HOURLY_READ_BUDGET * PRICE_BUDGET_SHARE
    required_seconds = ticker_count * 3600 / allowance
    seconds = max(PRICE_UPDATE_INTERVAL_BASE.total_seconds(), required_seconds)
    return timedelta(seconds=seconds)


def convert_price(price: str, rate: float | None) -> float | None:
    """Convert an EUR ticker price into the display currency.

    /tickers always returns EUR. `rate` is units of the display currency per
    EUR, or None when no conversion is needed or possible.
    """
    try:
        value = float(price)
    except (TypeError, ValueError):
        return None
    return value if rate is None else value * rate


class PriceCoordinator(DataUpdateCoordinator[dict]):
    """Fetches tickers for tracked assets that are not held."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BitpandaApiClient,
        portfolio: PortfolioCoordinator,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_prices",
            update_interval=PRICE_UPDATE_INTERVAL_BASE,
            config_entry=entry,
        )
        self._client = client
        self._portfolio = portfolio
        self._tracked: list[str] = []

    def set_tracked(self, asset_ids: list[str]) -> None:
        """Set which asset ids have price sensors."""
        self._tracked = list(asset_ids)

    async def _async_update_data(self) -> dict[str, float]:
        portfolio = self._portfolio.data
        held = portfolio.holdings if portfolio else {}
        rate = portfolio.rate if portfolio else None

        # A holding priced from the portfolio needs a non-zero balance to
        # divide by. Anything else — not held at all, or held at zero — must
        # fall through to a ticker call, or it would get no price from either
        # path and no log line saying why.
        def _priceable_from_portfolio(asset_id: str) -> bool:
            holding = held.get(asset_id)
            return holding is not None and holding.balance > 0

        needed = [a for a in self._tracked if not _priceable_from_portfolio(a)]
        self.update_interval = price_interval(len(needed))

        if self.update_interval > _SLOW_PRICE_INTERVAL:
            _LOGGER.warning(
                "Tracking %s assets you do not hold; prices will refresh only "
                "every %s to stay inside the API rate limit. Track fewer "
                "assets for more frequent updates.",
                len(needed),
                self.update_interval,
            )

        prices: dict[str, float] = {}

        # Held assets: derive the unit price from the portfolio, no request.
        for asset_id in self._tracked:
            if _priceable_from_portfolio(asset_id):
                holding = held[asset_id]
                prices[asset_id] = holding.value / holding.balance

        ticker_failures = 0
        for asset_id in needed:
            try:
                ticker = await self._client.async_get_ticker(asset_id)
            except BitpandaApiError:
                ticker_failures += 1
                _LOGGER.debug("No ticker for %s this cycle", asset_id)
                continue
            converted = convert_price(ticker.get("price", ""), rate)
            if converted is not None:
                prices[asset_id] = converted

        if not prices and needed:
            raise UpdateFailed("No prices could be fetched")

        # Partial data still beats none, so held prices are returned rather
        # than failing the whole update. But a ticker endpoint that is down
        # for every asset must not be visible only at DEBUG level, which
        # nobody has enabled.
        if needed and ticker_failures == len(needed):
            _LOGGER.warning(
                "Every one of the %s ticker requests failed this cycle. "
                "Prices for assets you do not hold are stale; values for "
                "assets you hold are unaffected.",
                len(needed),
            )

        return prices


def _is_later(candidate: str | None, current: str | None) -> bool:
    """Return True when `candidate` is the later of two API timestamps.

    Comparing these as strings is wrong. The API emits both
    `2026-09-22T17:16:35Z` and `2026-09-09T18:31:22.080Z`, and within the
    same second `"." < "Z"`, so a zero-fraction timestamp sorts *above* a
    later fractional one. Parse instead, and fall back to string comparison
    only if parsing fails.
    """
    if not candidate:
        return False
    if not current:
        return True
    try:
        return datetime.fromisoformat(candidate) > datetime.fromisoformat(current)
    except (TypeError, ValueError):
        # ValueError for a malformed string; TypeError for a non-string, and
        # for comparing an offset-aware datetime against a naive one. Every
        # timestamp seen from this endpoint carries a Z, but it is undocumented
        # and a mixed batch must not raise out of a coordinator refresh.
        return str(candidate) > str(current)


@dataclass
class RewardTotals:
    """Lifetime Earn rewards for one asset, in that asset's own units."""

    gross: float = 0.0
    fee: float = 0.0
    net: float = 0.0
    count: int = 0
    last_at: str | None = None


def map_earn_configs(configs: list[dict]) -> dict[str, float]:
    """Map asset id to annual percentage rate.

    The rate is a JSON number and a fraction: 0.0544 means 5.44 %. Sold-out
    products keep their rate — `soldout` and `enabled` are separate flags.
    """
    out: dict[str, float] = {}
    for config in configs:
        asset_id = config.get("asset_id")
        rate = config.get("annual_percentage_rate")
        if asset_id and isinstance(rate, (int, float)):
            out[asset_id] = float(rate)
    return out


def sum_rewards(operations: list[dict]) -> dict[str, RewardTotals]:
    """Aggregate staking rewards per asset.

    Only `operation_type == "reward"` with `wallet_owner == "staking-service"`
    counts. `earn_on_fiat_reward` is Cash Plus interest, a different product.
    The operation_type enum is open — 29 values were seen in a single account —
    so anything unrecognised is ignored rather than raising.

    The fee is charged in the reward asset and is not a fixed rate: recent
    payouts showed exactly 20 % while lifetime aggregates sat near 17 %. Always
    read `fee_amount`.
    """
    totals: dict[str, RewardTotals] = {}

    for operation in operations:
        if operation.get("operation_type") != "reward":
            continue
        for tx in operation.get("transactions", []):
            if tx.get("wallet_owner") != "staking-service":
                continue
            asset_id = tx.get("asset_id")
            gross = _to_float(tx.get("asset_amount"))
            if not asset_id or gross is None:
                continue
            fee = _to_float(tx.get("fee_amount")) or 0.0

            entry = totals.setdefault(asset_id, RewardTotals())
            entry.gross += gross
            entry.fee += fee
            entry.net += gross - fee
            entry.count += 1

            credited = tx.get("credited_at")
            if _is_later(credited, entry.last_at):
                entry.last_at = credited

    return totals


class EarnCoordinator(DataUpdateCoordinator[dict]):
    """Polls the Earn product catalog once a day."""

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

    async def _async_update_data(self) -> dict[str, float]:
        try:
            return map_earn_configs(await self._client.async_get_earn_configs())
        except BitpandaApiError as err:
            raise UpdateFailed(str(err)) from None


class RewardsCoordinator(DataUpdateCoordinator[dict]):
    """Aggregates Earn rewards from the operation history.

    Requires a key with all read scopes. A portfolio-capable key returns 401,
    in which case this coordinator reports no data and sets `unauthorized`,
    leaving every other part of the integration working.
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
        self.unauthorized = False

    async def _async_update_data(self) -> dict[str, RewardTotals]:
        if self.unauthorized:
            return {}
        try:
            operations = await self._client.async_get_operations()
        except BitpandaAuthError:
            self.unauthorized = True
            _LOGGER.info(
                "Earn reward totals unavailable: the API key lacks the scope "
                "required for operation history. Every other feature is "
                "unaffected."
            )
            return {}
        except BitpandaApiError as err:
            raise UpdateFailed(str(err)) from None
        return sum_rewards(operations)


async def collect_returns(
    client: BitpandaApiClient, currency_id: str | None
) -> dict[str, float]:
    """Fetch return_percentage for every timeframe.

    One request per timeframe — there is no combined call. A failure on one
    window is logged and skipped so the others still report.
    """
    out: dict[str, float] = {}
    for timeframe in PORTFOLIO_TIMEFRAMES:
        try:
            body = await client.async_get_portfolio_history(
                timeframe=timeframe, equivalent_currency_id=currency_id
            )
        except BitpandaApiError:
            _LOGGER.debug("No history for timeframe %s this cycle", timeframe)
            continue
        value = body.get("return_percentage")
        if isinstance(value, bool):
            # isinstance(True, int) is True in Python, so a boolean would be
            # stored as 1.0 — data that looks real. A dropped key is honest.
            continue
        if isinstance(value, (int, float)):
            out[timeframe] = float(value)

    # PORTFOLIO_TIMEFRAMES is a fixed five-entry constant, so an empty result
    # can only mean every request failed. Returning {} normally would leave
    # last_update_success True, making a dead endpoint indistinguishable from
    # "no data yet" — forever, at any log level.
    if not out:
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
        return await collect_returns(self._client, self._currency_id)
