"""Sensors that keep showing their coordinator's last data through short
outages: TolerantCoordinator counts its failed refreshes, TolerantEntity
takes its availability from it. How many failures in a row, over how much
time, confirm a failure is streaks.FailureStreak's rule.

This departs on purpose from Home Assistant's quality-scale rule
`entity-unavailable`, which asks for unavailable as soon as data cannot be
fetched: the maintainer's decision, 2026-09-27.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, TypeVar, final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .streaks import FailureStreak

_DataT = TypeVar("_DataT")
_CoordinatorT = TypeVar("_CoordinatorT", bound="TolerantCoordinator[Any]")


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
    Home Assistant logs a rejected key only when the refresh before
    succeeded; rejected after a failed one, it is warned about here, once.
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
        # When the refresh under way was asked for: kept by
        # _async_update_data for _async_refresh_finished, which drops it.
        self._requested_at: datetime | None = None
        # The outcome and the data before the refresh under way, as
        # DataUpdateCoordinator compares them once it is done: kept by
        # _async_update_data for _async_refresh_finished.
        self._succeeded_before = True
        self._data_before: _DataT | None = None
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
        self._requested_at = requested_at
        # Home Assistant's own previous_update_success and previous_data. The
        # streak cannot stand in for the outcome: a refresh cancelled while
        # under way never gets to _async_refresh_finished, yet Home Assistant
        # 2026.9 marks it failed.
        self._succeeded_before = self.last_update_success
        self._data_before = self.data
        return await self._async_fetch(requested_at)

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
        """
        super()._async_refresh_finished()
        requested_at, self._requested_at = self._requested_at, None
        if self.last_update_success:
            self._streak = FailureStreak()
            self._confirmed = False
            self._rejection_logged = False
            return
        # Every refresh passes _async_update_data first; should one ever
        # not, the clock stands in for its request time.
        self._streak.add(requested_at if requested_at is not None else dt_util.utcnow())
        tell = self.data is not self._data_before
        rejected = isinstance(self.last_exception, ConfigEntryAuthFailed)
        if rejected and not self._rejection_logged:
            self._rejection_logged = True
            # Home Assistant logs a rejected key only after a success.
            if not self._succeeded_before:
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
        if tell and not self._succeeded_before:
            self.async_update_listeners()


class TolerantEntity(CoordinatorEntity[_CoordinatorT]):
    """An entity of a TolerantCoordinator: available while the coordinator's
    data may be shown, not merely while its last refresh succeeded. A
    subclass with conditions of its own -- a wallet whose asset is still
    listed, say -- adds them to super().available."""

    @property
    def available(self) -> bool:
        return self.coordinator.data_available
