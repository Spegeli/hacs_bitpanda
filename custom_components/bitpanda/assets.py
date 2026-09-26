"""Asset records: categories, legacy symbol resolution, holding metadata, list labels.

Every endpoint except /assets and /currencies works on UUIDs. A symbol does
not uniquely name an asset (`XAU` is both a stock and a metal), so nothing
here ever keys by symbol. `pick_legacy` serves only the version 1 migration;
`AssetDirectory` names the holdings of a portfolio.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable

from .api import BitpandaApiClient, BitpandaApiError, BitpandaRateLimitError

_LOGGER = logging.getLogger(__name__)

# All the integration reads from a catalogue record. The rest of a full
# record -- trading flags -- would only cost memory.
CATALOGUE_FIELDS = ("id", "symbol", "name", "isin", "type", "group")

# The asset types the integration tells apart, each with the catalogue
# filters -- (type, group), group None for any -- that list it. Every filter
# was verified live on 2026-09-24. Together they cover 14,051 of 14,054
# catalogue assets -- the three left out are security/fiat_earn (Cash Plus),
# a cash equivalent. Stocks exist in two families, equity_security/
# equity_stock and security/stock, often the same company twice; both are
# genuine, priced listings, so a category can merge several filters.
ASSET_CATEGORY_FILTERS: dict[str, list[tuple[str, str | None]]] = {
    "crypto": [("cryptocoin", None)],
    "stock": [("equity_security", "equity_stock"), ("security", "stock")],
    "etf": [
        ("equity_security", "equity_etf"),
        ("equity_security", "equity_complex_etf"),
        ("security", "etf"),
    ],
    "etc": [("equity_security", "equity_complex_etc"), ("security", "etc")],
    "index": [("index", None)],
    "metal": [("commodity", "metal")],
}

# The category of an asset no filter above lists, such as Cash Plus.
CATEGORY_OTHER = "other"


def slim_asset(asset: dict) -> dict:
    """A catalogue record reduced to CATALOGUE_FIELDS."""
    return {key: asset[key] for key in CATALOGUE_FIELDS if key in asset}


def asset_category(asset: dict) -> str:
    """The first category of ASSET_CATEGORY_FILTERS with a filter the record
    matches (its type, and its group where the filter names one);
    CATEGORY_OTHER when no filter does."""
    for category, filters in ASSET_CATEGORY_FILTERS.items():
        for type_, group in filters:
            if asset.get("type") == type_ and (group is None or asset.get("group") == group):
                return category
    return CATEGORY_OTHER


class AssetDirectory:
    """Records of held assets, looked up by id.

    /portfolio names holdings by UUID only. Wallet devices need a name and a
    symbol, and only a record's group tells Cash Plus apart, so each held
    asset is looked up once with a keyless /assets?id= request and kept in
    `cache` -- a dict the caller keeps across reloads. A failed lookup is
    retried on the next refresh; an asset the catalogue does not know is
    asked for once per run.
    """

    def __init__(self, client: BitpandaApiClient, cache: dict[str, dict]) -> None:
        self._client = client
        self._cache = cache
        self._unknown: set[str] = set()

    def get(self, asset_id: str) -> dict | None:
        return self._cache.get(asset_id)

    async def async_resolve(self, asset_ids: Iterable[str]) -> None:
        for asset_id in asset_ids:
            if asset_id in self._cache or asset_id in self._unknown:
                continue
            try:
                found = await self._client.async_get_assets(asset_id=asset_id)
            except BitpandaRateLimitError:
                _LOGGER.debug("Rate limited looking up assets; retrying next refresh")
                return
            except BitpandaApiError as err:
                _LOGGER.debug("Could not look up asset %s: %s", asset_id, err)
                continue
            record = next((a for a in found if a.get("id") == asset_id), None)
            if record is None:
                self._unknown.add(asset_id)
                _LOGGER.warning(
                    "Held asset %s is not in the Bitpanda catalogue; it gets no "
                    "wallet sensor",
                    asset_id,
                )
                continue
            self._cache[asset_id] = slim_asset(record)


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

    Shared by `pick_legacy` (which wants exactly one survivor) and
    migration.py's own reason-building, which needs to tell "no survivor"
    apart from "more than one" so it can name the count in the reason it
    lists -- with the entity left in place -- in the migration notification,
    instead of collapsing both into the same message.
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
    # tolerance only (see _LEGACY_PREFIXES in migration.py).
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


def asset_label(asset: dict) -> str:
    """'Name / SYMBOL / ISIN', or 'Name / SYMBOL' when the asset has no ISIN."""
    parts = [asset.get("name") or asset["symbol"], asset["symbol"]]
    if asset.get("isin"):
        parts.append(asset["isin"])
    return " / ".join(parts)


def asset_label_map(assets: Iterable[dict]) -> dict[str, dict]:
    """`asset_label(asset)` -> asset, for one listing, with every label made
    unique first.

    The asset picker is a searchable `SelectSelector` with `custom_value=True`;
    the frontend shows an option's raw value back with no way to render its
    label instead, so the value must already be the label the user picked.
    Two or more assets that share a label all get " · <type>/<group>"
    appended -- the real shape of a stock listed under both catalogue
    families, same name, symbol and ISIN. If that still collides -- the same
    type and group too -- " · " plus the first 8 characters of the id is
    appended as well, so every asset ends up with exactly one, unique entry.
    """
    by_label: dict[str, list[dict]] = {}
    for asset in assets:
        by_label.setdefault(asset_label(asset), []).append(asset)

    result: dict[str, dict] = {}
    for label, group in by_label.items():
        if len(group) == 1:
            result[label] = group[0]
            continue
        by_suffixed: dict[str, list[dict]] = {}
        for asset in group:
            suffixed = f"{label} · {asset.get('type')}/{asset.get('group')}"
            by_suffixed.setdefault(suffixed, []).append(asset)
        for suffixed_label, subgroup in by_suffixed.items():
            if len(subgroup) == 1:
                result[suffixed_label] = subgroup[0]
                continue
            for asset in subgroup:
                result[f"{suffixed_label} · {asset['id'][:8]}"] = asset
    return result


def resolve_asset(
    value: str, label_map: dict[str, dict], catalogue: Iterable[dict]
) -> dict | None:
    """What the picker's raw submitted `value` names: a label in `label_map`,
    or -- typed or pasted -- the id of an asset in `catalogue`. None for
    anything else.
    """
    chosen = label_map.get(value)
    if chosen is not None:
        return chosen
    return next((asset for asset in catalogue if asset.get("id") == value), None)
