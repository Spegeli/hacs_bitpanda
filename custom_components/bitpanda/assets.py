"""Asset records: categories, legacy symbol resolution, holding metadata, list labels.

Every endpoint except /assets and /currencies works on UUIDs. A symbol does
not uniquely name an asset (`XAU` is both a stock and a metal), so nothing
here ever keys by symbol. `pick_legacy` serves only the version 1 migration;
`AssetDirectory` names the holdings of a portfolio.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable

from .api import BitpandaApiClient, BitpandaApiError

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
    `cache` -- a dict the caller keeps across reloads. A failed lookup --
    a rate limit, a timeout, a connection or server error -- ends the pass:
    the next lookup would most likely fail the same way, and with /assets
    hanging, each would hold the refresh (the first one runs inside setup)
    for the whole request timeout. The next refresh asks again, but for the
    assets whose lookup failed last, the one that failed longest ago first:
    an asset whose own lookup keeps failing never keeps the others waiting
    longer than that, and assets that keep failing take turns. An asset the
    catalogue does not know -- an empty answer, not a failure -- is asked
    for once per run, and the pass goes on.
    """

    def __init__(self, client: BitpandaApiClient, cache: dict[str, dict]) -> None:
        self._client = client
        self._cache = cache
        self._unknown: set[str] = set()
        # Asset id -> when its lookup last failed, as a running count of
        # failures: the order in which failed assets are asked for again.
        self._failed: dict[str, int] = {}
        self._failures = 0

    def get(self, asset_id: str) -> dict | None:
        return self._cache.get(asset_id)

    async def async_resolve(self, asset_ids: Iterable[str]) -> None:
        pending = [
            asset_id
            for asset_id in asset_ids
            if asset_id not in self._cache and asset_id not in self._unknown
        ]
        # Stable: the assets never failed keep the order given, ahead of the
        # rest.
        pending.sort(key=lambda asset_id: self._failed.get(asset_id, 0))
        for asset_id in pending:
            try:
                found = await self._client.async_get_assets(asset_id=asset_id)
            except BitpandaApiError as err:
                # The rate limit (BitpandaRateLimitError) included. The
                # message names a path and a cause, never request data.
                _LOGGER.debug(
                    "Could not look up asset %s: %s; retrying next refresh", asset_id, err
                )
                self._failures += 1
                self._failed[asset_id] = self._failures
                return
            self._failed.pop(asset_id, None)
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
    an entity left in place, and listed with the reason in the migration
    notification, beats one silently tracking the wrong asset.
    """
    survivors = legacy_candidates(candidates, prefix)
    return survivors[0] if len(survivors) == 1 else None


def asset_label(asset: dict) -> str:
    """'Name / SYMBOL / ISIN', or 'Name / SYMBOL' when the asset has no ISIN."""
    parts = [asset.get("name") or asset["symbol"], asset["symbol"]]
    if asset.get("isin"):
        parts.append(asset["isin"])
    return " / ".join(parts)


def _label_rungs(asset: dict, label: str) -> list[str]:
    """`asset`'s escalation ladder from `label`, most preferred first: the
    plain label, then with its type/group, then with the first 8 characters
    of its id, then with the whole id. A caller starting partway down this
    ladder just slices off the rungs its own local duplicates already rule
    out."""
    suffixed = f"{label} · {asset.get('type')}/{asset.get('group')}"
    asset_id = asset.get("id", "")
    return [label, suffixed, f"{suffixed} · {asset_id[:8]}", f"{suffixed} · {asset_id}"]


def _place_asset(result: dict[str, dict], asset: dict, rungs: list[str]) -> None:
    """Write `asset` into `result` at the first rung not already taken by a
    *different* asset. `rungs` only encodes what `asset`'s own raw-label
    duplicates require; this also guards against a rung colliding with an
    unrelated asset placed under a different raw label entirely, escalating
    past the last rung with a counter on the practically-unreachable chance
    that even the full id collides too. Never overwrites an existing entry.
    """
    for candidate in rungs:
        if candidate not in result:
            result[candidate] = asset
            return
    base = rungs[-1]
    counter = 2
    candidate = f"{base} · {counter}"
    while candidate in result:
        counter += 1
        candidate = f"{base} · {counter}"
    result[candidate] = asset


def asset_label_map(assets: Iterable[dict]) -> dict[str, dict]:
    """`asset_label(asset)` -> asset, for one listing, with exactly one
    globally-unique entry per input asset -- no asset is ever dropped or
    silently overwritten by another one's computed label.

    Two or more assets sharing a raw label skip it and start from
    " · <type>/<group>" appended instead -- the real shape of a stock listed
    under both catalogue families, same name, symbol and ISIN. Two or more
    of those sharing their type and group too skip that as well and start
    from " · " plus the first 8 characters of the id instead. Whatever rung
    an asset's own duplicates require it to start from, every candidate is
    then also checked against every *other* asset already placed -- not
    just the ones it shares a raw label with -- so a computed suffix that
    happens to equal an unrelated asset's plain or suffixed label still
    escalates further instead of colliding with it. A record missing
    `group` (never true for any catalogue entry filtered in today) renders
    as "type/None" in the suffix -- still unique, just not pretty.
    """
    by_label: dict[str, list[dict]] = {}
    for asset in assets:
        by_label.setdefault(asset_label(asset), []).append(asset)

    result: dict[str, dict] = {}
    for label, siblings in by_label.items():
        if len(siblings) == 1:
            _place_asset(result, siblings[0], _label_rungs(siblings[0], label))
            continue
        by_suffixed: dict[str, list[tuple[dict, list[str]]]] = {}
        for asset in siblings:
            rungs = _label_rungs(asset, label)
            by_suffixed.setdefault(rungs[1], []).append((asset, rungs))
        for subgroup in by_suffixed.values():
            skip = 1 if len(subgroup) == 1 else 2
            for asset, rungs in subgroup:
                _place_asset(result, asset, rungs[skip:])
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
