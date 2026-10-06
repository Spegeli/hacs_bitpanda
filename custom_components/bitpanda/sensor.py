"""Sensor platform: each service sets up its own sensors."""
from __future__ import annotations

from typing import cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BitpandaConfigEntry
from .const import ENTRY_TYPE_PRICE_TRACKER, entry_type
from .portfolio_coordinator import PortfolioConfigEntry
from .portfolio_sensor import async_setup_portfolio_entities
from .price_coordinator import PriceTrackerConfigEntry
from .price_sensor import async_setup_price_entities

# Every sensor reads what its service's coordinators fetched and requests
# nothing itself, so Home Assistant needs no limit on parallel updates.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BitpandaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    # The entry's type names its service, and so its runtime data.
    if entry_type(entry) == ENTRY_TYPE_PRICE_TRACKER:
        await async_setup_price_entities(
            hass, cast(PriceTrackerConfigEntry, entry), async_add_entities
        )
    else:
        await async_setup_portfolio_entities(
            hass, cast(PortfolioConfigEntry, entry), async_add_entities
        )
