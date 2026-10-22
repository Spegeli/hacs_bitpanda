"""The 24-hour references of both services: a price sensor's or a wallet's
price of about 24 hours ago, looked up in Home Assistant's recorder for all
sensors of an entry at once (DayAgoPrices).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timedelta
import logging
from typing import Any, Protocol

from homeassistant.core import HomeAssistant, State, callback
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
    tracked; Home Assistant's stop removes none, but ends the periodic
    lookup, and one due while it stops fails quietly, as any failed one.
    One lookup (`look_up`) serves all that are there: a second after the
    first joins -- the others join meanwhile -- and then every
    CHANGE_24H_UPDATE_INTERVAL, until the last one leaves. A sensor without a value of a day ago, and every sensor
    after a failed lookup, gets no reference: its 24 h attributes are
    absent, never stale. The sensor's next update publishes them.

    `last` keeps each joined sensor's last reference, None without one, by
    the key it joined with -- a wallet's asset, whatever its entity ID --
    or by its entity ID: for what answers without a sensor (services.py).
    A sensor that leaves takes it along.
    """

    def __init__(self, hass: HomeAssistant, look_up: LookUp) -> None:
        self._hass = hass
        self._look_up = look_up
        self._sensors: dict[str, DayAgoSensor] = {}
        # Entity ID -> the key of `last` its sensor joined with.
        self._keys: dict[str, str] = {}
        self.last: dict[str, float | None] = {}
        self._timers: list[Callable[[], None]] = []

    @callback
    def join(self, sensor: DayAgoSensor, key: str | None = None) -> Callable[[], None]:
        """Add `sensor` to the lookups, its result kept in `last` under
        `key`, else its entity ID; returns its removal."""
        if not self._sensors:
            self._timers = [
                async_call_later(self._hass, _FIRST_LOOKUP_DELAY, self.async_look_up),
                async_track_time_interval(
                    self._hass,
                    self.async_look_up,
                    CHANGE_24H_UPDATE_INTERVAL,
                    cancel_on_shutdown=True,
                ),
            ]
        self._sensors[sensor.entity_id] = sensor
        self._keys[sensor.entity_id] = key or sensor.entity_id

        @callback
        def _leave() -> None:
            if self._sensors.get(sensor.entity_id) is sensor:
                del self._sensors[sensor.entity_id]
                self.last.pop(self._keys.pop(sensor.entity_id), None)
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
            value = found.get(entity_id)
            sensor.set_price_24h_ago(value)
            # A sensor that left during the lookup keeps nothing here.
            if self._sensors.get(entity_id) is sensor:
                self.last[self._keys[entity_id]] = value


async def async_wallet_prices_24h_ago(
    hass: HomeAssistant, entity_ids: set[str], now: datetime
) -> dict[str, float]:
    """Each wallet's price of 24 hours before `now`: the ticker price its
    Balance (total) sensor recorded then (`price`).

    When: the 5-minute statistics, as for a price sensor
    (async_prices_24h_ago) -- a row every 5 minutes, whether the value
    changed or not (a stablecoin, a stock over the weekend), and none while
    Home Assistant was off. What: the recorded state in effect at the row's
    end. The nearest row within CHANGE_24H_TOLERANCE either side whose state
    recorded a price, in the sensor's currency of today, counts -- after a
    change of the Portfolio's currency the old rows may still be there. A
    state recorded without a price -- by the version before, or while there
    was no ticker price -- is no reference: never the value over the units,
    which /portfolio gives in cents. A wallet without a reference is left
    out. Two queries for all wallets, in one recorder job.
    """
    # The recorder is an after-dependency, imported only when it is needed.
    from homeassistant.components.recorder import get_instance, history
    from homeassistant.components.recorder.statistics import statistics_during_period

    target = now - timedelta(hours=24)
    start = target - CHANGE_24H_TOLERANCE - _PERIOD
    end = target + CHANGE_24H_TOLERANCE
    currencies = {
        entity_id: state.attributes.get("unit_of_measurement")
        for entity_id in entity_ids
        if (state := hass.states.get(entity_id)) is not None
    }

    def _read() -> tuple[Mapping[str, list[Any]], Mapping[str, list[Any]]]:
        rows = statistics_during_period(
            hass, start, end, entity_ids, "5minute", None, {"state"}
        )
        states = history.get_significant_states(
            hass,
            start,
            end,
            entity_ids=list(entity_ids),
            include_start_time_state=True,
            significant_changes_only=False,
            minimal_response=False,
            no_attributes=False,
        )
        return rows, states

    rows, recorded = await get_instance(hass).async_add_executor_job(_read)
    target_ts = target.timestamp()
    tolerance = CHANGE_24H_TOLERANCE.total_seconds()
    found: dict[str, float] = {}
    for entity_id, series in rows.items():
        near = sorted(
            (
                row
                for row in series
                if row.get("state") is not None
                and row.get("end") is not None
                and abs(row["end"] - target_ts) <= tolerance
            ),
            key=lambda row: abs(row["end"] - target_ts),
        )
        states = [state for state in recorded.get(entity_id, []) if isinstance(state, State)]
        for row in near:
            then = _price_then(states, row, currencies.get(entity_id))
            if then is not None:
                found[entity_id] = then
                break
    return found


def _price_then(states: list[State], row: Any, currency: Any) -> float | None:
    """The price at a statistics row's end: the `price` the state in effect
    then recorded."""
    state = _state_at(states, row["end"], currency)
    return None if state is None else _positive(state.attributes.get("price"))


def _positive(value: Any) -> float | None:
    """`value` as a number above 0, or None."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return float(value)
    return None


def _state_at(states: list[State], moment: float, currency: Any) -> State | None:
    """The recorded state in effect at `moment` (a timestamp), a row's end:
    the newest one written before it -- one written at the end is the next
    period's, as for the statistics. None when it is not a number -- the
    wallet unavailable then -- or was in another currency than `currency`,
    today's (None: not known, not compared)."""
    current = None
    for state in states:
        if state.last_updated.timestamp() < moment and (
            current is None or state.last_updated >= current.last_updated
        ):
            current = state
    if current is None:
        return None
    if currency is not None and current.attributes.get("unit_of_measurement") != currency:
        return None
    try:
        float(current.state)
    except ValueError:
        return None
    return current
