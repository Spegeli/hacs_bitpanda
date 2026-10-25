"""The Portfolio's actions with response data -- bitpanda.get_portfolio,
bitpanda.get_portfolio_history and bitpanda.get_staking_rewards --
registered with the integration (async_setup), as bitpanda.refresh is.

They answer from what the Portfolio holds -- its coordinators' data, the
wallets' price round, the 24-hour references, the operations read so far --
and never ask Bitpanda. Each is a callback, awaiting nothing, so an unload
never comes in between. Figures are rounded as the sensors' attributes are
(the helpers of portfolio_model.py); a figure that waits, or a timeframe
that failed, reads null. The response formats are interfaces: fields may
be added, never renamed or dropped.
"""
from __future__ import annotations

from datetime import UTC, datetime
from functools import partial
from typing import Any, cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.util import dt as dt_util

from .assets import asset_category
from .const import (
    CONF_CURRENCY,
    DOMAIN,
    ENTRY_TYPE_PORTFOLIO,
    PORTFOLIO_TIMEFRAMES,
    entry_type,
)
from .devices import find_wallet_device
from .portfolio_coordinator import PortfolioConfigEntry, PortfolioRuntime
from .portfolio_model import (
    DECIMALS,
    PortfolioData,
    change_24h,
    performance,
    position_totals,
    return_amount,
    share_percent,
    significant,
    time_key,
)

# The actions' timeframes, and /portfolio-history's.
TIMEFRAMES = {timeframe.lower(): timeframe for timeframe in PORTFOLIO_TIMEFRAMES}

_HISTORY_SCHEMA = vol.Schema({vol.Required("timeframe"): vol.In(list(TIMEFRAMES))})
_REWARDS_SCHEMA = vol.Schema(
    {vol.Optional("start"): cv.datetime, vol.Optional("end"): cv.datetime}
)


@callback
def async_register_portfolio_actions(hass: HomeAssistant) -> None:
    """Register the three actions, once."""
    for name, handler, schema in (
        ("get_portfolio", _get_portfolio, vol.Schema({})),
        ("get_portfolio_history", _get_portfolio_history, _HISTORY_SCHEMA),
        ("get_staking_rewards", _get_staking_rewards, _REWARDS_SCHEMA),
    ):
        # Newer releases type schemas with probatio; voluptuous works the
        # same at runtime on every release from the minimum on, and mypy
        # checks the newest.
        # Home Assistant judges the function inside the partial: the
        # handlers carry @callback themselves, so they run on the loop.
        hass.services.async_register(
            DOMAIN, name, partial(handler, hass),
            schema=schema,  # type: ignore[arg-type]
            supports_response=SupportsResponse.ONLY,
        )


