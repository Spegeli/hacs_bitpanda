"""Delete Portfolio sensors' history and long-term statistics: the entry's own
on a currency change, and at setup those an earlier Portfolio left behind in
another currency.

A currency change. Every value the Portfolio's sensors recorded is in the old
currency and would be wrong next to the new one. What goes is what the
Portfolio manages: its figures (naming.PORTFOLIO_KEYS), the wallet, staking
and total sensors of this entry (naming.managed_asset_id), their devices --
the Portfolio device and the wallet devices -- and their history and the
long-term statistics every one of these sensors keeps (state_class,
portfolio_sensor.py). Anything else of the entry -- a legacy entity the
version 1 migration left in place, such as an unresolved wallet, another fiat
wallet or a legacy price sensor, and the legacy device it sits on -- keeps its
entity and its history: the `entities_not_migrated` repair issue tells the
user it stays until they delete it. The wallet groups stay too; the recreated
wallets go back into them.

A new Portfolio setup. The entity IDs carry no currency, and a long-term
statistic is keyed by its entity ID and stores its unit. Deleting a Portfolio
keeps its statistics, so a new Portfolio in another currency meets them under
the very IDs its sensors take (naming.is_portfolio_entity_id). Home Assistant
cannot convert one currency to another: for such a sensor it records no
statistics at all, and lists a "units changed" issue until the old ones are
gone. async_find_old_statistics finds them, so that setup can offer to delete
them; the deletion is the one the currency change uses
(async_purge_recorded).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import async_list_statistic_ids
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .devices import device_identifiers
from .naming import (
    PORTFOLIO_KEYS,
    is_portfolio_entity_id,
    managed_asset_id,
    portfolio_device_identifier,
    portfolio_unique_id,
    wallet_device_asset_id,
)

_LOGGER = logging.getLogger(__name__)

_RECORDER = "recorder"

# Seconds setup waits for the recorder's list of statistics: a recorder busy
# with a database migration, or a locked database, must not hold the dialog.
_LISTING_TIMEOUT = 10


def _is_managed_device(entry_id: str, device: dr.DeviceEntry) -> bool:
    """The Portfolio device or a wallet device of this entry."""
    return any(
        identifier == portfolio_device_identifier(entry_id)
        or wallet_device_asset_id(entry_id, identifier) is not None
        for identifier in device_identifiers(device)
    )


async def async_purge_recorded(hass: HomeAssistant, entity_ids: list[str]) -> None:
    """Delete the recorded history and the long-term statistics of `entity_ids`.

    Order matters. purge_entities fixes its cut-off when it is called
    (keep_days 0: now) and removes only what was recorded before it, so the
    states the recreated sensors write afterwards -- after the caller's
    reload or setup -- are never touched, however long the recorder takes to
    work its queue. The statistics clear is queued right behind it, before
    any of those sensors compiles statistics.

    Does nothing without entity IDs or without the recorder.
    """
    if not entity_ids or _RECORDER not in hass.config.components:
        return
    await hass.services.async_call(
        _RECORDER,
        "purge_entities",
        {"entity_id": entity_ids, "keep_days": 0},
        blocking=True,
    )
    get_instance(hass).async_clear_statistics(entity_ids)


async def async_purge_portfolio(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove what the Portfolio manages (see above), with history and statistics.

    Order matters. The entry is unloaded first, so no sensor writes a state
    while its history is purged; history and statistics go last, through
    async_purge_recorded, whose cut-off spares what the recreated sensors
    write after the caller's reload.

    Returns False, with nothing changed, when the entry cannot be unloaded
    -- its unload fails now, or it is in a state Home Assistant can neither
    unload nor reload before a restart (an earlier failed unload, a failed
    migration). The currency change would be left half done: the reload
    that follows a purge cannot bring such an entry back.
    """
    if entry.state is ConfigEntryState.LOADED:
        if not await hass.config_entries.async_unload(entry.entry_id):
            return False
    elif not entry.state.recoverable:
        return False

    entry_id = entry.entry_id
    figures = {portfolio_unique_id(entry_id, key) for key in PORTFOLIO_KEYS}
    ent_reg = er.async_get(hass)
    entity_ids = [
        reg_entry.entity_id
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry_id)
        if reg_entry.unique_id in figures
        or managed_asset_id(entry_id, reg_entry.unique_id) is not None
    ]
    for entity_id in entity_ids:
        ent_reg.async_remove(entity_id)
    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry_id):
        if _is_managed_device(entry_id, device):
            dev_reg.async_remove_device(device.id)

    await async_purge_recorded(hass, entity_ids)
    return True


