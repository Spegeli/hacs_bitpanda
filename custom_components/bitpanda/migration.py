"""Migration of a version 1 (legacy API) config entry to version 3.

Version 1 was one entry: the legacy API key, a currency, and two lists the
user picked -- price-tracked symbols and wallet ids. Version 3 is two
services. The version 1 entry becomes the Portfolio in place; its tracked
prices move to a new Price Tracker entry created through an import flow.

Entity history is kept: every legacy entity is re-keyed to its new unique_id
and, while its ID is still the legacy default, renamed to the new scheme --
the recorder moves history and statistics along with a rename. A user's own
entity IDs are never renamed, and nothing that cannot be mapped with
certainty is changed or deleted: it is listed in a notification instead.
The notification is written in the language Home Assistant runs in, from
templates under `exceptions` in strings.json and translations/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.translation import async_get_translations

from .api import BitpandaApiClient, BitpandaApiError, BitpandaRateLimitError
from .assets import legacy_candidates, pick_legacy, slim_asset
from .const import (
    API_KEY_URL,
    CONF_API_KEY,
    CONF_CURRENCY,
    CONF_CURRENCY_ID,
    CONF_EXTRA_CURRENCIES,
    CONF_LEGACY_ADOPT,
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DEFAULT_CURRENCY,
    DOMAIN,
    ENTRY_TYPE,
    ENTRY_TYPE_PORTFOLIO,
    EUR_CURRENCY_ID,
    IMPORT_ASSETS,
    PORTFOLIO_TITLE,
    SUPPORTED_CURRENCIES,
)
from .devices import find_entry_device
from .groups import price_group_of_asset
from .naming import (
    LEGACY_PORTFOLIO_OBJECT_ID,
    is_default_entity_id,
    legacy_price_object_id,
    legacy_wallet_object_id,
    managed_asset_id,
    portfolio_entity_id,
    portfolio_unique_id,
    price_entity_id,
    price_unique_id,
    wallet_entity_id,
    wallet_unique_id,
)

_LOGGER = logging.getLogger(__name__)

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
    succeeds outright (a bare symbol) or legitimately fails (an unrecognised
    category), in which case the entity is left in place and listed, with
    the reason, in the migration notification -- both are safer than
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


@dataclass(frozen=True)
class Message:
    """A text of the migration notification: the key of its template under
    `exceptions` in strings.json, and the values of its placeholders."""

    key: str
    placeholders: dict[str, str] = field(default_factory=dict)

    def render(self, templates: dict[str, str]) -> str:
        """This text in the language of `templates`, the `exceptions`
        translations as async_get_translations returns them: English stands
        in for any template the language lacks."""
        template = templates.get(f"component.{DOMAIN}.exceptions.{self.key}.message", self.key)
        return template.format(**self.placeholders)


@dataclass
class MigrationPlan:
    """Everything the migration resolved, before anything is changed."""

    currency: str
    currency_id: str
    wallets: dict[str, dict] = field(default_factory=dict)
    prices: dict[str, dict] = field(default_factory=dict)
    cash_wallet: str | None = None
    reasons: dict[str, Message] = field(default_factory=dict)
    notes: list[Message] = field(default_factory=list)


def legacy_price_key(entry_id: str, unique_id: str) -> tuple[str, str] | None:
    """(symbol, currency) of a legacy price unique_id "{entry_id}_{SYMBOL}_price_{CUR}".

    rpartition: the symbol can itself contain underscores. A wallet unique_id
    never contains "_price_".
    """
    head, sep, currency = unique_id.rpartition("_price_")
    prefix = f"{entry_id}_"
    if not sep or not head.startswith(prefix) or not currency:
        return None
    return head[len(prefix):], currency


def free_entity_id(hass: HomeAssistant, entity_id: str, reserved=frozenset()) -> str:
    """`entity_id`, or the first free "_2", "_3", ... variant, the way Home
    Assistant itself numbers a taken ID.

    Free the way the entity registry itself checks it: registered by no
    entity, and available in the state machine -- no state, and not reserved
    for an entity being added. `reserved` holds IDs planned in this run that
    are not registered yet.
    """
    ent_reg = er.async_get(hass)
    candidate, number = entity_id, 2
    while (
        candidate in reserved
        or ent_reg.async_is_registered(candidate)
        or not hass.states.async_available(candidate)
    ):
        candidate = f"{entity_id}_{number}"
        number += 1
    return candidate


def _legacy_wallet_ids(hass: HomeAssistant, entry: ConfigEntry) -> list[str]:
    """Wallet ids from the options and from the registry, minus the ones an
    earlier, interrupted run already re-keyed to a UUID."""
    prefix = f"{entry.entry_id}_wallet_"
    registered = [
        reg_entry.unique_id[len(prefix):]
        for reg_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if reg_entry.unique_id.startswith(prefix)
        and managed_asset_id(entry.entry_id, reg_entry.unique_id) is None
    ]
    return list(dict.fromkeys([*entry.options.get(CONF_TRACKED_WALLETS, []), *registered]))


def _legacy_symbols(hass: HomeAssistant, entry: ConfigEntry) -> list[str]:
    registered = [
        key[0]
        for reg_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if (key := legacy_price_key(entry.entry_id, reg_entry.unique_id)) is not None
    ]
    return list(dict.fromkeys([*entry.options.get(CONF_TRACKED_ASSETS, []), *registered]))


async def async_plan(hass: HomeAssistant, entry: ConfigEntry) -> MigrationPlan:
    """Resolve every legacy identifier. Changes nothing; API errors propagate.

    Public endpoints only, called without a key: the legacy key plays no
    part. An empty answer is the only meaning of "no longer exists" -- a
    timeout or a 5xx says nothing about a symbol, so it aborts instead.
    """
    client = BitpandaApiClient(None, async_get_clientsession(hass))
    currency = entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY)
    currencies = await client.async_get_currencies()
    if not any(c.get("symbol") == "EUR" and c.get("id") for c in currencies):
        # Empty, or missing EUR: too broken a list to plan a migration from.
        # Abort with nothing changed rather than silently switch a non-EUR
        # user to EUR on a fallback built from a bad answer -- a currency
        # genuinely missing from an otherwise valid list still falls back
        # further down.
        raise BitpandaApiError("/currencies returned no usable currency list")
    ids = {c.get("symbol"): c.get("id") for c in currencies}
    if currency in SUPPORTED_CURRENCIES and ids.get(currency):
        plan = MigrationPlan(currency=currency, currency_id=ids[currency])
    else:
        plan = MigrationPlan(
            currency=DEFAULT_CURRENCY,
            currency_id=ids.get(DEFAULT_CURRENCY) or EUR_CURRENCY_ID,
        )
        plan.notes.append(Message("migration_currency_dropped", {"currency": currency}))

    candidates: dict[str, list[dict]] = {}

    async def _resolve(symbol: str, prefix: str | None) -> tuple[dict | None, Message | None]:
        if symbol not in candidates:
            # Never an empty symbol: without the filter /assets lists the
            # whole 14,000-asset catalogue.
            candidates[symbol] = (
                await client.async_get_assets(symbol=symbol) if symbol else []
            )
        asset = pick_legacy(candidates[symbol], prefix)
        if asset is not None:
            return slim_asset(asset), None
        survivors = legacy_candidates(candidates[symbol], prefix)
        if len(survivors) > 1:
            return None, Message(
                "migration_asset_ambiguous", {"symbol": symbol, "count": str(len(survivors))}
            )
        return None, Message("migration_asset_gone", {"symbol": symbol})

    fiat: list[str] = []
    for wallet_id in _legacy_wallet_ids(hass, entry):
        prefix = legacy_prefix(wallet_id)
        if prefix == "fiat_":
            fiat.append(wallet_id)
            continue
        asset, reason = await _resolve(legacy_symbol(wallet_id), prefix)
        if asset is not None:
            plan.wallets[wallet_id] = asset
        else:
            plan.reasons[wallet_id] = reason

    for symbol in _legacy_symbols(hass, entry):
        asset, reason = await _resolve(symbol, None)
        if asset is not None:
            plan.prices[symbol] = asset
        else:
            plan.reasons[symbol] = reason

    # Portfolio Cash sums every fiat balance. The legacy fiat wallet in the
    # entry currency -- else the only one -- carries its history over.
    preferred = f"fiat_{currency}"
    if preferred in fiat:
        plan.cash_wallet = preferred
    elif len(fiat) == 1:
        plan.cash_wallet = fiat[0]
    for wallet_id in fiat:
        if wallet_id != plan.cash_wallet:
            plan.reasons[wallet_id] = Message("migration_fiat_in_cash")
    return plan


def plan_price_adoption(
    hass: HomeAssistant, entry: ConfigEntry, plan: MigrationPlan
) -> tuple[list[dict], list[tuple[str, str]], list[tuple[str, Message]]]:
    """Which legacy price entities the Price Tracker adopts, and as what.

    Changes nothing: the Price Tracker entry does the moving on its first
    setup, before it creates any entity (migration.async_adopt_legacy_prices).
    """
    items: list[dict] = []
    renames: list[tuple[str, str]] = []
    skipped: list[tuple[str, Message]] = []
    reserved: set[str] = set()
    for reg_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        key = legacy_price_key(entry.entry_id, reg_entry.unique_id)
        if key is None:
            continue
        symbol, currency = key
        asset = plan.prices.get(symbol)
        if asset is None:
            skipped.append(
                (
                    reg_entry.entity_id,
                    plan.reasons.get(symbol, Message("migration_unknown_asset")),
                )
            )
            continue
        if currency not in SUPPORTED_CURRENCIES:
            skipped.append(
                (reg_entry.entity_id, Message("migration_currency_gone", {"currency": currency}))
            )
            continue
        new_entity_id = None
        if is_default_entity_id(reg_entry.entity_id, legacy_price_object_id(symbol, currency)):
            new_entity_id = free_entity_id(hass, price_entity_id(asset, currency), reserved)
            reserved.add(new_entity_id)
            renames.append((reg_entry.entity_id, new_entity_id))
        items.append(
            {
                "entity_id": reg_entry.entity_id,
                "unique_id": reg_entry.unique_id,
                "asset_id": asset["id"],
                "currency": currency,
                "new_entity_id": new_entity_id,
            }
        )
    return items, renames, skipped


async def _async_create_price_tracker(
    hass: HomeAssistant, entry: ConfigEntry, plan: MigrationPlan, items: list[dict]
) -> str:
    """Create the Price Tracker through its import flow.

    Returns "none" (nothing tracked), "created", "exists" (a Price Tracker was
    already set up; nothing adopted) or "failed". Awaited: the new entry's
    setup, adoption included, runs inside the flow.
    """
    if not plan.prices:
        return "none"
    extras = {item["currency"] for item in items} | {plan.currency}
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={
            IMPORT_ASSETS: list({a["id"]: a for a in plan.prices.values()}.values()),
            CONF_EXTRA_CURRENCIES: sorted(c for c in extras if c != "EUR"),
            CONF_LEGACY_ADOPT: {"source_entry_id": entry.entry_id, "entities": items},
        },
    )
    if result["type"] == FlowResultType.CREATE_ENTRY:
        return "created"
    if result.get("reason") == "already_configured":
        return "exists"
    _LOGGER.error(
        "Cannot migrate the Bitpanda config entry: the Price Tracker could not be "
        "created (%s). Migration will be retried on the next restart.",
        result.get("reason"),
    )
    return "failed"


def rewrite_portfolio_registry(
    hass: HomeAssistant, entry: ConfigEntry, plan: MigrationPlan
) -> tuple[list[tuple[str, str]], list[tuple[str, Message]]]:
    """Re-key, rename and detach the entry's wallet and portfolio entities.

    Returns the renames (old, new) and every entity left alone, with the
    reason. Idempotent: an entity an earlier run already re-keyed carries a
    UUID unique_id or a new Portfolio key and matches nothing here any more.
    """
    ent_reg = er.async_get(hass)
    eid = entry.entry_id
    wallet_prefix = f"{eid}_wallet_"
    renames: list[tuple[str, str]] = []
    skipped: list[tuple[str, Message]] = []
    reserved: set[str] = set()
    for reg_entry in list(er.async_entries_for_config_entry(ent_reg, eid)):
        unique_id = reg_entry.unique_id
        if unique_id == portfolio_unique_id(eid, "total"):
            new_unique_id = None
            target = portfolio_entity_id("total")
            legacy_default = LEGACY_PORTFOLIO_OBJECT_ID
        elif unique_id.startswith(wallet_prefix) and managed_asset_id(eid, unique_id) is None:
            wallet_id = unique_id[len(wallet_prefix):]
            legacy_default = legacy_wallet_object_id(legacy_symbol(wallet_id))
            if wallet_id in plan.wallets:
                asset = plan.wallets[wallet_id]
                new_unique_id = wallet_unique_id(eid, asset["id"])
                target = wallet_entity_id(asset)
            elif wallet_id == plan.cash_wallet:
                new_unique_id = portfolio_unique_id(eid, "cash")
                target = portfolio_entity_id("cash")
            else:
                reason = plan.reasons.get(wallet_id, Message("migration_unknown_wallet"))
                skipped.append((reg_entry.entity_id, reason))
                continue
        else:
            continue  # price entities: adopted by the Price Tracker
        if new_unique_id is not None and ent_reg.async_get_entity_id(
            reg_entry.domain, DOMAIN, new_unique_id
        ):
            skipped.append((reg_entry.entity_id, Message("migration_duplicate")))
            continue
        updates: dict[str, Any] = {"device_id": None}
        if new_unique_id is not None:
            updates["new_unique_id"] = new_unique_id
        if reg_entry.entity_id != target and is_default_entity_id(
            reg_entry.entity_id, legacy_default
        ):
            updates["new_entity_id"] = free_entity_id(hass, target, reserved)
            reserved.add(updates["new_entity_id"])
            renames.append((reg_entry.entity_id, updates["new_entity_id"]))
        ent_reg.async_update_entity(reg_entry.entity_id, **updates)
    return renames, skipped


def remove_empty_legacy_device(hass: HomeAssistant, entry_id: str, identifier: str) -> None:
    """Remove a legacy device once no entity refers to it any more.

    Removing a device also removes its entities -- which is why every
    migrated entity was detached first, and why a device that still holds a
    legacy entity the migration left alone is kept. The device is looked up
    within its own config entry, `entry_id` (see `devices.find_entry_device`).
    """
    device = find_entry_device(hass, entry_id, identifier)
    if device is None:
        return
    if er.async_entries_for_device(er.async_get(hass), device.id, include_disabled_entities=True):
        return
    dr.async_get(hass).async_remove_device(device.id)


@callback
def async_adopt_legacy_prices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Take over the legacy price entities the migration listed for `entry`.

    Runs first in the Price Tracker's setup, before it creates any entity:
    an adopted entity must already carry its new unique_id when the new
    sensor is added, or Home Assistant would create a "_2" twin beside it.
    Each entity moves into the group that tracks its asset; an entity whose
    asset no group tracks stays where it is.
    """
    adopt = entry.data.get(CONF_LEGACY_ADOPT) or {}
    ent_reg = er.async_get(hass)
    for item in adopt.get("entities", []):
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, item["unique_id"])
        group = price_group_of_asset(entry, item["asset_id"])
        if entity_id is None or group is None:
            continue
        new_unique_id = price_unique_id(entry.entry_id, item["asset_id"], item["currency"])
        if ent_reg.async_get_entity_id("sensor", DOMAIN, new_unique_id) is not None:
            _LOGGER.warning(
                "Not adopting %s: another entity already stands for the same price",
                entity_id,
            )
            continue
        updates: dict[str, Any] = {
            "config_entry_id": entry.entry_id,
            "config_subentry_id": group.subentry_id,
            "device_id": None,
            "new_unique_id": new_unique_id,
        }
        target = item.get("new_entity_id")
        if target and target != entity_id:
            updates["new_entity_id"] = free_entity_id(hass, target)
        ent_reg.async_update_entity(entity_id, **updates)
    source = adopt.get("source_entry_id")
    if source:
        remove_empty_legacy_device(hass, source, f"{source}_price_tracker")
    hass.config_entries.async_update_entry(
        entry, data={k: v for k, v in entry.data.items() if k != CONF_LEGACY_ADOPT}
    )


