"""Event platform: the Portfolio's announcements as event entities, on the
Portfolio device (announcements.PORTFOLIO_EVENT_TYPES). The Price Tracker
announces nothing and has none.

An announcement fires its bus event and the entity's event in one call
(announcements.async_announce), with the same data, which the entity shows
as its attributes. An event entity's state is the time of its last event to
the millisecond: two events written within one millisecond would read as
one state, and a state trigger would see only the second. So each entity
writes the events that reach it at least a millisecond apart, the first at
once; the bus events are fired at once all the same.

Home Assistant restores an event entity's last event at a start, firing no
trigger; at a reload the entity is unavailable for a moment and then shows
its last event again, which a plain state trigger takes for a new one; after
a currency change, or once enabled, it comes back with its last event and no
state before (the README's trigger: `not_from` and `not_to` unavailable, and
a state before).
"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BitpandaConfigEntry
from .announcements import PORTFOLIO_EVENT_TYPES, portfolio_event_signal
from .const import ENTRY_TYPE_PRICE_TRACKER, entry_type
from .naming import portfolio_event_entity_id, portfolio_unique_id
from .portfolio_sensor import portfolio_device_info

# The entities request nothing; they show what the announcers send them.
PARALLEL_UPDATES = 0

# Seconds between two events an entity writes: its state counts milliseconds.
_SPACING = 0.001


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BitpandaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if entry_type(entry) == ENTRY_TYPE_PRICE_TRACKER:
        return
    async_add_entities(
        PortfolioEventEntity(entry.entry_id, key) for key in PORTFOLIO_EVENT_TYPES
    )


class PortfolioEventEntity(EventEntity):
    """One kind of the Portfolio's announcements (see the module)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry_id: str, key: str) -> None:
        self._entry_id = entry_id
        self._key = key
        self._attr_translation_key = key
        self._attr_event_types = list(PORTFOLIO_EVENT_TYPES[key])
        self._attr_unique_id = portfolio_unique_id(entry_id, key)
        self.entity_id = portfolio_event_entity_id(key)
        self._attr_device_info = portfolio_device_info(entry_id)
        # The events not written yet, oldest first.
        self._queue: deque[tuple[str, dict[str, Any]]] = deque()
        self._drain: asyncio.TimerHandle | None = None
        # When the last event was written (the event loop's clock).
        self._written_at: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, portfolio_event_signal(self._entry_id), self._async_announced
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._drain is not None:
            self._drain.cancel()
            self._drain = None
        await super().async_will_remove_from_hass()

    @callback
    def _async_announced(self, key: str, event_type: str, data: dict[str, Any]) -> None:
        if key != self._key:
            return
        self._queue.append((event_type, data))
        if self._drain is None:
            self._async_write_next()

    @callback
    def _async_write_next(self) -> None:
        """Write the oldest event waiting, unless the last one was written
        less than a millisecond ago: then, and for any left, a millisecond
        later."""
        self._drain = None
        loop = self.hass.loop
        if self._written_at is not None:
            wait = self._written_at + _SPACING - loop.time()
            if wait > 0:
                self._drain = loop.call_later(wait, self._async_write_next)
                return
        event_type, data = self._queue.popleft()
        self._trigger_event(event_type, data)
        self.async_write_ha_state()
        self._written_at = loop.time()
        if self._queue:
            self._drain = loop.call_later(_SPACING, self._async_write_next)
