"""Labels, device names, entity IDs, unique_ids and device identifiers.

Device names are English: "Vision (VSN) Wallet", "Bitcoin (BTC) Price
Tracker". Every entity ID is set explicitly: `sensor.bitpanda_` + the slug of
its device's name + the sensor's own ending -- "Portfolio" + `_total`,
"Vision (VSN) Wallet" + `_available` -- so it does not depend on the language
Home Assistant runs in. unique_ids are built from UUIDs and never change.
"""
from __future__ import annotations

import re
from typing import Any

from homeassistant.util import slugify

from .assets import asset_isin

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


def asset_display_label(asset: dict[str, Any]) -> str:
    """ "Name (SYMBOL)", or just SYMBOL when the name only repeats it; a
    stock, ETF or ETC adds its ISIN (assets.asset_isin): "Name (SYMBOL /
    ISIN)", or "SYMBOL (ISIN)".

    Compared ignoring case and spaces, so "BCI 5" / BCI5 reads "BCI5". Device
    names and entity IDs are built from it, and so are the texts and log
    lines that name a known asset.
    """
    symbol = asset["symbol"]
    name = (asset.get("name") or "").strip()
    isin = asset_isin(asset)
    if name and _squash(name) != _squash(symbol):
        return f"{name} ({symbol})" if isin is None else f"{name} ({symbol} / {isin})"
    return symbol if isin is None else f"{symbol} ({isin})"


def _entity_id(device_name: str, ending: str) -> str:
    """The entity ID of the sensor with `ending` on the device `device_name`."""
    return f"{_ENTITY_ID_PREFIX}{slugify(device_name)}_{ending}"


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


PORTFOLIO_DEVICE_NAME = "Portfolio"


def portfolio_device_identifier(entry_id: str) -> str:
    return f"{entry_id}_portfolio"


def portfolio_unique_id(entry_id: str, key: str) -> str:
    return f"{entry_id}_portfolio_{key}"


def portfolio_entity_id(key: str) -> str:
    for timeframe, suffix in RETURN_SUFFIXES.items():
        if key == return_key(timeframe):
            return _entity_id(PORTFOLIO_DEVICE_NAME, f"return_{suffix}")
    return _entity_id(PORTFOLIO_DEVICE_NAME, key)


# --- Wallet devices -------------------------------------------------------------


def wallet_device_name(asset: dict[str, Any]) -> str:
    return f"{asset_display_label(asset)} Wallet"


def wallet_device_identifier(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_wallet_{asset_id}"


def wallet_unique_id(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_wallet_{asset_id}"


def staking_unique_id(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_staking_{asset_id}"


def total_unique_id(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_total_{asset_id}"


def wallet_entity_id(asset: dict[str, Any]) -> str:
    """Ends in the sensor's name, "Balance (available)", like its siblings'
    IDs: `…_wallet` alone would read as the whole wallet."""
    return _entity_id(wallet_device_name(asset), "available")


def staking_entity_id(asset: dict[str, Any]) -> str:
    return _entity_id(wallet_device_name(asset), "staking")


def total_entity_id(asset: dict[str, Any]) -> str:
    return _entity_id(wallet_device_name(asset), "total")


def managed_asset_key(entry_id: str, unique_id: str) -> tuple[str, str] | None:
    """(kind, asset id) of a wallet, staking or total unique_id of this
    entry, kind being "wallet", "staking" or "total".

    None for anything else -- including a legacy wallet the migration could
    not resolve, whose unique_id still ends in a legacy id such as
    "cryptocoin_BTC" rather than a UUID. The lifecycle manager only ever
    removes what this names an asset for.
    """
    for kind in ("wallet", "staking", "total"):
        asset_id = _uuid_after(f"{entry_id}_{kind}_", unique_id)
        if asset_id is not None:
            return kind, asset_id
    return None


def managed_asset_id(entry_id: str, unique_id: str) -> str | None:
    """The asset a wallet, staking or total unique_id of this entry names,
    or None (see managed_asset_key)."""
    key = managed_asset_key(entry_id, unique_id)
    return None if key is None else key[1]


def wallet_device_asset_id(entry_id: str, identifier: str) -> str | None:
    """The asset a wallet device identifier of this entry names, or None."""
    return _uuid_after(f"{entry_id}_wallet_", identifier)


# --- Price Tracker devices ------------------------------------------------------


def price_device_name(asset: dict[str, Any]) -> str:
    """Says what the device is, as "… Wallet" does: Home Assistant lists an
    entity under its device's name, and the price sensors are named by
    their currency alone -- "Bitcoin (BTC) Price Tracker EUR"."""
    return f"{asset_display_label(asset)} Price Tracker"


def price_device_identifier(entry_id: str, asset_id: str) -> str:
    return f"{entry_id}_price_{asset_id}"


def price_unique_id(entry_id: str, asset_id: str, currency: str) -> str:
    return f"{entry_id}_{asset_id}_price_{currency}"


def price_entity_id(asset: dict[str, Any], currency: str) -> str:
    return _entity_id(price_device_name(asset), currency.lower())


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
