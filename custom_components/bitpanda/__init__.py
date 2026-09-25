"""The Bitpanda integration."""
from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from .assets import AssetResolver, legacy_candidates, pick_legacy
from .const import (
    CONF_API_KEY,
    CONF_ASSET_CACHE,
    CONF_CURRENCY,
    CONF_CURRENCY_ID,
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DOMAIN,
    EUR_CURRENCY_ID,
)
from .coordinator import (
    EarnCoordinator,
    HistoryCoordinator,
    PortfolioCoordinator,
    PriceCoordinator,
    RewardsCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# The v1 options flow built wallet ids from the legacy /asset-wallets nesting:
# "{category}_{symbol}" for a flat category, "{category}_{sub}_{symbol}" for a
# nested one. Crypto was flat, metals sat under commodity -> metal and indices
# under index -> index, and fiat came from a separate listing -- so the ids it
# produced are "cryptocoin_BTC", "commodity_metal_XAU", "index_index_BCI5" and
# "fiat_EUR". "index_wallet_", "index_" and "metal_" were never produced; they
# stay as tolerance for hand-edited entries.
#
# Order matters: this is checked longest/most-specific first, or a shorter
# prefix that is itself a prefix of a longer one ("index_" / "index_index_")
# would strip first and leave a symbol that does not exist ("index_BCI5").
_LEGACY_PREFIXES = (
    "commodity_metal_",
    "index_index_",
    "index_wallet_",
    "cryptocoin_",
    "fiat_",
    "index_",
    "metal_",
)


def legacy_symbol(wallet_id: str) -> str:
    """Extract the asset symbol from a version 1 wallet id.

    A wallet id with no recognised prefix (already a bare symbol, or an
    unrecognised category) is returned unchanged. Resolution then either
    succeeds outright (a bare symbol) or legitimately fails and gets dropped
    with a warning (an unrecognised category) -- both are safer than
    guessing at a split.
    """
    for prefix in _LEGACY_PREFIXES:
        if wallet_id.startswith(prefix):
            return wallet_id[len(prefix):]
    return wallet_id


def legacy_prefix(wallet_id: str) -> str | None:
    """Return the recognised v1 category prefix of a wallet id, or None.

    Mirrors `legacy_symbol`'s own prefix search (same `_LEGACY_PREFIXES`,
    longest/most-specific first) but returns the prefix itself instead of
    stripping it -- `pick_legacy` (assets.py) needs to know which category a
    wallet id claimed, not just its bare symbol, to tell a metal wallet from
    a coin wallet that happens to share a symbol.
    """
    for prefix in _LEGACY_PREFIXES:
        if wallet_id.startswith(prefix):
            return prefix
    return None


def v2_unique_id(
    unique_id: str,
    entry_id: str,
    price_map: dict[str, str],
    wallet_map: dict[str, str],
) -> str | None:
    """Map a version 1 entity unique_id to its version 2 form.

    Returns None when the entity needs no change (the portfolio sensor), when
    it belongs to another config entry, or when its asset did not resolve.

    The wallet check runs before the price check -- a wallet unique_id is
    `f"{entry_id}_wallet_{wallet_id}"` with the whole prefixed v1 wallet id
    embedded (`eid_wallet_index_index_BCI5`, `eid_wallet_commodity_metal_XAU`),
    which `wallet_map` is keyed by -- but a wallet-prefix match is not proof
    either: a price sensor's own asset symbol could itself start with
    "wallet_" (`eid_wallet_XYZ_price_EUR`), so a miss in `wallet_map` falls
    through to the price pattern below instead of returning None outright.
    The reverse direction cannot be fooled the same way: a wallet unique_id
    never contains the literal substring "_price_", so nothing here is ever
    misparsed as a wallet by the price check.
    """
    wallet_prefix = f"{entry_id}_wallet_"
    if unique_id.startswith(wallet_prefix):
        raw_wallet_id = unique_id[len(wallet_prefix):]
        new_id = wallet_map.get(raw_wallet_id)
        if new_id is not None:
            return f"{wallet_prefix}{new_id}"
        # Fall through rather than returning None: see the docstring above.

    # rpartition, not split: the symbol half (the head) can itself contain
    # underscores ("SOME_TOKEN"), and only the last "_price_" is the real
    # separator.
    head, sep, currency = unique_id.rpartition("_price_")
    entry_prefix = f"{entry_id}_"
    if sep and head.startswith(entry_prefix):
        symbol = head[len(entry_prefix):]
        new_id = price_map.get(symbol)
        if new_id is not None:
            return f"{entry_id}_{new_id}_price_{currency}"

    return None


async def _migrate_entity_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    price_map: dict[str, str],
    wallet_map: dict[str, str],
) -> None:
    """Rewrite this entry's entity registry unique_ids from v1 to v2 form.

    Only unique_id changes; entity_id is untouched by
    `async_migrate_entries`/`async_update_entity`. That is what keeps
    recorder history, dashboard cards and automations pointed at the same
    entity across the upgrade instead of Home Assistant creating an orphaned
    duplicate (see task-18-fix1-brief.md).
    """
    ent_reg = er.async_get(hass)

    @callback
    def _entry_callback(reg_entry: er.RegistryEntry) -> dict[str, str] | None:
        new_unique_id = v2_unique_id(
            reg_entry.unique_id, entry.entry_id, price_map, wallet_map
        )
        if new_unique_id is None:
            return None
        colliding_entity_id = ent_reg.async_get_entity_id(
            reg_entry.domain, DOMAIN, new_unique_id
        )
        if colliding_entity_id is not None:
            # Not only a "second migration" concern: er.async_migrate_entries
            # applies each entity's update synchronously inside its own loop,
            # so if two distinct v1 identifiers resolve to the same UUID, the
            # second entity's collision check sees the first entity's
            # just-migrated unique_id, on a single, first-ever run. This was
            # already possible under the old first-match resolver too --
            # task 23's prefix narrowing does not introduce the collision,
            # though it does add a concrete instance: "commodity_metal_XAU"
            # and "metal_XAU" both resolve to gold. Log entity_ids only,
            # never entry.data, and move on rather than letting
            # async_update_entity's ValueError crash migration for this one
            # odd installation.
            _LOGGER.warning(
                "Skipping unique_id migration for %s: %s already uses the "
                "target unique_id",
                reg_entry.entity_id,
                colliding_entity_id,
            )
            return None
        return {"new_unique_id": new_unique_id}

    await er.async_migrate_entries(hass, entry.entry_id, _entry_callback)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry from version 1 to version 2.

    Version 1 stored asset symbols and "{category}_{symbol}" wallet ids. The
    public API works on UUIDs, so every stored identifier is resolved once
    and replaced.

    This runs once against a real installation's only copy of its
    configuration, so it must never leave an entry partially rewritten.
    A symbol the API answers with an empty result (delisted, renamed) is
    expected, and that entry is dropped with a warning. Any API error means
    something else: an auth or rate-limit error, a timeout, a 5xx or a reset
    connection says nothing about whether a particular symbol still exists,
    and dropping on it would be permanent. The whole attempt is aborted
    instead, with the entry untouched -- Home Assistant re-checks the
    version and retries migration on every subsequent startup, so nothing
    is lost by waiting.

    An entry from a newer release (version above 2) is refused: this code
    cannot know its format, and Home Assistant leaves it unloaded.
    """
    if entry.version > 2:
        _LOGGER.error(
            "The Bitpanda config entry was written by a newer release of this "
            "integration (version %s) and cannot be loaded by this one",
            entry.version,
        )
        return False
    if entry.version == 2:
        return True

    _LOGGER.info("Migrating Bitpanda config entry to version 2")

    client = BitpandaApiClient(
        entry.data[CONF_API_KEY], async_get_clientsession(hass)
    )
    resolver = AssetResolver(client, {})

    # Memoised across both _resolve_all calls below (tracked_assets, then
    # tracked_wallets), keyed by the bare symbol -- not by the raw v1 value,
    # which still differs between a price tracker and a wallet even when they
    # name the same asset. A symbol tracked as both costs one request instead
    # of two (task-23-review.md, finding 9).
    candidates_by_symbol: dict[str, list[dict]] = {}

    async def _candidates_for(sym: str) -> list[dict]:
        if sym not in candidates_by_symbol:
            candidates_by_symbol[sym] = await resolver.async_candidates(sym)
        return candidates_by_symbol[sym]

    async def _resolve_all(values: list[str], strip_prefix: bool) -> dict[str, str]:
        """Resolve each raw version-1 value to its asset UUID.

        Keyed by the RAW value (the bare symbol for tracked_assets, the whole
        prefixed wallet id for tracked_wallets) rather than the stripped
        symbol, because that raw value is exactly what a version-1 entity's
        unique_id embeds and what the registry migration below looks up.
        Insertion order is preserved, which is what lets the options lists
        below be rebuilt with `dict.fromkeys` instead of a second pass.

        A symbol does not uniquely name an asset -- `XAU` is both the
        GoldMoney stock and the Gold metal, in an API order that is not
        stable -- so every candidate is fetched and `pick_legacy` chooses the
        one a legacy (crypto/index/metal-only) identifier could have meant,
        using the wallet id's own category prefix to narrow further. See
        assets.py. Only the chosen asset is `remember`ed into the resolver's
        cache -- not every candidate `_candidates_for` returned -- so an
        unrelated candidate sharing the symbol (GoldMoney, say, beside Gold)
        never rides along into the persisted `asset_cache`.
        """
        out: dict[str, str] = {}
        for value in values:
            prefix = legacy_prefix(value) if strip_prefix else None
            if prefix == "fiat_":
                # A currency is not an /assets record at all -- pick_legacy
                # always returns None for it -- so asking the API is a
                # wasted request and a needless rate-limit exposure for a
                # run that aborts on 429 (task-23-review.md, finding 9).
                _LOGGER.warning(
                    "Dropping %s during migration: a fiat wallet has no "
                    "asset to resolve to",
                    value,
                )
                continue
            sym = legacy_symbol(value) if strip_prefix else value
            candidates = await _candidates_for(sym)
            asset = pick_legacy(candidates, prefix)
            if asset is not None:
                resolver.remember(asset)
                out[value] = asset["id"]
                continue
            survivors = legacy_candidates(candidates, prefix)
            if len(survivors) > 1:
                # Ambiguous, not absent: naming the count (never any asset
                # detail beyond that) is enough to tell this apart from a
                # plain "no longer exists" drop in the log.
                _LOGGER.warning(
                    "Dropping %s during migration: symbol %s matches %s "
                    "possible assets and which one this identifier meant is "
                    "ambiguous",
                    value,
                    sym,
                    len(survivors),
                )
            else:
                _LOGGER.warning(
                    "Dropping %s during migration: symbol %s no longer resolves",
                    value,
                    sym,
                )
        return out

    options = dict(entry.options)
    try:
        currencies = await client.async_get_currencies()
        symbol = entry.data.get(CONF_CURRENCY, "EUR")
        currency_id = next(
            (c["id"] for c in currencies if c["symbol"] == symbol), EUR_CURRENCY_ID
        )
        price_map = await _resolve_all(
            options.get(CONF_TRACKED_ASSETS, []), strip_prefix=False
        )
        wallet_map = await _resolve_all(
            options.get(CONF_TRACKED_WALLETS, []), strip_prefix=True
        )
    except BitpandaAuthError:
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: the API key was "
            "rejected. Nothing has been changed; migration will be retried "
            "on the next restart once a valid key is in place."
        )
        return False
    except BitpandaRateLimitError:
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: rate limited by the "
            "Bitpanda API. Nothing has been changed; migration will be "
            "retried on the next restart."
        )
        return False
    except BitpandaApiError:
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: could not reach the "
            "Bitpanda API. Nothing has been changed; migration will be "
            "retried on the next restart."
        )
        return False

    # Registry before entry, deliberately. If the registry step below raised,
    # an entry already bumped to version 2 would never see migration run
    # again, orphaning every entity that had not been rewritten yet. Doing it
    # first means a partial failure here leaves the entry at version 1 --
    # migration retries in full on the next start, and is idempotent, because
    # entities already rewritten to version 2 no longer match `v2_unique_id`'s
    # version-1 patterns.
    await _migrate_entity_registry(hass, entry, price_map, wallet_map)

    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_CURRENCY_ID: currency_id},
        options={
            CONF_TRACKED_ASSETS: list(dict.fromkeys(price_map.values())),
            CONF_TRACKED_WALLETS: list(dict.fromkeys(wallet_map.values())),
            CONF_ASSET_CACHE: resolver.as_dict(),
        },
        version=2,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bitpanda from a config entry."""
    client = BitpandaApiClient(
        entry.data[CONF_API_KEY], async_get_clientsession(hass)
    )
    currency_id = entry.data.get(CONF_CURRENCY_ID, EUR_CURRENCY_ID)
    currency = entry.data.get(CONF_CURRENCY, "EUR")
    resolver = AssetResolver(client, entry.options.get(CONF_ASSET_CACHE, {}))

    portfolio = PortfolioCoordinator(hass, entry, client, currency_id)
    prices = PriceCoordinator(hass, entry, client, portfolio, currency_id)
    earn = EarnCoordinator(hass, entry, client)
    rewards = RewardsCoordinator(hass, entry, client)
    history = HistoryCoordinator(hass, entry, client, currency_id)

    prices.set_tracked(entry.options.get(CONF_TRACKED_ASSETS, []))

    await portfolio.async_config_entry_first_refresh()
    await prices.async_config_entry_first_refresh()
    # Earn, rewards and history are additive. A failure there must not block
    # setup, so they refresh without raising ConfigEntryNotReady -- unlike
    # async_config_entry_first_refresh(), plain async_refresh() never raises
    # it, even on total failure; it only marks last_update_success False. A
    # 401 from any of them is different: DataUpdateCoordinator._async_refresh
    # catches the ConfigEntryAuthFailed each coordinator raises for it and
    # calls config_entry.async_start_reauth_if_available(hass) itself, so the
    # reauth prompt appears even though only portfolio and prices went
    # through async_config_entry_first_refresh() above.
    await earn.async_refresh()
    await rewards.async_refresh()
    await history.async_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "portfolio_coordinator": portfolio,
        "price_coordinator": prices,
        "earn_coordinator": earn,
        "rewards_coordinator": rewards,
        "history_coordinator": history,
        "resolver": resolver,
        "currency": currency,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    if not hass.services.has_service(DOMAIN, "refresh"):
        _last_refresh: dict[str, float] = {"time": 0.0}
        _COOLDOWN = 10.0

        async def handle_refresh(call: ServiceCall) -> None:
            now = time.monotonic()
            if now - _last_refresh["time"] < _COOLDOWN:
                _LOGGER.debug("Refresh cooldown active, ignoring call")
                return
            _last_refresh["time"] = now
            for store in hass.data[DOMAIN].values():
                await store["portfolio_coordinator"].async_request_refresh()
                await store["price_coordinator"].async_request_refresh()

        hass.services.async_register(DOMAIN, "refresh", handle_refresh)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "refresh")
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
