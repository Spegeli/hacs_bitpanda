"""Symbol to asset-id resolution for the Bitpanda Public API.

Every endpoint except /assets and /currencies works on UUIDs. `AssetResolver`
resolves one symbol at a time -- migration is its only caller now -- and
caches every hit in the config entry by asset id, not by symbol, because a
symbol does not uniquely name an asset (`XAU` is both a stock and a metal;
see `pick_legacy` below). The options flow separately pages through whole
catalogue categories to build its pickers (`config_flow.py`'s
`ASSET_CATEGORY_FILTERS` and `BitpandaApiClient.async_list_assets`) -- a
different, unrelated enumeration that this module has no part in.
"""
from __future__ import annotations

from .api import BitpandaApiClient

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


# What the legacy (v1, api.bitpanda.com) API could ever track. It only ever
# traded crypto, indices and metals -- a stock or an ETF was never reachable
# through it, so a v1 identifier can never have meant one, no matter what
# /assets?symbol= returns today.
LEGACY_TYPES = ("cryptocoin", "index")


def is_legacy_supported(asset: dict) -> bool:
    """What the legacy API could track: crypto, indices and metals — never securities."""
    return asset.get("type") in LEGACY_TYPES or asset.get("group") == "metal"


def legacy_candidates(candidates: list[dict], prefix: str | None) -> list[dict]:
    """Candidates narrowed to what a v1 identifier bearing `prefix` could mean.

    Shared by `pick_legacy` (which wants exactly one survivor) and the
    migration's own logging (`__init__.py`), which needs to tell "no
    survivor" apart from "more than one" so it can name the count in its
    warning instead of collapsing both into the same message.
    """
    if prefix == "fiat_":
        # A currency is not an /assets record at all -- fiat balances live on
        # as the portfolio sensor's `cash` attribute, never as a resolved
        # asset -- so there is nothing here to narrow down to.
        return []

    survivors = [a for a in candidates if is_legacy_supported(a)]

    if prefix == "cryptocoin_":
        return [a for a in survivors if a.get("type") == "cryptocoin"]
    if prefix in ("commodity_metal_", "metal_"):
        return [a for a in survivors if a.get("group") == "metal"]
    # "index_index_" is what the legacy flow stored; the other two are
    # tolerance only (see _LEGACY_PREFIXES in __init__.py).
    if prefix in ("index_index_", "index_", "index_wallet_"):
        return [a for a in survivors if a.get("type") == "index"]
    # prefix is None for a bare symbol (what v1 price trackers stored) --
    # only the legacy-supported-type filter above applies.
    return survivors


def pick_legacy(candidates: list[dict], prefix: str | None) -> dict | None:
    """Choose the asset a version 1 identifier meant, or None if that is unclear.

    Filters to legacy-supported types first — the legacy API never offered a
    stock or an ETF, so a stock can never be what a v1 entry meant. A wallet's
    category prefix then narrows further. More than one survivor returns None:
    dropping an entry with a warning beats silently tracking the wrong asset.
    """
    survivors = legacy_candidates(candidates, prefix)
    return survivors[0] if len(survivors) == 1 else None


class AssetResolver:
    """Resolves symbols to asset records, caching every hit by asset id."""

    def __init__(
        self, client: BitpandaApiClient | None, cache: dict[str, dict] | None = None
    ) -> None:
        self._client = client
        # Re-keyed from each record's own id rather than trusting the given
        # dict's outer keys: a v2 entry saved by an earlier dev build
        # persisted `asset_cache` keyed by symbol, and trusting that would
        # keep every one of its records permanently unreachable by id --
        # silently dropping every tracked sensor at setup instead of healing
        # (task-23-review.md, finding 6). A cache already keyed by id
        # re-keys to the same thing, so this is free for the normal case.
        self._by_id: dict[str, dict] = {
            a["id"]: a for a in (cache or {}).values() if a.get("id")
        }

    def remember(self, asset: dict) -> None:
        """Cache an asset record by its id. A record with no id is ignored."""
        if asset.get("id"):
            self._by_id[asset["id"]] = asset

    async def async_candidates(self, symbol: str) -> list[dict]:
        """Return every asset the API has under `symbol`. Migration only.

        Always asks the API: nothing here can tell whether a previous call
        already saw every asset that carries this symbol, so there is no
        cache to short-circuit on, unlike a single-answer lookup. The caller
        (migration's `pick_legacy`) decides which candidate, if any, is the
        right one, and `remember`s only that one -- not every candidate this
        returns, so an unrelated candidate sharing the symbol is never
        persisted into the config entry alongside the one actually chosen.

        Never queries an empty symbol: `BitpandaApiClient.async_get_assets`
        drops the `symbol` filter entirely when it is falsy, which would page
        through the whole ~14,000-asset catalogue instead of finding nothing
        (task-23-review.md, finding 10). `legacy_symbol` returns "" for a
        bare-prefix v1 id like `"cryptocoin_"`; migration never builds one,
        but this stays correct even if that changes.

        Every API error propagates, not only auth and rate-limit errors. An
        empty 200 is the only answer that means "no such symbol": the
        migration drops an asset for good on that, while a timeout, a 5xx or
        a reset connection says nothing about the symbol and must abort the
        migration instead, which retries on the next start.
        """
        if not symbol or self._client is None:
            return []
        return await self._client.async_get_assets(symbol=symbol)

    def get_cached(self, asset_id: str) -> dict | None:
        """Return a cached asset by its id, without any network access."""
        return self._by_id.get(asset_id)

    def as_dict(self) -> dict[str, dict]:
        """Return the cache for persisting into the config entry, keyed by id."""
        return dict(self._by_id)


def asset_label(asset: dict) -> str:
    """'Name / SYMBOL / ISIN', or 'Name / SYMBOL' when the asset has no ISIN."""
    parts = [asset.get("name") or asset["symbol"], asset["symbol"]]
    if asset.get("isin"):
        parts.append(asset["isin"])
    return " / ".join(parts)