def _entry(hass: HomeAssistant) -> PortfolioConfigEntry:
    """The loaded Portfolio; refused without one."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED and entry_type(entry) == ENTRY_TYPE_PORTFOLIO:
            return cast(PortfolioConfigEntry, entry)
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_portfolio")


def _data(runtime: PortfolioRuntime) -> PortfolioData:
    """The portfolio's figures while its sensors show them: an error before
    the first answer, after a confirmed outage and with a rejected key."""
    data = runtime.portfolio.data
    if data is None or not runtime.portfolio.data_available:
        raise HomeAssistantError(translation_domain=DOMAIN, translation_key="portfolio_unavailable")
    return data


@callback
def _get_portfolio(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    entry = _entry(hass)
    runtime = entry.runtime_data
    data = _data(runtime)
    waiting = data.waiting
    total = None if "total" in waiting else data.total
    positions = None if "positions" in waiting else data.positions
    totals = None if positions is None else position_totals(positions.values())
    history = runtime.history.data if runtime.history.data_available else None
    returns: dict[str, Any] = {}
    for key, timeframe in TIMEFRAMES.items():
        percent = (
            None if history is None or timeframe in history.failed
            else history.values.get(timeframe)
        )
        returns[key] = {"percent": percent, "amount": return_amount(total, percent)}
    wallets = [_wallet(hass, entry, data, asset_id, total) for asset_id in data.wallet_ids]
    # Largest first; one without a value last.
    wallets.sort(key=lambda wallet: (wallet["value"] is None, -(wallet["value"] or 0.0)))
    return {
        "currency": entry.data[CONF_CURRENCY],
        "total_value": total,
        "cash": None if "cash" in waiting else data.cash,
        "cash_plus": None if "cash_plus" in waiting else data.cash_plus,
        "invested": None if totals is None else totals.invested,
        "total_return": None if totals is None else totals.total_return,
        "total_return_percent": None if totals is None else totals.total_return_percent,
        "returns": returns,
        "wallets": wallets,
    }


def _wallet(
    hass: HomeAssistant,
    entry: PortfolioConfigEntry,
    data: PortfolioData,
    asset_id: str,
    total: float | None,
) -> dict[str, Any]:
    """One wallet, as its sensors show it -- whatever their state: the
    24-hour figures are those its Balance (total) was given, none while it
    is disabled; the price that of the round (WalletPrices), none after a
    quarter of an hour without one."""
    runtime = entry.runtime_data
    asset = data.assets[asset_id]
    holding = data.holdings[asset_id]
    price = None if runtime.prices is None else runtime.prices.price_of(asset_id)
    then = None if runtime.day_ago is None else runtime.day_ago.last.get(asset_id)
    day = change_24h(price, then, holding.balance)
    figures = performance(holding)
    earn = runtime.earn.data
    apr = None if earn is None else earn.apr.get(asset_id)
    rewards = (runtime.rewards.data or {}).get(asset_id)
    net = rewards.net if rewards is not None and rewards.count else None
    device = find_wallet_device(dr.async_get(hass), entry.entry_id, asset_id)
    return {
        "asset_id": asset_id,
        "symbol": asset["symbol"],
        "name": asset.get("name"),
        "category": asset_category(asset),
        "device_id": None if device is None else device.id,
        "units": round(holding.balance, DECIMALS),
        "staked_units": holding.staked,
        "value": None if holding.value is None else round(holding.value, DECIMALS),
        "price": None if price is None else significant(price),
        "invested_amount": figures.get("invested_amount"),
        "total_return": figures.get("total_return"),
        "total_return_percent": figures.get("total_return_percent"),
        "change_24h_pct": None if day is None else day[0],
        "return_24h": None if day is None else day[1],
        "portfolio_share_percent": share_percent(holding.value, total),
        "apr_percent": None if apr is None else round(apr * 100, DECIMALS),
        "rewards_net": net,
        "rewards_net_value": None if net is None or price is None else round(net * price, 2),
    }


@callback
def _get_portfolio_history(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    """The series the Portfolio card draws: empty while the history is
    unavailable."""
    entry = _entry(hass)
    runtime = entry.runtime_data
    _data(runtime)
    key = call.data["timeframe"]
    history = runtime.history
    series = (
        history.data.series.get(TIMEFRAMES[key], ())
        if history.data_available and history.data is not None
        else ()
    )
    return {
        "currency": entry.data[CONF_CURRENCY],
        "timeframe": key,
        "points": [
            {"time": datetime.fromtimestamp(time / 1000, UTC).isoformat(), "value": value}
            for time, value in series
        ],
    }


def _utc(value: datetime | None) -> datetime | None:
    """`value` in UTC; one without an offset is in Home Assistant's time
    zone."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_utc(value)


@callback
def _get_staking_rewards(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    """Every payout read so far, oldest first, from `start` on and before
    `end` -- whatever the portfolio's state: they come from the store. A
    payout whose time does not parse is left out under a filter. The
    symbol is that of a held asset's record, null for any other: no
    lookup."""
    entry = _entry(hass)
    runtime = entry.runtime_data
    start, end = _utc(call.data.get("start")), _utc(call.data.get("end"))
    if start is not None and end is not None and start > end:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="rewards_start_after_end"
        )
    records = runtime.portfolio.data.assets if runtime.portfolio.data is not None else {}
    found: list[tuple[tuple[int, datetime | str], dict[str, Any]]] = []
    for asset_id, totals in (runtime.rewards.data or {}).items():
        for payout in totals.payouts:
            when = time_key(payout.credited_at)
            if start is not None or end is not None:
                rank, moment = when
                if rank:
                    continue
                if (start is not None and cast(datetime, moment) < start) or (
                    end is not None and cast(datetime, moment) >= end
                ):
                    continue
            record = records.get(asset_id)
            found.append((when, {
                "asset_id": asset_id,
                "symbol": None if record is None else record["symbol"],
                "credited_at": payout.credited_at,
                "gross": payout.gross,
                "fee": payout.fee,
                "net": payout.net,
            }))
    found.sort(key=lambda item: item[0])
    # Before this run's first successful read, the last one of an earlier run.
    updated = runtime.rewards.last_update_success_time or runtime.operations.read_at
    return {
        "updated_at": None if updated is None else dt_util.as_utc(updated).isoformat(),
        "payouts": [payout for _, payout in found],
    }