def _migration_text(
    templates: dict[str, str],
    renames: list[tuple[str, str]],
    skipped: list[tuple[str, Message]],
    notes: list[Message],
) -> str:
    """The notification's text in the language of `templates`."""
    paragraphs = [Message("migration_intro").render(templates)]
    if renames:
        rename_list = "\n".join(f"- `{old}` → `{new}`" for old, new in renames)
        paragraphs.append(Message("migration_renamed", {"renames": rename_list}).render(templates))
    if skipped:
        entity_list = "\n".join(
            f"- `{entity_id}`: {reason.render(templates)}" for entity_id, reason in skipped
        )
        paragraphs.append(
            Message("migration_not_migrated", {"entities": entity_list}).render(templates)
        )
    paragraphs += [note.render(templates) for note in notes]
    paragraphs.append(Message("migration_new_key", {"api_key_url": API_KEY_URL}).render(templates))
    return "\n\n".join(paragraphs)


async def _async_notify(
    hass: HomeAssistant,
    renames: list[tuple[str, str]],
    skipped: list[tuple[str, Message]],
    notes: list[Message],
) -> None:
    """Tell the user what changed, in the language Home Assistant runs in."""
    english = await async_get_translations(hass, "en", "exceptions", {DOMAIN})
    templates = await async_get_translations(
        hass, hass.config.language, "exceptions", {DOMAIN}
    )
    # A persistent notification lives in memory only. The same text goes to
    # the log once -- in English, like every log line -- so the old -> new
    # mapping outlives a restart.
    _LOGGER.warning("%s", _migration_text(english, renames, skipped, notes))
    persistent_notification.async_create(
        hass,
        _migration_text(templates, renames, skipped, notes),
        title=Message("migration_title").render(templates),
        notification_id=f"{DOMAIN}_migration",
    )


