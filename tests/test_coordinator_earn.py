"""Tests for reward aggregation."""
import asyncio
import base64
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
)
from custom_components.bitpanda.const import API_BASE_URL, DOMAIN
from custom_components.bitpanda.portfolio_coordinator import RewardsCoordinator
from custom_components.bitpanda.portfolio_model import Holding, PortfolioData, sum_rewards
from custom_components.bitpanda.portfolio_store import (
    PortfolioStore,
    async_get_portfolio_store,
    async_remove_portfolio_store,
)
from custom_components.bitpanda.portfolio_sensor import StakingSensor

from tests.conftest import async_settle


def _reward(asset_id, gross, fee, credited_at, owner="staking-service"):
    return {
        "operation_id": f"op-{credited_at}-{asset_id}",
        "operation_type": "reward",
        "transactions": [
            {
                "asset_id": asset_id,
                "wallet_owner": owner,
                "asset_amount": {"value": gross},
                "fee_amount": {"value": fee},
                "credited_at": credited_at,
            }
        ],
    }


# ---------------------------------------------------------------------------
# RewardsCoordinator._async_update_data
# ---------------------------------------------------------------------------


class _FakeClient:
    """Fake API client with a controllable async_get_operations; `requests`
    holds the `from_ts` of each call, None for the whole history."""

    def __init__(self, operations=None, error=None):
        self._operations = operations or []
        self._error = error
        self.calls = 0
        self.requests = []

    async def async_get_operations(self, *, from_ts=None, to_ts=None):
        self.calls += 1
        self.requests.append(from_ts)
        if self._error is not None:
            raise self._error
        return self._operations


async def _history(hass):
    """The operations section of a Portfolio's file, as a start loads it."""
    store = PortfolioStore(hass, "eid")
    await store.async_load()
    return store.operations


async def test_rewards_coordinator_returns_totals_from_operations(hass):
    client = _FakeClient(
        operations=[_reward("vsn", "1", "0", "2026-09-22T17:16:35Z")]
    )
    coordinator = RewardsCoordinator(hass, None, client, await _history(hass))

    data = await coordinator._async_update_data()

    assert data["vsn"].gross == 1.0


async def test_the_rewards_coordinator_calls_back_after_each_successful_refresh_only(hass):
    """The announcer's call (announcements.RewardAnnouncer) comes after a
    refresh that succeeded, never after a failed one."""
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": "key", "currency": "EUR"})
    entry.add_to_hass(hass)
    client = _FakeClient(operations=[_reward("vsn", "1", "0", "2026-09-22T17:16:35Z")])
    coordinator = RewardsCoordinator(hass, entry, client, await _history(hass))
    coordinator.on_refreshed = Mock()

    await coordinator.async_refresh()
    assert coordinator.on_refreshed.call_count == 1

    client._error = BitpandaApiError("down", path="/operations")
    await coordinator.async_refresh()
    assert coordinator.on_refreshed.call_count == 1