@dataclass(frozen=True)
class OldStatistics:
    """What an earlier Portfolio left in another currency.

    `entity_ids` are the IDs to delete, sorted -- empty when no question needs
    to be asked; `currencies` are the other currencies found, sorted.
    """

    entity_ids: list[str]
    currencies: list[str]


def _is_live(hass: HomeAssistant, entity_id: str) -> bool:
    """Whether something lives under `entity_id`: it is registered, or it
    has a state."""
    return (
        er.async_get(hass).async_get(entity_id) is not None
        or hass.states.get(entity_id) is not None
    )


async def async_find_old_statistics(hass: HomeAssistant, currency: str) -> OldStatistics:
    """Look for long-term statistics an earlier Portfolio left in another
    currency than `currency` (upper case), under the IDs a new Portfolio's
    sensors take.

    Only a statistic under a Portfolio ID counts
    (naming.is_portfolio_entity_id), and only one whose sensor is gone: a
    deleted Portfolio leaves neither an entity-registry entry nor a state, so
    a statistic whose ID still has one belongs to a sensor that exists -- a
    template's or another integration's under a matching ID -- and cannot be
    attributed to the integration safely. It counts neither for the question
    nor for the deletion, whatever its unit. What this cannot tell apart is a
    look-alike that is gone as well -- a deleted template with a wallet-like
    ID: its statistics count as the earlier Portfolio's.

    A statistic without a unit never counts either: every Portfolio sensor
    has one -- its currency, or "%" for a return -- so such a statistic is
    another sensor's. A question is needed when one of the statistics that
    count has a unit that is neither `currency` nor "%", so any other
    currency code, also one the integration no longer supports. Then every
    one of them goes, whatever its unit: the earlier Portfolio's sensors are
    deleted together, as they are in a currency change. Statistics in the
    same currency ask nothing: they simply continue.

    Nothing is found without the recorder, or when the listing fails or takes
    longer than _LISTING_TIMEOUT: setup goes on without the question, and the
    manual way stays. The error is logged by its type alone, as everywhere
    here.
    """
    nothing = OldStatistics(entity_ids=[], currencies=[])
    if _RECORDER not in hass.config.components:
        return nothing
    try:
        async with asyncio.timeout(_LISTING_TIMEOUT):
            listed = await async_list_statistic_ids(hass)
        # A statistic of another source is an external one, keyed `domain:id`,
        # which no Portfolio ID matches: the source check only guards that.
        units: dict[str, str] = {
            entry["statistic_id"]: entry["statistics_unit_of_measurement"]
            for entry in listed
            if entry["source"] == _RECORDER
            and entry["statistics_unit_of_measurement"] is not None
            and is_portfolio_entity_id(entry["statistic_id"])
            and not _is_live(hass, entry["statistic_id"])
        }
    except Exception as err:  # noqa: BLE001 - setup goes on without the question
        _LOGGER.warning(
            "Could not look for long-term statistics of an earlier Bitpanda "
            "Portfolio (%s); setup continues without asking about them",
            type(err).__name__,
        )
        return nothing
    currencies = {unit for unit in units.values() if unit not in (currency, PERCENTAGE)}
    if not currencies:
        return nothing
    return OldStatistics(entity_ids=sorted(units), currencies=sorted(currencies))
