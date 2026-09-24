"""Data update coordinators for the Bitpanda integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BitpandaApiClient, BitpandaApiError
from .const import (
    DOMAIN,
    EUR_CURRENCY_ID,
    HOURLY_READ_BUDGET,
    PORTFOLIO_UPDATE_INTERVAL,
    PRICE_BUDGET_SHARE,
    PRICE_UPDATE_INTERVAL_BASE,
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

        needed = [a for a in self._tracked if a not in held]
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
            holding = held.get(asset_id)
            if holding and holding.balance:
                prices[asset_id] = holding.value / holding.balance

        for asset_id in needed:
            try:
                ticker = await self._client.async_get_ticker(asset_id)
            except BitpandaApiError:
                _LOGGER.debug("No ticker for %s this cycle", asset_id)
                continue
            converted = convert_price(ticker.get("price", ""), rate)
            if converted is not None:
                prices[asset_id] = converted

        if not prices and needed:
            raise UpdateFailed("No prices could be fetched")
        return prices
