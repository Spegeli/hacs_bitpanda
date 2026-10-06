"""Sensors that keep showing their coordinator's last data through short
outages: TolerantCoordinator counts its failed refreshes, TolerantEntity
takes its availability from it. How many failures in a row, over how much
time, confirm a failure is streaks.FailureStreak's rule.

This departs on purpose from Home Assistant's quality-scale rule
`entity-unavailable`, which asks for unavailable as soon as data cannot be
fetched: the maintainer's decision, 2026-09-27.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any, Generic, TypeVar, final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .streaks import FailureStreak

_DataT = TypeVar("_DataT")
_CoordinatorT = TypeVar("_CoordinatorT", bound="TolerantCoordinator[Any]")


@dataclass
class _Refresh(Generic[_DataT]):
    """What a refresh noted for _async_refresh_finished. As it began: when
    it was asked for, and the outcome and the data before it -- Home
    Assistant's own previous_update_success and previous_data, which it
    keeps for each refresh. And should its key be rejected, the outcome
    Home Assistant holds as it catches that, which decides whether it logs
    the rejection."""

    requested_at: datetime
    succeeded_before: bool
    data_before: _DataT | None
    # None unless the key was rejected.
    succeeded_at_rejection: bool | None = None


class TolerantCoordinator(DataUpdateCoordinator[_DataT]):
    """A coordinator whose sensors show its last data until a failure is
    confirmed.

    DataUpdateCoordinator keeps its data after a failed refresh, but its
    sensors turn unavailable at once (CoordinatorEntity.available): a short
    drop of the Internet connection at home would clear every value from
    the dashboards. Here they go on showing the last data until
    FAILURE_TOLERANCE failed refreshes in a row, the last asked for
    (FAILURE_TOLERANCE - 1) `regular_interval`s after the first at the
    least (streaks.CLOCK_GRACE aside), confirm the failure. A rejected API
    key confirms it at once: the key does not become valid again by itself.
    Home Assistant logs a rejected key only when the outcome it holds as it
    catches the rejection is a success -- the refresh before succeeded,
    unless refreshes overlap; otherwise it is warned about here, once.
    From then on they are unavailable until a refresh succeeds. Without
    data -- a failed first refresh -- there is nothing to show, and they
    are unavailable too. data_available says which applies; TolerantEntity
    reads it.

    `regular_interval` is the interval the time is counted in: the base
    update interval, never a backed-off one, whose failures come further
    apart and take longer to confirm anyway. Refreshes by hand bring
    failures sooner; they count, but never confirm sooner.

    A subclass implements its refresh in _async_fetch, which is handed the
    time the refresh was asked for; _async_update_data is final. A failed
    refresh keeps `data`, unless the subclass replaces it -- to leave out an
    item whose own failure the refresh confirms, say --, and the listeners
    are then told. last_update_success stays the real outcome of the last
    refresh, as diagnostics and bitpanda.refresh report it.

    Refreshes can overlap: Home Assistant 2025.5 takes no lock around one,
    so a refresh by hand can run while a scheduled one is under way. Each is
    judged by its own request time and the outcome and data before it, as
    Home Assistant judges each by its own; see _async_refresh_finished.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        config_entry: ConfigEntry[Any] | None,
        name: str,
        update_interval: timedelta | None,
        regular_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            name=name,
            update_interval=update_interval,
        )
        self._regular_interval = regular_interval
        self._streak = FailureStreak()
        # Whether the failure is confirmed: by the streak, or at once by a
        # rejected key. Only a success clears it, whatever fails after it.
        self._confirmed = False
        # The refreshes under way, by the task that runs each: noted by
        # _async_update_data, taken back by _async_refresh_finished, which
        # Home Assistant calls in the same task.
        self._refreshes: dict[asyncio.Task[Any] | None, _Refresh[_DataT]] = {}
        # Whether a rejected key has been logged since the last success: by
        # Home Assistant, rejected right after it, or here.
        self._rejection_logged = False

    @property
    def data_available(self) -> bool:
        """Whether the sensors may show `data`: the last refresh succeeded,
        or there is data from an earlier one and the failure is not
        confirmed yet."""
        return self.last_update_success or (self.data is not None and not self._confirmed)

    @final
    async def _async_update_data(self) -> _DataT:
        # When the refresh was asked for -- not when its answer arrived,
        # which a slow request would put later than the regular pace.
        requested_at = dt_util.utcnow()
        # A refresh that never got to _async_refresh_finished left its entry
        # behind: one cancelled while under way, or one whose error Home
        # Assistant raises again before the hook -- a rejected key at the
        # first refresh, say. Its task is done by now, or will be by the next
        # refresh: every refresh drops the entries of the tasks that are.
        for ended in [task for task in self._refreshes if task is not None and task.done()]:
            del self._refreshes[ended]
        # Home Assistant's own previous_update_success and previous_data, for
        # this refresh alone. The streak cannot stand in for the outcome: a
        # refresh cancelled while under way never gets to the hook, yet Home
        # Assistant 2026.9 marks it failed.
        refresh = _Refresh(requested_at, self.last_update_success, self.data)
        self._refreshes[asyncio.current_task()] = refresh
        try:
            return await self._async_fetch(requested_at)
        except ConfigEntryAuthFailed:
            # The outcome Home Assistant's own except block reads next --
            # nothing runs in between -- to decide whether it logs the
            # rejection: overlapping refreshes may have changed it since this
            # one began.
            refresh.succeeded_at_rejection = self.last_update_success
            raise

    async def _async_fetch(self, requested_at: datetime) -> _DataT:
        """This coordinator's refresh: the data, or an exception as
        _async_update_data would raise it. `requested_at` is when the
        refresh was asked for, on Home Assistant's clock."""
        raise NotImplementedError

    @callback
    def _async_refresh_finished(self) -> None:
        """Count a failed refresh, or end the streak with a successful one;
        warn once when the failure is confirmed, and once about a rejected
        key that Home Assistant does not log.

        DataUpdateCoordinator calls this once a refresh has run, before it
        updates the listeners -- which, after a failed refresh, it does only
        when the refresh before succeeded. So after a failure that follows a
        failure, this tells the listeners itself when the failure is newly
        confirmed or the data changed (a subclass leaving out an item whose
        own failure the refresh confirms): otherwise the sensors would go on
        showing the last data.

        Each refresh is judged by what it noted as it began, taken back
        here. Home Assistant awaits _async_update_data and calls this in the
        same task, 2025.5 and 2026.9 alike, so the running task finds its
        own entry even when refreshes overlap. A refresh without an entry --
        one that never passed _async_update_data, which neither version runs
        -- takes the clock for its request time, and the outcome and the
        data now for those before it. That keeps every confirmation told:
        after a failure the outcome now reads failed, so a newly confirmed
        failure always tells the listeners, and a rejected key is always
        warned about -- at worst in addition to Home Assistant. Only a change
        of the data in such a refresh would go untold, the data now standing
        in for the data before.
        """
        super()._async_refresh_finished()
        refresh = self._refreshes.pop(asyncio.current_task(), None)
        if refresh is None:
            refresh = _Refresh(dt_util.utcnow(), self.last_update_success, self.data)
        if self.last_update_success:
            self._streak = FailureStreak()
            self._confirmed = False
            self._rejection_logged = False
            return
        self._streak.add(refresh.requested_at)
        tell = self.data is not refresh.data_before
        rejected = isinstance(self.last_exception, ConfigEntryAuthFailed)
        if rejected and not self._rejection_logged:
            self._rejection_logged = True
            # Home Assistant logs a rejected key only when the outcome it
            # held as it caught the rejection was a success.
            if not refresh.succeeded_at_rejection:
                self.logger.warning(
                    "%s: the API key was rejected; its sensors are unavailable "
                    "until a new key is entered",
                    self.name,
                )
        if not self._confirmed and (
            rejected or self._streak.confirmed(self._regular_interval)
        ):
            self._confirmed = True
            tell = True
            # A rejected key is no outage to warn about: Home Assistant
            # starts the reauth dialog for it.
            if not rejected:
                self.logger.warning(
                    "%s: %s refreshes in a row failed; its sensors are "
                    "unavailable until one succeeds",
                    self.name,
                    self._streak.count,
                )
        # After a success Home Assistant tells the listeners itself.
        if tell and not refresh.succeeded_before:
            self.async_update_listeners()


class TolerantEntity(CoordinatorEntity[_CoordinatorT]):
    """An entity of a TolerantCoordinator: available while the coordinator's
    data may be shown, not merely while its last refresh succeeded. A
    subclass with conditions of its own -- a wallet whose asset is still
    listed, say -- adds them to super().available."""

    @property
    def available(self) -> bool:
        return self.coordinator.data_available
