"""Symbol to asset-id resolution for the Bitpanda Public API.

Every endpoint except /assets and /currencies works on UUIDs, and the catalog
is over 14000 entries, so it is never enumerated. Symbols are resolved one at
a time and cached in the config entry.
"""
from __future__ import annotations

import logging

from .api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)

_LOGGER = logging.getLogger(__name__)

# Keyed by `group`, the more specific of the API's two classification fields.
_GROUP_CATEGORY = {
    "coin": "crypto",
    "token": "crypto",
    "leveraged_token": "crypto",
    "security_token": "crypto",
    "metal": "metal",
    "index": "index",
    "stock": "stock",
    "equity_stock": "stock",
    "etf": "etf",
    "equity_etf": "etf",
    "equity_complex_etf": "etf",
    "etc": "commodity",
    "equity_complex_etc": "commodity",
    "fiat_earn": "cash_plus",
}


def category_of(asset: dict) -> str:
    """Return the UI category for an asset.

    Unknown groups fall through to "other" rather than raising: the catalog
    gains entries, and an unseen group must not break setup.
    """
    return _GROUP_CATEGORY.get(asset.get("group", ""), "other")


class AssetResolver:
    """Resolves symbols to asset records, caching every hit."""

    def __init__(
        self, client: BitpandaApiClient | None, cache: dict[str, dict] | None = None
    ) -> None:
        self._client = client
        self._by_symbol: dict[str, dict] = dict(cache or {})
        self._by_id: dict[str, dict] = {
            a["id"]: a for a in self._by_symbol.values() if a.get("id")
        }

    async def async_resolve(self, symbol: str) -> dict | None:
        """Return the asset record for a symbol, or None if it does not exist."""
        if symbol in self._by_symbol:
            return self._by_symbol[symbol]
        if self._client is None:
            return None
        try:
            found = await self._client.async_get_assets(symbol=symbol)
        except (BitpandaAuthError, BitpandaRateLimitError):
            # Never swallow these. "Your key is invalid" and "you are being
            # rate limited" are not the same condition as "no such symbol",
            # and the caller has to be able to tell them apart — the config
            # flow shows a different error for each.
            raise
        except BitpandaApiError:
            _LOGGER.warning("Could not resolve symbol %s", symbol)
            return None
        if not found:
            return None
        asset = found[0]
        self._by_symbol[symbol] = asset
        if asset.get("id"):
            self._by_id[asset["id"]] = asset
        return asset

    def get_cached(self, asset_id: str) -> dict | None:
        """Return a cached asset by its id, without any network access."""
        return self._by_id.get(asset_id)

    def as_dict(self) -> dict[str, dict]:
        """Return the cache for persisting into the config entry."""
        return dict(self._by_symbol)
