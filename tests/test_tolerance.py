"""Tests for the coordinators whose sensors keep their last data through
short outages, and the entities that follow them (tolerance.py)."""
import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.bitpanda.tolerance import TolerantCoordinator, TolerantEntity

F = UpdateFailed("down")
_REGULAR = timedelta(minutes=5)
# Refreshes by hand (bitpanda.refresh) come a cooldown apart.
_BY_HAND = timedelta(seconds=20)
# How long a slow answer takes to arrive.
_LATE = timedelta(seconds=50)
# A refresh that hangs until it is cancelled.
_HANG = "hang"


def _down() -> UpdateFailed:
    """A failed refresh for a script, its own instance: one instance raised
    again and again keeps a growing traceback, and with it the frames of
    every test that raised it, alive."""
    return UpdateFailed("down")


@dataclass
class _Replaced:
    """A failed refresh that replaces the data with `data` first, as a
    subclass does that leaves out an item whose own failure the refresh
    confirms."""

    data: int


class _Probe(TolerantCoordinator[int]):
    """Answers from a script: an int is the data, an exception is raised, a
    _Replaced replaces the data and fails, and _HANG hangs until the refresh
    is cancelled. A callable is called first and answers with what it
    returns -- time can pass in it while the answer is on its way. Every
    fetch records the time its refresh was asked for."""

    def __init__(self, hass, *script):
        super().__init__(
            hass, logging.getLogger(__name__), config_entry=None, name="probe",
            update_interval=None, regular_interval=_REGULAR,
        )
        self.script = list(script)
        self.asked = []

    async def _async_fetch(self, requested_at):
        self.asked.append(requested_at)
        item = self.script.pop(0)
        if callable(item):
            item = item()
        if item == _HANG:
            await asyncio.Event().wait()
        if isinstance(item, _Replaced):
            self.data = item.data
            raise _down()
        if isinstance(item, Exception):
            raise item
        return item


def _late(freezer, answer):
    """An answer that arrives _LATE after its refresh was asked for."""

    def arrive():
        freezer.tick(_LATE)
        return answer

    return arrive


def _listen(probe) -> list[bool]:
    """What the probe's data_available was each time it told its listeners."""
    seen: list[bool] = []
    probe.async_add_listener(lambda: seen.append(probe.data_available))
    return seen


async def _refresh(probe, freezer, pace=_REGULAR) -> None:
    """One refresh, `pace` after the one before."""
    freezer.tick(pace)
    await probe.async_refresh()


async def _run(probe, freezer, pace=_REGULAR) -> None:
    """Refresh the probe until its script is used up, `pace` apart."""
    while probe.script:
        await _refresh(probe, freezer, pace)


def _tolerance_records(caplog) -> list[logging.LogRecord]:
    """The records of the tolerance's own warning. Home Assistant logs the
    first failure of an outage itself, at ERROR: "Error fetching probe data:
    down"."""
    return [
        record for record in caplog.records
        if "refreshes in a row failed" in record.getMessage()
    ]


def _rejection_records(caplog) -> list[logging.LogRecord]:
    """The records of the tolerance's warning about a rejected key."""
    return [
        record for record in caplog.records
        if "the API key was rejected" in record.getMessage()
    ]


async def _cancel_a_refresh(probe) -> None:
    """Start a refresh of the probe, whose script hangs, and cancel it while
    it is under way."""
    asked = len(probe.asked)
    refresh = asyncio.create_task(probe.async_refresh())
    while len(probe.asked) == asked:
        await asyncio.sleep(0)
    refresh.cancel()
    with pytest.raises(asyncio.CancelledError):
        await refresh


async def test_the_first_two_failures_keep_the_last_data_available(hass, freezer):
    probe = _Probe(hass, 1, F, F)
    await probe.async_refresh()
    while probe.script:
        await _refresh(probe, freezer)
        assert probe.data_available is True
        assert probe.data == 1
        assert probe.last_update_success is False


async def test_the_third_failure_at_the_regular_pace_ends_it_and_tells_the_listeners(
    hass, freezer
):
    """Home Assistant tells the listeners itself at the success and at the
    first failure, which follows a success -- never at a failure after a
    failure. So the tolerance tells them at the third; nobody does at the
    second."""
    probe = _Probe(hass, 1, F, F, F)
    seen = _listen(probe)
    await _run(probe, freezer)
    assert probe.data_available is False
    assert seen == [True, True, False]


