"""Sensor platform: each service sets up its own sensors."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ENTRY_TYPE_PRICE_TRACKER, entry_type
from .portfolio_sensor import async_setup_portfolio_entities
from .price_sensor import async_setup_price_entities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if entry_type(entry) == ENTRY_TYPE_PRICE_TRACKER:
        await async_setup_price_entities(hass, entry, async_add_entities)
    else:
        await async_setup_portfolio_entities(hass, entry, async_add_entities)
