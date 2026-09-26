"""Delete what the Portfolio manages, with its history, on a currency change.

Every value its sensors recorded is in the old currency and would be wrong
next to the new one. What goes is what the Portfolio manages: its figures
(naming.PORTFOLIO_KEYS), the wallet, staking and total sensors of this entry
(naming.managed_asset_id), their devices -- the Portfolio device and the
wallet devices -- and their history and statistics. Anything else of the
entry -- a legacy entity the version 1 migration left in place, such as an
unresolved wallet, another fiat wallet or a legacy price sensor, and the
legacy device it sits on -- keeps its entity and its history: the migration
notification promised it stays until the user deletes it. The wallet groups
stay too; the recreated wallets go back into them.
"""
from __future__ import annotations

from homeassistant.components.recorder import get_instance
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .devices import device_identifiers
from .naming import (
    PORTFOLIO_KEYS,
    managed_asset_id,
    portfolio_device_identifier,
    portfolio_unique_id,
    wallet_device_asset_id,
)

_RECORDER = "recorder"


def _is_managed_device(entry_id: str, device: dr.DeviceEntry) -> bool:
    """The Portfolio device or a wallet device of this entry."""
    return any(
        identifier == portfolio_device_identifier(entry_id)
        or wallet_device_asset_id(entry_id, identifier) is not None
        for identifier in device_identifiers(device)
    )


async def async_purge_portfolio(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove what the Portfolio manages (see above), with history and statistics.

    Order matters. The entry is unloaded first, so no sensor writes a state
    while its history is purged. purge_entities fixes its cut-off when it is
    called (keep_days 0: now) and removes only what was recorded before it,
    so the states the recreated sensors write after the caller's reload are
    never touched -- however long the recorder takes to work its queue.
    """
    if entry.state is ConfigEntryState.LOADED:
        await hass.config_entries.async_unload(entry.entry_id)

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

    if not entity_ids or _RECORDER not in hass.config.components:
        return
    await hass.services.async_call(
        _RECORDER,
        "purge_entities",
        {"entity_id": entity_ids, "keep_days": 0},
        blocking=True,
    )
    get_instance(hass).async_clear_statistics(entity_ids)