async def test_failures_by_hand_never_end_it_sooner(hass, freezer):
    """Six failures, but all within two minutes of the first: the regular
    pace would have brought only one of them."""
    probe = _Probe(hass, 1, F, F, F, F, F, F)
    await _run(probe, freezer, pace=_BY_HAND)
    assert probe.data_available is True


async def test_a_success_starts_the_count_again(hass, freezer):
    probe = _Probe(hass, 1, F, F, 2, F, F)
    await _run(probe, freezer)
    assert probe.data_available is True
    assert probe.data == 2


async def test_a_rejected_key_ends_it_at_once(hass, freezer):
    """The key does not become valid again by itself."""
    probe = _Probe(hass, 1, ConfigEntryAuthFailed())
    await _run(probe, freezer)
    assert probe.data_available is False


async def test_a_failure_after_a_rejected_key_keeps_it_ended(hass, freezer):
    """A failure after a rejected key -- a refresh by hand while the
    connection is down, say -- does not bring the last data back."""
    probe = _Probe(hass, 1, ConfigEntryAuthFailed(), F)
    await _run(probe, freezer)
    assert probe.data_available is False


async def test_a_rejected_key_after_failures_tells_the_listeners(hass, freezer):
    probe = _Probe(hass, 1, F, ConfigEntryAuthFailed())
    seen = _listen(probe)
    await _run(probe, freezer)
    assert seen[-1] is False


async def test_a_rejected_key_after_a_cancelled_refresh_tells_the_listeners(hass, freezer):
    """Home Assistant 2026.9 takes a refresh cancelled while under way for a
    failed one, though it never gets to the tolerance -- and after a failure
    it tells the listeners of no failure. So when the key is rejected at the
    next refresh, the tolerance tells them itself: the entities are
    unavailable."""
    probe = _Probe(hass, 1, _HANG, ConfigEntryAuthFailed())
    entity = TolerantEntity(probe)
    seen = _listen(probe)
    await probe.async_refresh()
    await _cancel_a_refresh(probe)
    await _refresh(probe, freezer)
    assert entity.available is False
    assert seen == [True, False]


async def test_a_failed_refresh_that_replaces_the_data_tells_the_listeners(hass, freezer):
    """A subclass may replace the data in a refresh that fails, to leave out
    an item whose own failure the refresh confirms. After a failure Home
    Assistant tells the listeners nothing, so the tolerance tells them."""
    probe = _Probe(hass, 1, _down(), _Replaced(0))
    seen = _listen(probe)
    await _run(probe, freezer)
    assert probe.data == 0
    assert seen == [True, True, True]


@pytest.mark.parametrize(
    ("failure", "told"),
    [(_Replaced(0), [True, True]), (ConfigEntryAuthFailed(), [True, False])],
    ids=["data_replaced", "key_rejected"],
)
async def test_a_failure_right_after_a_success_is_told_to_the_listeners_once(
    hass, freezer, failure, told
):
    """Home Assistant tells the listeners of a failure that follows a success
    itself -- the data replaced, or the failure confirmed at once by a
    rejected key: the tolerance does not tell them again."""
    probe = _Probe(hass, 1, failure)
    seen = _listen(probe)
    await _run(probe, freezer)
    assert seen == told


async def test_without_data_nothing_is_available(hass, freezer):
    """A failed first refresh leaves nothing to show."""
    probe = _Probe(hass, F)
    await _run(probe, freezer)
    assert probe.data is None
    assert probe.data_available is False


async def test_one_warning_and_one_notice_per_outage(hass, freezer, caplog):
    """Failures go on after the confirmation: each outage is warned about,
    and told to the listeners, once -- and a new outage after a success
    again."""
    probe = _Probe(hass, 1, F, F, F, F, F, 2, F, F, F)
    seen = _listen(probe)
    with caplog.at_level(logging.WARNING):
        await _run(probe, freezer)
    warned = _tolerance_records(caplog)
    assert [record.levelno for record in warned] == [logging.WARNING] * 2
    assert all(
        record.getMessage().startswith("probe: 3 refreshes in a row failed")
        for record in warned
    )
    assert seen.count(False) == 2


