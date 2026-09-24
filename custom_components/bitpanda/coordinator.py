"""Data update coordinators for the Bitpanda integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BitpandaApiClient, BitpandaApiError
from .const import DOMAIN, EUR_CURRENCY_ID, PORTFOLIO_UPDATE_INTERVAL
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