def _portfolio_taken(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return any(
        other.entry_id != entry.entry_id and other.unique_id == ENTRY_TYPE_PORTFOLIO
        for other in hass.config_entries.async_entries(DOMAIN)
    )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry to version 3."""
    if entry.version > 3:
        _LOGGER.error(
            "The Bitpanda config entry was written by a newer release of this "
            "integration (version %s) and cannot be loaded by this one",
            entry.version,
        )
        return False
    if entry.version == 3:
        return True
    if entry.version == 2:
        _LOGGER.error(
            "This Bitpanda config entry comes from an unreleased development "
            "build (version 2) that cannot be migrated. Please remove the "
            "Bitpanda integration and add it again."
        )
        return False
    # The recorder moves an entity's history along with an entity-ID rename
    # only while its entity registry listener is installed. Before Home
    # Assistant 2025.5 it installed that listener only once Home Assistant had
    # started -- after config entry migrations such as this one -- so every
    # rename below would leave the history behind under the old ID. HACS
    # enforces the floor (hacs.json); this covers a manual install.
    if (MAJOR_VERSION, MINOR_VERSION) < (2025, 5):
        _LOGGER.error(
            "Updating the Bitpanda config entry needs Home Assistant 2025.5 or newer "
            "to keep entity history. Nothing has been changed; update Home Assistant "
            "and restart."
        )
        return False
    if _portfolio_taken(hass, entry):
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: a Bitpanda Portfolio is "
            "already set up. Remove one of the two entries."
        )
        return False

    _LOGGER.info("Migrating the Bitpanda config entry to version 3")
    try:
        plan = await async_plan(hass, entry)
    except BitpandaRateLimitError:
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: rate limited by the "
            "Bitpanda API. Nothing has been changed; migration will be retried "
            "on the next restart."
        )
        return False
    except BitpandaApiError as err:
        # The message names only a path and a cause, never request data.
        _LOGGER.error(
            "Cannot migrate the Bitpanda config entry: %s. Nothing has been "
            "changed; migration will be retried on the next restart.",
            err,
        )
        return False

    # plan_price_adoption only reads, so it can run before the import; the
    # registry rewrite must not -- a failed import has to leave the entry,
    # registry included, exactly as it was.
    items, price_renames, price_skipped = plan_price_adoption(hass, entry, plan)
    outcome = await _async_create_price_tracker(hass, entry, plan, items)
    if outcome == "failed":
        return False
    # Registry rewrite, after the Price Tracker step and before the version
    # bump: every step from here on is idempotent, so a migration whose
    # version bump was never saved runs again in full on the next start. A
    # hard kill after the bump *was* saved is not covered by this -- the
    # entity registry itself saves later than config entries, and that
    # residual gap is an accepted risk, not one this code closes.
    renames, skipped = rewrite_portfolio_registry(hass, entry, plan)
    if outcome == "exists":
        price_renames = []
        price_skipped += [
            (item["entity_id"], Message("migration_price_tracker_exists")) for item in items
        ]
    remove_empty_legacy_device(hass, entry.entry_id, f"{entry.entry_id}_wallets")
    hass.config_entries.async_update_entry(
        entry,
        title=PORTFOLIO_TITLE,
        unique_id=ENTRY_TYPE_PORTFOLIO,
        data={
            ENTRY_TYPE: ENTRY_TYPE_PORTFOLIO,
            CONF_API_KEY: entry.data[CONF_API_KEY],
            CONF_CURRENCY: plan.currency,
            CONF_CURRENCY_ID: plan.currency_id,
        },
        options={},
        version=3,
    )
    await _async_notify(hass, renames + price_renames, skipped + price_skipped, plan.notes)
    return True
