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
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .streaks import FailureStreak

_DataT = TypeVar("_DataT")
_CoordinatorT = TypeVar("_CoordinatorT", bound="TolerantCoordinator[Any]")

# The warning about a key Home Assistant's reauth dialog asks a new one for.
_KEY_REJECTED = "the API key was rejected; its sensors are unavailable until a new key is entered"


class Rejected(UpdateFailed):
    """A refresh that cannot succeed until the API key changes: the key it
    borrows is missing, or Bitpanda refused it. It confirms the failure at
    once, as a rejected key (ConfigEntryAuthFailed) does, but Home Assistant
    starts no reauth for it: the service that borrows the key asks the
    Portfolio for a new one (keys.py). Its message is the reason, for the
    log."""


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
    key confirms it at once -- the key does not become valid again by
    itself --, and so does a refresh Rejected for its borrowed key. Home
    Assistant logs either only when the outcome it holds as it catches it is
    a success -- the refresh before succeeded, unless refreshes overlap --
    and never at the first refresh; otherwise it is warned about here, once
    per reason until a refresh succeeds.
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

    Refreshes never overlap: Home Assistant locks each refresh from 2025.11
    on, and a lock of the coordinator's own keeps 2025.5 to 2025.10 alike,
    where a refresh by hand could run while a scheduled one was under way.
    A refresh asked for meanwhile begins once the one under way has ended,
    as on 2025.11, and counts as asked for then. The outcome and the data
    before it are noted before the wait, as Home Assistant notes its own:
    before 2025.11 its part of a refresh runs outside the lock, and from
    2025.11 on nothing waits here (see _async_refresh_finished).
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
        # What was told about a rejection since the last success -- by Home
        # Assistant, rejected right after it, or here: its reason.
        self._rejection_told: str | None = None
        # Whether the refresh under way is the first, which Home Assistant
        # runs without logging its failure.
        self._first_refresh = False
        # One fetch at a time (see the class docstring).
        self._fetch_lock = asyncio.Lock()

    @property
    def data_available(self) -> bool:
        """Whether the sensors may show `data`: the last refresh succeeded,
        or there is data from an earlier one and the failure is not
        confirmed yet."""
        return self.last_update_success or (self.data is not None and not self._confirmed)

    async def async_config_entry_first_refresh(self) -> None:
        """Home Assistant's first refresh, noted as the first: it logs none
        of its failures, so a rejection then is warned about here."""
        self._first_refresh = True
        try:
            await super().async_config_entry_first_refresh()
        finally:
            self._first_refresh = False

    @final
    async def _async_update_data(self) -> _DataT:
        # Home Assistant's own previous_update_success and previous_data, for
        # this refresh alone, noted as it notes them: before any wait for
        # another refresh. The streak cannot stand in for the outcome: a
        # refresh cancelled while under way never gets to the hook, yet Home
        # Assistant 2026.9 marks it failed.
        succeeded_before, data_before = self.last_update_success, self.data
        async with self._fetch_lock:
            return await self._async_fetch_in_turn(succeeded_before, data_before)

    async def _async_fetch_in_turn(
        self, succeeded_before: bool, data_before: _DataT | None
    ) -> _DataT:
        """The refresh proper, once no other is under way."""
        # When the refresh was asked for -- not when its answer arrived,
        # which a slow request would put later than the regular pace -- or,
        # after waiting for another, when that one ended.
        requested_at = dt_util.utcnow()
        # A refresh that never got to _async_refresh_finished left its entry
        # behind: one cancelled while under way, or one whose error Home
        # Assistant raises again before the hook -- a rejected key at the
        # first refresh, say. Its task is done by now, or will be by the next
        # refresh: every refresh drops the entries of the tasks that are.
        for ended in [task for task in self._refreshes if task is not None and task.done()]:
            del self._refreshes[ended]
        refresh = _Refresh(requested_at, succeeded_before, data_before)
        self._refreshes[asyncio.current_task()] = refresh
        try:
            return await self._async_fetch(requested_at)
        except (ConfigEntryAuthFailed, Rejected):
            # The outcome Home Assistant's own except block reads next --
            # nothing runs in between -- to decide whether it logs the
            # rejection; it never logs the first refresh's.
            refresh.succeeded_at_rejection = self.last_update_success and not self._first_refresh
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
        own entry. A refresh without an entry --
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
            self._rejection_told = None
            return
        self._streak.add(refresh.requested_at)
        tell = self.data is not refresh.data_before
        failure = self.last_exception
        rejected = isinstance(failure, (ConfigEntryAuthFailed, Rejected))
        reason = str(failure) if isinstance(failure, Rejected) else _KEY_REJECTED
        if rejected and self._rejection_told != reason:
            self._rejection_told = reason
            # Home Assistant logs a rejection only when the outcome it held
            # as it caught it was a success, and never at the first refresh.
            if not refresh.succeeded_at_rejection:
                self.logger.warning("%s: %s", self.name, reason)
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
