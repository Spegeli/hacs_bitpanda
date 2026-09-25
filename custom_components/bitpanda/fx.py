"""Currency rate derivation.

GET /tickers/{assetId} returns EUR and ignores every currency parameter, so a
non-EUR price sensor has to convert. The rate comes from Bitpanda itself: the
same position of the user's own portfolio, fetched once valued in EUR and once
in the target currency, converted server-side.

Measured against ECB reference rates on 2026-09-24, every one of the eleven
non-EUR currencies landed within 0.57 % from a fiat balance of 0.01 EUR.
"""
from __future__ import annotations

import logging
import math

from .const import MIN_PORTFOLIO_DERIVED_VALUE

_LOGGER = logging.getLogger(__name__)


def _positive(container: object) -> float | None:
    """The `value` of an API amount object as a finite, positive float.

    float() accepts "nan", "inf" and "-inf" without raising, and a zero or
    negative amount cannot anchor a ratio either: a zero target would give a
    rate of 0.0, which turns every converted price into 0.
    """
    if not isinstance(container, dict):
        return None
    try:
        value = float(container["value"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def _fiat_amounts(entries: list[dict]) -> dict[str, float]:
    """`available_balance` of every usable fiat entry, keyed by currency_id.

    Fiat entries carry `currency_id` and no `asset_id`. Their `currency_id`
    stays at the wallet's own currency even when the values are converted,
    which makes it a stable key for finding the same wallet in both
    responses. `available_balance`, never `balance`: both are converted, but
    `balance` is rounded to two decimals, which destroys the ratio for small
    holdings.
    """
    out: dict[str, float] = {}
    for entry in entries:
        currency_id = entry.get("currency_id")
        if entry.get("asset_id") or not currency_id:
            continue
        amount = _positive(entry.get("available_balance"))
        if amount is not None:
            out[currency_id] = amount
    return out


def _asset_values(entries: list[dict]) -> dict[str, float]:
    """`currency_balance` of every usable asset entry, keyed by asset_id."""
    out: dict[str, float] = {}
    for entry in entries:
        asset_id = entry.get("asset_id")
        if not asset_id:
            continue
        value = _positive(entry.get("currency_balance"))
        if value is not None:
            out[asset_id] = value
    return out


def _largest_pair(
    base: dict[str, float], target: dict[str, float]
) -> tuple[float, float] | None:
    """The (base, target) values of the key present in both with the largest
    base value -- the one whose rounding weighs least -- or None."""
    shared = [key for key in base if key in target]
    if not shared:
        return None
    key = max(shared, key=lambda k: base[k])
    return base[key], target[key]


def derive_rate(
    eur_entries: list[dict], target_entries: list[dict]
) -> float | None:
    """Return units of the target currency per EUR, or None.

    First choice is a fiat wallet present in both responses, paired by its
    `currency_id` -- never by position, which pairs different wallets as
    soon as the two responses list several in a different order. Without a
    usable fiat pair (no cash at all, a zero balance, cash parked in Cash
    Plus) the ratio of the largest holding's `currency_balance` in both
    responses serves instead, at no extra request -- but only a holding worth
    at least MIN_PORTFOLIO_DERIVED_VALUE in EUR, because those values are
    rounded to cents and a small one yields a rate that is plainly wrong.
    Without either there is no rate: unheld prices then show no value, which
    beats a wrong one.
    """
    pair = _largest_pair(_fiat_amounts(eur_entries), _fiat_amounts(target_entries))
    if pair is None:
        large_enough = {
            asset_id: value
            for asset_id, value in _asset_values(eur_entries).items()
            if value >= MIN_PORTFOLIO_DERIVED_VALUE
        }
        pair = _largest_pair(large_enough, _asset_values(target_entries))
    if pair is None:
        _LOGGER.debug("No cash or holding to derive a currency rate from")
        return None
    base_value, target_value = pair
    return target_value / base_value
