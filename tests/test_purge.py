"""Deleting the Portfolio's sensors, devices and history on a currency change."""
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.purge import async_purge_portfolio


def _entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    entry.add_to_hass(hass)
    return entry


def _register(hass, entry, unique_id: str) -> str:
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, f"dev_{unique_id}")}
    )
    return er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, unique_id, config_entry=entry, device_id=device.id
    ).entity_id


def _fake_recorder(hass, calls: list):
    hass.config.components.add("recorder")

    async def _purge(call):
        calls.append(("purge", sorted(call.data["entity_id"]), call.data["keep_days"]))

    hass.services.async_register("recorder", "purge_entities", _purge)
    instance = MagicMock()
    instance.async_clear_statistics = MagicMock(
        side_effect=lambda ids: calls.append(("clear", sorted(ids)))
    )
    return instance


async def test_purge_removes_the_entry_entities_devices_history_and_statistics(hass):
    entry = _entry(hass)
    other = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "price_tracker"})
    other.add_to_hass(hass)
    ids = sorted([_register(hass, entry, "a"), _register(hass, entry, "b")])
    kept = _register(hass, other, "c")
    calls: list = []
    instance = _fake_recorder(hass, calls)

    with patch("custom_components.bitpanda.purge.get_instance", return_value=instance):
        await async_purge_portfolio(hass, entry)

    ent_reg = er.async_get(hass)
    assert er.async_entries_for_config_entry(ent_reg, entry.entry_id) == []
    assert dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id) == []
    assert ent_reg.async_get(kept) is not None
    # keep_days 0: everything recorded before this moment goes. Both are
    # queued before the caller reloads the entry.
    assert calls == [("purge", ids, 0), ("clear", ids)]


async def test_purge_without_a_recorder_still_clears_the_registries(hass):
    entry = _entry(hass)
    _register(hass, entry, "a")
    await async_purge_portfolio(hass, entry)
    assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id) == []


async def test_purge_unloads_a_loaded_entry_first(hass):
    entry = _entry(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    with patch.object(hass.config_entries, "async_unload", AsyncMock(return_value=True)) as unload:
        await async_purge_portfolio(hass, entry)
    unload.assert_awaited_once_with(entry.entry_id)
