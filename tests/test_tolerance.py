"""Tests for the coordinators whose sensors keep their last data through
short outages, and the entities that follow them (tolerance.py)."""
from datetime import timedelta
import logging

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


class _Probe(TolerantCoordinator[int]):
    """Answers from a script: an int is the data, an exception is raised. A
    callable is called first and answers with what it returns -- time can
    pass in it while the answer is on its way. Every fetch records the time
    its refresh was asked for."""

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