async def test_no_tolerance_warning_for_a_rejected_key(hass, freezer, caplog):
    """A rejected key is no outage to warn about: Home Assistant starts the
    reauth dialog for it."""
    probe = _Probe(hass, 1, ConfigEntryAuthFailed())
    with caplog.at_level(logging.WARNING):
        await _run(probe, freezer)
    assert _tolerance_records(caplog) == []


_KEY_REJECTED = (
    "probe: the API key was rejected; its sensors are unavailable until a new key is entered"
)


@pytest.mark.parametrize("failures", [1, 3], ids=["within_the_tolerance", "after_its_end"])
async def test_a_key_rejected_after_a_failure_is_warned_about_once(
    hass, freezer, caplog, failures
):
    """Home Assistant logs a rejected key only when the refresh before it
    succeeded. Rejected after a failure -- the outage confirmed or not --
    the key is warned about by the tolerance, once: not again when it is
    rejected at a later refresh. Nothing of the key, no traceback."""
    probe = _Probe(
        hass, 1, *[_down() for _ in range(failures)],
        ConfigEntryAuthFailed(), _down(), ConfigEntryAuthFailed(),
    )
    with caplog.at_level(logging.WARNING):
        await _run(probe, freezer)
    [record] = _rejection_records(caplog)
    assert (record.levelno, record.getMessage(), record.exc_info) == (
        logging.WARNING, _KEY_REJECTED, None
    )


async def test_a_key_rejected_in_a_later_outage_is_warned_about_again(
    hass, freezer, caplog
):
    """A success in between ends the first outage: the key rejected in the
    next one is warned about again."""
    probe = _Probe(
        hass, 1, _down(), ConfigEntryAuthFailed(), 2, _down(), ConfigEntryAuthFailed()
    )
    with caplog.at_level(logging.WARNING):
        await _run(probe, freezer)
    assert [record.getMessage() for record in _rejection_records(caplog)] == [
        _KEY_REJECTED
    ] * 2


async def test_a_key_rejected_after_a_success_is_left_to_home_assistant(
    hass, freezer, caplog
):
    """Home Assistant logs it itself, at ERROR -- and nobody logs it again
    when the key is rejected at the next refresh."""
    probe = _Probe(hass, 1, ConfigEntryAuthFailed(), ConfigEntryAuthFailed())
    with caplog.at_level(logging.WARNING):
        await _run(probe, freezer)
    assert _rejection_records(caplog) == []
    assert [
        record.levelno for record in caplog.records
        if record.getMessage().startswith("Authentication failed while fetching probe data")
    ] == [logging.ERROR]


async def test_a_slow_first_failure_does_not_prolong_it(hass, freezer):
    """The streak is timed by when each refresh was asked for, not by when
    its answer arrived. Asked for at R, R + 5 min and R + 10 min, three
    failures confirm the outage; timed by their answers -- the first one
    50 s late -- they would span 9 min 10 s, and confirm nothing."""
    probe = _Probe(hass, 1, _late(freezer, F), F, F)
    await probe.async_refresh()
    await _refresh(probe, freezer)  # asked for at R, answered at R + 50 s
    await _refresh(probe, freezer, _REGULAR - _LATE)  # R + 5 min
    await _refresh(probe, freezer)  # R + 10 min
    assert probe.data_available is False


async def test_the_fetch_is_handed_the_time_its_refresh_was_asked_for(hass, freezer):
    probe = _Probe(hass, 1)
    asked = dt_util.utcnow()
    await probe.async_refresh()
    assert probe.asked == [asked]


async def test_an_entity_follows_its_coordinator(hass, freezer):
    """Not the outcome of the last refresh, which CoordinatorEntity follows:
    after two failures the entity is still available."""
    probe = _Probe(hass, 1, F, F, F)
    entity = TolerantEntity(probe)
    for _ in range(3):
        await _refresh(probe, freezer)
    assert (entity.available, probe.data_available) == (True, True)
    await _refresh(probe, freezer)
    assert (entity.available, probe.data_available) == (False, False)
