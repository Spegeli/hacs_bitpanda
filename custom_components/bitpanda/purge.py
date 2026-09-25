"""Delete everything a Portfolio entry created: entities, devices, history.

Used when the Portfolio currency changes: every value in the history was
recorded in the old currency and would be wrong next to the new one.
"""
from __future__ import annotations

from homeassistant.components.recorder import get_instance
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

_RECORDER = "recorder"


async def async_purge_portfolio(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove every entity and device of `entry`, with history and statistics.

    Order matters. The entry is unloaded first, so no sensor writes a state
    while its history is purged. purge_entities fixes its cut-off when it is
    called (keep_days 0: now) and removes only what was recorded before it,
    so the states the recreated sensors write after the caller's reload are
    never touched -- however long the recorder takes to work its queue.
    """
    if entry.state is ConfigEntryState.LOADED:
        await hass.config_entries.async_unload(entry.entry_id)

    ent_reg = er.async_get(hass)
    entity_ids = [
        reg_entry.entity_id
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    ]
    for entity_id in entity_ids:
        ent_reg.async_remove(entity_id)
    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
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
