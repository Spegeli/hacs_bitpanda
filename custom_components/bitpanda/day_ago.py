"""The 24-hour references of both services: a price sensor's or a wallet's
price of about 24 hours ago, looked up in Home Assistant's recorder for all
sensors of an entry at once (DayAgoPrices).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
import logging
from typing import Protocol

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CHANGE_24H_TOLERANCE, CHANGE_24H_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

# A lookup: each entity id's price of 24 hours before `now`; an id without
# one is left out.
LookUp = Callable[[HomeAssistant, set[str], datetime], Awaitable[dict[str, float]]]


class DayAgoSensor(Protocol):
    """A sensor DayAgoPrices serves."""

    entity_id: str

    def set_price_24h_ago(self, value: float | None) -> None:
        """The price of 24 hours ago; None: none known."""


# The length of a short-term statistics period.
_PERIOD = timedelta(minutes=5)
# How long the first lookup waits after a sensor joined: the sensors of an
# entry join one after the other, and one query serves them all.
_FIRST_LOOKUP_DELAY = timedelta(seconds=1)


async def async_prices_24h_ago(
    hass: HomeAssistant, statistic_ids: set[str], now: datetime
) -> dict[str, float]:
    """Each statistic's price of 24 hours before `now`, from Home
    Assistant's 5-minute statistics, in one query: the value nearest to that
    time, within CHANGE_24H_TOLERANCE either side -- never an average, and
    never one further off. An id without such a value is left out.

    A 5-minute row's `state` is the sensor's last state in its period, so
    it stood at the period's end: the row's `end` is the time compared. A
    row without a state -- a period the sensor was unavailable throughout
    -- is no value.
    """
    # The recorder is an after-dependency, imported only when it is needed.
    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.statistics import statistics_during_period

    target = now - timedelta(hours=24)
    rows = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        target - CHANGE_24H_TOLERANCE - _PERIOD,
        target + CHANGE_24H_TOLERANCE,
        statistic_ids,
        "5minute",
        None,
        {"state"},
    )
    target_ts = target.timestamp()
    tolerance = CHANGE_24H_TOLERANCE.total_seconds()
    found: dict[str, float] = {}
    for statistic_id, series in rows.items():
        nearest: tuple[float, float] | None = None
        for row in series:
            state, end = row.get("state"), row.get("end")
            if state is None or end is None:
                continue
            distance = abs(end - target_ts)
            if distance <= tolerance and (nearest is None or distance < nearest[0]):
                nearest = (distance, state)
        if nearest is not None:
            found[statistic_id] = nearest[1]
    return found


class DayAgoPrices:
    """The 24 h references of one entry's sensors: a Price Tracker's price
    sensors or a Portfolio's wallets.

    Every sensor joins as Home Assistant adds it and leaves as it is
    removed -- at an unload, when it is disabled, or when it is no longer
    tracked; Home Assistant's stop removes none, and a lookup due while it
    stops fails quietly, as any failed one. One lookup (`look_up`) serves
    all that are there: a second after the first joins -- the others join
    meanwhile -- and then every CHANGE_24H_UPDATE_INTERVAL, until the last
    one leaves. A sensor without a value of a day ago, and every sensor
    after a failed lookup, gets no reference: its 24 h attributes are
    absent, never stale. The sensor's next update publishes them.
    """

    def __init__(self, hass: HomeAssistant, look_up: LookUp) -> None:
        self._hass = hass
        self._look_up = look_up
        self._sensors: dict[str, DayAgoSensor] = {}
        self._timers: list[Callable[[], None]] = []

    @callback
    def join(self, sensor: DayAgoSensor) -> Callable[[], None]:
        """Add `sensor` to the lookups; returns its removal."""
        if not self._sensors:
            self._timers = [
                async_call_later(self._hass, _FIRST_LOOKUP_DELAY, self.async_look_up),
                async_track_time_interval(
                    self._hass, self.async_look_up, CHANGE_24H_UPDATE_INTERVAL
                ),
            ]
        self._sensors[sensor.entity_id] = sensor

        @callback
        def _leave() -> None:
            if self._sensors.get(sensor.entity_id) is sensor:
                del self._sensors[sensor.entity_id]
            if not self._sensors:
                for cancel in self._timers:
                    cancel()
                self._timers = []

        return _leave

    async def async_look_up(self, _: datetime | None = None) -> None:
        """Look up every joined sensor's reference, in one query."""
        sensors = dict(self._sensors)
        if not sensors:
            return
        try:
            found = await self._look_up(self._hass, set(sensors), dt_util.utcnow())
        except Exception as err:  # noqa: BLE001 - optional data, never fatal
            _LOGGER.debug("No 24 h statistics: %s", type(err).__name__)
            found = {}
        for entity_id, sensor in sensors.items():
            sensor.set_price_24h_ago(found.get(entity_id))
