"""Labels, entity IDs, unique_ids and device identifiers.

Every entity ID is set explicitly, in English, from the asset's label, so it
does not depend on the language Home Assistant runs in. unique_ids are built
from UUIDs and never change.
"""
from __future__ import annotations

import re

from homeassistant.util import slugify

_ENTITY_ID_PREFIX = "sensor.bitpanda_"

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# /portfolio-history timeframe -> entity_id suffix of its return sensor.
RETURN_SUFFIXES: dict[str, str] = {
    "DAY": "day",
    "WEEK": "week",
    "MONTH": "month",
    "SIX_MONTH": "6_months",
    "YEAR": "year",
}

LEGACY_PORTFOLIO_OBJECT_ID = "bitpanda_wallets_portfolio_total"


def _squash(text: str) -> str:
    return "".join(text.split()).casefold()


def _uuid_after(prefix: str, text: str) -> str | None:
    """The UUID that `text` consists of after `prefix`, or None."""
    if not text.startswith(prefix):
        return None
    candidate = text[len(prefix):]
    return candidate if _UUID.fullmatch(candidate) else None


def asset_display_label(asset: dict) -> str:
    """ "Name (SYMBOL)", or just SYMBOL when the name only repeats it.

    Compared ignoring case and spaces, so "BCI 5" / BCI5 reads "BCI5".
    """
    symbol = asset["symbol"]
    name = (asset.get("name") or "").strip()
    if not name or _squash(name) == _squash(symbol):
        return symbol
    return f"{name} ({symbol})"


def asset_slug(asset: dict) -> str:
    return slugify(asset_display_label(asset))


def return_key(timeframe: str) -> str:
    """The Portfolio sensor key of one /portfolio-history timeframe."""
    return f"return_{timeframe.lower()}"


# The figures of the Portfolio device, by the key each of its sensors passes
# to portfolio_unique_id and portfolio_entity_id: three values, then one
# return per /portfolio-history timeframe.
PORTFOLIO_KEYS: tuple[str, ...] = (
    "total",
    "cash",
    "cash_plus",
    *(return_key(timeframe) for timeframe in RETURN_SUFFIXES),
)


# --- Portfolio device ---------------------------------------------------------


def portfolio_device_identifier(entry_id: str) -> str:
    return f"{entry_id}_portfolio"


def portfolio_unique_id(entry_id: str, key: str) -> str:
    return f"{entry_id}_portfolio_{key}"


def portfolio_entity_id(key: str) -> str:
    for timeframe, suffix in RETURN_SUFFIXES.items():
        if key == return_key(timeframe):
            return f"{_ENTITY_ID_PREFIX}portfolio_return_{suffix}"
    return f"{_ENTITY_ID_PREFIX}portfolio_{key}"


# --- Wallet devices -------------------------------------------------------------


def wallet_device_identifier(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_wallet_{asset_id}"


def wallet_unique_id(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_wallet_{asset_id}"


def staking_unique_id(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_staking_{asset_id}"


def total_unique_id(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_total_{asset_id}"


def wallet_entity_id(asset: dict) -> str:
    return f"{_ENTITY_ID_PREFIX}{asset_slug(asset)}_wallet"


def staking_entity_id(asset: dict) -> str:
    return f"{_ENTITY_ID_PREFIX}{asset_slug(asset)}_wallet_staking"


def total_entity_id(asset: dict) -> str:
    return f"{_ENTITY_ID_PREFIX}{asset_slug(asset)}_wallet_total"


def managed_asset_id(entry_id: str, unique_id: str) -> str | None:
    """The asset a wallet, staking or total unique_id of this entry names.

    None for anything else -- including a legacy wallet the migration could
    not resolve, whose unique_id still ends in a legacy id such as
    "cryptocoin_BTC" rather than a UUID. The lifecycle manager only ever
    removes what this returns an asset for.
    """
    for kind in ("wallet", "staking", "total"):
        asset_id = _uuid_after(f"{entry_id}_{kind}_", unique_id)
        if asset_id is not None:
            return asset_id
    return None


def wallet_device_asset_id(entry_id: str, identifier: str) -> str | None:
    """The asset a wallet device identifier of this entry names, or None."""
    return _uuid_after(f"{entry_id}_wallet_", identifier)


# --- Price Tracker devices ------------------------------------------------------


def price_device_identifier(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_price_{asset_id}"


def price_unique_id(entry_id: str, asset_id: str, currency: str) -> str:
    return f"{entry_id}_{asset_id}_price_{currency}"


def price_entity_id(asset: dict, currency: str) -> str:
    return f"{_ENTITY_ID_PREFIX}{asset_slug(asset)}_{currency.lower()}"


def price_key(entry_id: str, unique_id: str) -> tuple[str, str] | None:
    """(asset id, currency) of a price unique_id of this entry, or None."""
    head, sep, currency = unique_id.rpartition("_price_")
    asset_id = _uuid_after(f"{entry_id}_", head) if sep and currency else None
    return None if asset_id is None else (asset_id, currency)


def price_device_asset_id(entry_id: str, identifier: str) -> str | None:
    """The asset a price device identifier of this entry names, or None."""
    return _uuid_after(f"{entry_id}_price_", identifier)


# --- Legacy (version 1) default entity IDs ---------------------------------------


def legacy_price_object_id(symbol: str, currency: str) -> str:
    """Device "Bitpanda Price Tracker" + entity name "BTC/EUR"."""
    return slugify(f"Bitpanda Price Tracker {symbol}/{currency}")


def legacy_wallet_object_id(symbol: str) -> str:
    """Device "Bitpanda Wallets" + entity name "VSN Wallet"."""
    return slugify(f"Bitpanda Wallets {symbol} Wallet")


def is_default_entity_id(entity_id: str, object_id: str) -> bool:
    """Whether `entity_id` is still the default Home Assistant gave `object_id`.

    Home Assistant appends "_2", "_3", ... when an ID is taken, so a numeric
    suffix still counts as the default. Anything else is the user's own ID
    and is never renamed.
    """
    return re.fullmatch(rf"sensor\.{re.escape(object_id)}(_\d+)?", entity_id) is not None