async def test_the_callback_schedules_no_refresh_without_a_listener(hass, freezer):
    """The call is no listener: without a Staking sensor listening, the
    whole history is not read again an hour later (issue #13)."""
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": "key", "currency": "EUR"})
    entry.add_to_hass(hass)
    client = _FakeClient(operations=[_reward("vsn", "1", "0", "2026-09-22T17:16:35Z")])
    coordinator = RewardsCoordinator(hass, entry, client, await _history(hass))
    coordinator.on_refreshed = Mock()

    await coordinator.async_refresh()
    freezer.tick(timedelta(hours=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert (client.calls, coordinator.on_refreshed.call_count) == (1, 1)


async def test_rewards_coordinator_raises_config_entry_auth_failed_on_401(hass):
    """Setup requires every scope, so a 401 here means the key
    expired, was revoked, or predates that requirement (a migrated legacy
    key). Every case is answered by a new key, so this must raise
    ConfigEntryAuthFailed and let Home Assistant start the reauth flow --
    not degrade silently, which is what this coordinator used to do.
    """
    client = _FakeClient(error=BitpandaAuthError("Unauthorized for /operations"))
    coordinator = RewardsCoordinator(hass, None, client, await _history(hass))

    with pytest.raises(ConfigEntryAuthFailed) as excinfo:
        await coordinator._async_update_data()
    assert (excinfo.value.translation_domain, excinfo.value.translation_key) == (
        "bitpanda", "api_key_rejected"
    )


async def test_rewards_coordinator_raises_update_failed_on_other_errors(hass):
    client = _FakeClient(
        error=BitpandaApiError(
            "/operations repeated a page cursor; its listing is incomplete",
            kind="incomplete_listing",
            path="/operations",
        )
    )
    coordinator = RewardsCoordinator(hass, None, client, await _history(hass))

    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert (
        excinfo.value.translation_domain,
        excinfo.value.translation_key,
        excinfo.value.translation_placeholders,
    ) == ("bitpanda", "update_failed_incomplete_listing", {"path": "/operations"})


# ---------------------------------------------------------------------------
# A paging failure reaches the wallet sensor as absent or stale rewards --
# never as totals recounted over whichever pages happened to arrive. Driven
# through the real client, the real coordinator refresh and the real sensor.
# ---------------------------------------------------------------------------

# Carries milliseconds already, so the /operations cursor workaround cannot
# repair a server that keeps handing it back: the pager must raise.
_REPEATING_CURSOR = base64.b64encode(b"2026-09-09T18:31:22.080Z").decode("ascii")


def _register_repeating_operations(mocker, operations: list[dict]) -> None:
    page = {
        "data": operations,
        "next_cursor": _REPEATING_CURSOR,
        "has_next_page": True,
    }
    mocker.get(f"{API_BASE_URL}/operations?cursor={_REPEATING_CURSOR}", json=page)
    mocker.get(f"{API_BASE_URL}/operations", json=page)


class _Coordinator:
    def __init__(self, data):
        self.data = data
        self.last_update_success = True
        self.data_available = True


def _vsn_staking_sensor(rewards) -> StakingSensor:
    portfolio = _Coordinator(
        PortfolioData(
            holdings={"vsn": Holding(asset_id="vsn", balance=100.0, available=0.0, value=4.0)}
        )
    )
    return StakingSensor(
        portfolio, _Coordinator(None), rewards, "entry1", "EUR",
        {"id": "vsn", "symbol": "VSN"},
    )


@pytest.mark.timeout(10)
async def test_rewards_paging_failure_leaves_rewards_attributes_absent(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": "key", "currency": "EUR"})
    entry.add_to_hass(hass)

    with mock_aiohttp_client() as mocker:
        _register_repeating_operations(
            mocker, [_reward("vsn", "20.68994769", "4.13798954", "2026-09-22T17:16:35Z")]
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            rewards = RewardsCoordinator(
                hass, entry, BitpandaApiClient("key", session), await _history(hass)
            )
            await rewards.async_refresh()

    assert rewards.last_update_success is False
    assert rewards.data is None
    attrs = _vsn_staking_sensor(rewards).extra_state_attributes
    assert attrs["units"] == 100.0
    assert not [key for key in attrs if key.startswith("rewards_")]


@pytest.mark.timeout(10)
async def test_rewards_paging_failure_keeps_the_last_complete_totals(hass):
    """Stale is honest; a recount over a partial history is not."""
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": "key", "currency": "EUR"})
    entry.add_to_hass(hass)
    older = _reward("vsn", "20.67399483", "4.13479897", "2026-09-15T17:16:25Z")
    newer = _reward("vsn", "20.68994769", "4.13798954", "2026-09-22T17:16:35Z")

    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/operations",
            json={"data": [newer, older], "has_next_page": False},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            rewards = RewardsCoordinator(
                hass, entry, BitpandaApiClient("key", session), await _history(hass)
            )
            await rewards.async_refresh()
            assert rewards.last_update_success is True
            assert rewards.data["vsn"].count == 2

            # Next hour the listing breaks down after one page holding only
            # the newer reward.
            mocker.clear_requests()
            _register_repeating_operations(mocker, [newer])
            await rewards.async_refresh()

    assert rewards.last_update_success is False
    attrs = _vsn_staking_sensor(rewards).extra_state_attributes
    assert attrs["rewards_count"] == 2
    assert abs(attrs["rewards_gross"] - (20.67399483 + 20.68994769)) < 1e-8


# ---------------------------------------------------------------------------
# Only what is new: the whole history first, then from the newest time seen
# less a day; the whole again once a week, for a kind not covered yet, and
# after a new key (portfolio_store.OperationsHistory).
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


def _swap(operation_id, *credited):
    """An operation of another kind, its legs credited at `credited`."""
    return {
        "operation_id": operation_id,
        "operation_type": "swap",
        "transactions": [{"credited_at": time, "wallet_owner": "shared-default"} for time in credited],
    }


async def test_without_a_section_the_whole_history_is_read_and_kept(hass, freezer):
    """The newest time is that of any operation -- a swap's later leg here
    -- and the ids kept are those of the day before it."""
    freezer.move_to(_NOW)
    operations = [
        _swap("swap", "2026-10-13T09:00:00Z", "2026-10-13T16:48:00.512Z"),
        _reward("vsn", "10", "2", "2026-10-13T08:00:00Z"),
        _reward("vsn", "20", "4", "2026-10-06T17:07:32Z"),
    ]
    client = _FakeClient(operations=operations)
    history = await _history(hass)
    coordinator = RewardsCoordinator(hass, None, client, history)

    data = await coordinator._async_update_data()

    assert client.requests == [None]
    assert data == sum_rewards(operations)
    assert history.staking == data
    assert history.anchor == "2026-10-13T16:48:00.512Z"
    assert history.recent_ids == {
        "swap": "2026-10-13T16:48:00.512Z",
        "op-2026-10-13T08:00:00Z-vsn": "2026-10-13T08:00:00Z",
    }
    assert history.kinds == ["staking"]
    assert history.full_read_at == _NOW


def _read_before(history, *, read_at=_NOW - timedelta(days=1), kinds=("staking",)):
    """A section as a full read left it: one payout, its id the recent one."""
    earlier = _reward("vsn", "10", "2", "2026-10-13T16:48:00.512Z")
    history.replace(
        staking=sum_rewards([earlier]),
        anchor="2026-10-13T16:48:00.512Z",
        recent_ids={earlier["operation_id"]: "2026-10-13T16:48:00.512Z"},
        kinds=kinds,
        full_read_at=read_at,
    )
    return earlier


async def test_then_only_what_is_new_is_read_and_counted_once(hass, freezer):
    """From the newest time less a day, to the second; the payout read
    before comes again and counts once, the new one adds to the totals."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    earlier = _read_before(history)
    newer = _reward("vsn", "1", "0.2", "2026-10-14T09:00:00Z")
    client = _FakeClient(operations=[newer, earlier])
    coordinator = RewardsCoordinator(hass, None, client, history)

    data = await coordinator._async_update_data()

    assert client.requests == ["2026-10-12T16:48:00Z"]
    assert data == sum_rewards([earlier, newer])
    assert history.staking == data
    assert history.anchor == "2026-10-14T09:00:00Z"
    assert history.recent_ids == {
        earlier["operation_id"]: "2026-10-13T16:48:00.512Z",
        newer["operation_id"]: "2026-10-14T09:00:00Z",
    }
    assert history.full_read_at == _NOW - timedelta(days=1)


async def test_an_anchor_that_is_no_time_has_the_whole_history_read(hass, freezer):
    """Nothing to begin a read from: the whole history, as without a
    section."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    earlier = _read_before(history)
    history.anchor = "not a time"
    client = _FakeClient(operations=[earlier])
    data = await RewardsCoordinator(hass, None, client, history)._async_update_data()
    assert client.requests == [None]
    assert data == sum_rewards([earlier])
    assert history.anchor == "2026-10-13T16:48:00.512Z"
    assert history.full_read_at == _NOW


async def test_operations_before_the_window_are_never_counted_again(hass, freezer):
    """Bitpanda answers `from` with what came since; should it list older
    operations all the same, they are not counted again -- a payout booked
    late with a time more than a day back waits for the weekly whole read."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    earlier = _read_before(history)
    older = _reward("vsn", "5", "1", "2026-10-06T17:07:32Z")
    newer = _reward("vsn", "1", "0.2", "2026-10-14T09:00:00Z")
    client = _FakeClient(operations=[newer, earlier, older])
    data = await RewardsCoordinator(hass, None, client, history)._async_update_data()
    assert data == sum_rewards([earlier, newer])
    assert older["operation_id"] not in history.recent_ids


async def test_only_the_ids_of_the_last_day_before_the_newest_time_are_kept(hass, freezer):
    """A payout more than a day before the newest time can come no more:
    its id goes."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    _read_before(history)
    newer = _reward("vsn", "1", "0.2", "2026-10-14T20:00:00Z")
    client = _FakeClient(operations=[newer])
    await RewardsCoordinator(hass, None, client, history)._async_update_data()
    assert history.recent_ids == {newer["operation_id"]: "2026-10-14T20:00:00Z"}


@pytest.mark.parametrize(
    "credited", ["2026-10-12T16:48:00.200Z", "2026-10-12T16:48:00Z"], ids=["fraction", "whole_second"]
)
async def test_a_payout_in_the_second_the_read_begins_with_counts_once(hass, freezer, credited):
    """Bitpanda's `from` takes whole seconds: a read begins at the newest
    time less a day, rounded down. A payout of the day before within that
    second, ahead of the newest time's fraction, comes again -- counted
    already, its id must still be kept."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    day_before = _reward("vsn", "5", "1", credited)
    newest = _reward("vsn", "10", "2", "2026-10-13T16:48:00.512Z")
    client = _FakeClient(operations=[newest, day_before])
    coordinator = RewardsCoordinator(hass, None, client, history)
    await coordinator._async_update_data()
    data = await coordinator._async_update_data()
    assert client.requests == [None, "2026-10-12T16:48:00Z"]
    assert data == sum_rewards([newest, day_before])
    assert day_before["operation_id"] in history.recent_ids


@pytest.mark.parametrize(
    ("read_at", "kinds", "whole"),
    [
        (_NOW - timedelta(days=7), ("staking",), True),
        (_NOW - timedelta(days=6, hours=23), ("staking",), False),
        (_NOW - timedelta(days=1), (), True),
    ],
    ids=["a_week_after", "within_the_week", "a_kind_not_covered"],
)
async def test_the_whole_history_again_once_a_week_and_for_a_kind_not_covered(
    hass, freezer, read_at, kinds, whole
):
    freezer.move_to(_NOW)
    history = await _history(hass)
    earlier = _read_before(history, read_at=read_at, kinds=kinds)
    client = _FakeClient(operations=[earlier])
    await RewardsCoordinator(hass, None, client, history)._async_update_data()
    assert client.requests == ([None] if whole else ["2026-10-12T16:48:00Z"])
    assert history.full_read_at == (_NOW if whole else read_at)


async def test_a_read_keeps_only_the_kinds_it_evaluates(hass, freezer):
    """A section a later release wrote may list a kind this one does not
    evaluate, and a read here keeps only the totals it evaluates: it lists
    only those, so that release, back again, reads the whole history for its
    kind."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    earlier = _read_before(history, kinds=("staking", "dividends"))
    newer = _reward("vsn", "1", "0.2", "2026-10-14T09:00:00Z")
    client = _FakeClient(operations=[newer, earlier])
    await RewardsCoordinator(hass, None, client, history)._async_update_data()
    assert client.requests == ["2026-10-12T16:48:00Z"]
    assert history.kinds == ["staking"]


@pytest.mark.parametrize("error", [BitpandaApiError("down", path="/operations"), BitpandaAuthError("401")])
async def test_a_failed_read_leaves_what_was_read(hass, freezer, error):
    """Nothing read before changes, not even in place, and the next read
    asks from the same time."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    earlier = _read_before(history)
    client = _FakeClient(error=error)
    coordinator = RewardsCoordinator(hass, None, client, history)
    with pytest.raises((UpdateFailed, ConfigEntryAuthFailed)):
        await coordinator._async_update_data()
    assert history.staking == sum_rewards([earlier])
    assert history.anchor == "2026-10-13T16:48:00.512Z"
    assert history.recent_ids == {earlier["operation_id"]: "2026-10-13T16:48:00.512Z"}
    assert history.full_read_at == _NOW - timedelta(days=1)
    client._error = None
    client._operations = [earlier]
    assert await coordinator._async_update_data() == sum_rewards([earlier])
    assert client.requests == ["2026-10-12T16:48:00Z", "2026-10-12T16:48:00Z"]


async def test_what_was_read_before_shows_before_any_request(hass, freezer):
    """After a restart or a reload the totals are there at once."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    _read_before(history)
    client = _FakeClient()
    coordinator = RewardsCoordinator(hass, None, client, history)
    assert coordinator.data == history.staking
    assert client.calls == 0


class _HeldClient(_FakeClient):
    """A fake whose answers wait for `release`; `entered` is set once the
    first request is under way."""

    def __init__(self, operations):
        super().__init__(operations=operations)
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def async_get_operations(self, *, from_ts=None, to_ts=None):
        self.requests.append(from_ts)
        self.entered.set()
        await self.release.wait()
        return self._operations


async def test_a_read_asked_for_meanwhile_begins_once_the_one_under_way_has_ended(hass, freezer):
    """Before 2025.11 Home Assistant could run the hourly read while one a
    new Staking sensor asked for was under way. The second begins once the
    first has ended, from where it ended: begun at once, it would count the
    payouts again that the first one's newer time leaves out of the ids
    kept."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    earlier = _read_before(history)
    newer = _reward("vsn", "1", "0.2", "2026-10-14T20:00:00Z")
    client = _HeldClient(operations=[newer, earlier])
    coordinator = RewardsCoordinator(hass, None, client, history)
    first = asyncio.create_task(coordinator._async_update_data())
    await client.entered.wait()
    second = asyncio.create_task(coordinator._async_update_data())
    await async_settle()
    assert client.requests == ["2026-10-12T16:48:00Z"]
    client.release.set()
    await first
    assert await second == sum_rewards([earlier, newer])
    assert client.requests == ["2026-10-12T16:48:00Z", "2026-10-13T20:00:00Z"]
    assert history.staking == sum_rewards([earlier, newer])


@pytest.mark.parametrize("read_before", [True, False], ids=["new only", "whole history"])
async def test_a_read_that_ends_after_the_shutdown_writes_nothing_and_announces_nothing(
    hass, freezer, read_before
):
    """An unload shuts the coordinator down -- Home Assistant does it for
    every coordinator with a config entry -- while a read may be under way.
    One that ends after the shutdown keeps nothing of what it read (the
    entry's file may be about to go with the entry) and announces nothing:
    a read of what is new as one of the whole history."""
    freezer.move_to(_NOW)
    history = await _history(hass)
    earlier = _read_before(history) if read_before else _reward(
        "vsn", "10", "2", "2026-10-13T16:48:00.512Z"
    )
    before = history.staking
    newer = _reward("vsn", "1", "0.2", "2026-10-14T20:00:00Z")
    client = _HeldClient(operations=[newer, earlier])
    coordinator = RewardsCoordinator(hass, None, client, history)
    coordinator.on_refreshed = Mock()
    refresh = asyncio.create_task(coordinator.async_refresh())
    await client.entered.wait()
    await coordinator.async_shutdown()
    client.release.set()
    await refresh
    assert history.staking == before
    coordinator.on_refreshed.assert_not_called()


@pytest.mark.parametrize("read_before", [True, False], ids=["new only", "whole history"])
async def test_a_read_that_ends_after_the_portfolio_was_removed_brings_no_file_back(
    hass, hass_storage, freezer, read_before
):
    """Removing the Portfolio unloads it -- the coordinator shuts down --
    and then deletes its file (async_remove_entry). A read still under way
    that ends after that leaves no file behind, however long one waits."""
    freezer.move_to(_NOW)
    store = await async_get_portfolio_store(hass, "eid")
    history = store.operations
    earlier = _read_before(history) if read_before else _reward(
        "vsn", "10", "2", "2026-10-13T16:48:00.512Z"
    )
    newer = _reward("vsn", "1", "0.2", "2026-10-14T20:00:00Z")
    # What was read before is on disk, its save done: only the read under
    # way could write again.
    await _flushed(hass, freezer)
    assert ("bitpanda.portfolio.eid" in hass_storage) is read_before
    client = _HeldClient(operations=[newer, earlier])
    coordinator = RewardsCoordinator(hass, None, client, history)
    refresh = asyncio.create_task(coordinator.async_refresh())
    await client.entered.wait()
    await coordinator.async_shutdown()
    await async_remove_portfolio_store(hass, "eid")
    client.release.set()
    await refresh
    await _flushed(hass, freezer)
    assert "bitpanda.portfolio.eid" not in hass_storage


async def _flushed(hass, freezer) -> None:
    """Past the store's delayed save: a save asked for is written."""
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
