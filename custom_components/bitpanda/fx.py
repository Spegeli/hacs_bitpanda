"""Currency rate derivation.

GET /tickers/{assetId} returns EUR and ignores every currency parameter, so a
non-EUR price sensor has to convert. The rate comes from Bitpanda itself: the
same fiat holding, fetched once per currency, converted server-side.

Measured against ECB reference rates on 2026-09-24, every one of the eleven
non-EUR currencies landed within 0.57 % from a balance of 0.01 EUR.
"""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


def fiat_entry(entries: list[dict]) -> dict | None:
    """Return the first fiat entry in a portfolio response.

    Fiat entries carry `currency_id` and no `asset_id`. There is no type field
    to branch on.
    """
    for entry in entries:
        if not entry.get("asset_id"):
            return entry
    return None


def derive_rate(
    eur_entries: list[dict], target_entries: list[dict]
) -> float | None:
    """Return units of the target currency per EUR, or None.

    Uses `available_balance`, never `balance`: both are converted, but
    `balance` is rounded to two decimals, which destroys the ratio for small
    holdings. The `currency_id` label on both is left at the source currency
    by the API and must not be trusted.
    """
    base = fiat_entry(eur_entries)
    target = fiat_entry(target_entries)
    if base is None or target is None:
        return None

    try:
        base_value = float(base["available_balance"]["value"])
        target_value = float(target["available_balance"]["value"])
    except (KeyError, TypeError, ValueError):
        _LOGGER.debug("Could not read available_balance for rate derivation")
        return None

    if base_value == 0:
        return None

    return target_value / base_value
