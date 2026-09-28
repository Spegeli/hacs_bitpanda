"""Tests for the portfolio history coordinator."""
import asyncio
from contextlib import contextmanager
from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
)
from custom_components.bitpanda.const import (
    API_BASE_URL,
    PORTFOLIO_TIMEFRAMES,
    PORTFOLIO_UPDATE_INTERVAL,
)
from custom_components.bitpanda.portfolio_coordinator import (
    HistoryCoordinator,
    collect_returns,
)
from custom_components.bitpanda.portfolio_model import PortfolioReturns


async def test_collect_returns_one_entry_per_timeframe():
    with mock_aiohttp_client() as mocker:
        for index, timeframe in enumerate(PORTFOLIO_TIMEFRAMES):
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json={"data": {"datapoints": [],
                                "return_percentage": float(index)}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert result == PortfolioReturns(
        values={tf: float(i) for i, tf in enumerate(PORTFOLIO_TIMEFRAMES)}, failed=frozenset()
    )


async def test_collect_returns_asks_in_the_portfolio_currency():
    """A Portfolio kept in USD gets its returns measured in USD: every
    timeframe's request names the Portfolio currency."""
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}"
                "&equivalent_currency_id=uuid-usd",
                json={"data": {"return_percentage": 1.0}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            await collect_returns(client, "uuid-usd")
    assert [call[1].query_string for call in mocker.mock_calls] == [
        f"timeframe={timeframe}&equivalent_currency_id=uuid-usd"
        for timeframe in PORTFOLIO_TIMEFRAMES
    ]


async def test_collect_returns_skips_a_failing_timeframe():
    """One bad window must not lose the other four -- and is told apart from
    a timeframe answered without a figure: its own request failed."""
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            if timeframe == "YEAR":
                mocker.get(
                    f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                    status=500,
                )
            else:
                mocker.get(
                    f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                    json={"data": {"return_percentage": 1.0}},
                )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert "YEAR" not in result.values
    assert len(result.values) == len(PORTFOLIO_TIMEFRAMES) - 1
    assert result.failed == {"YEAR"}


async def test_collect_returns_raises_when_every_timeframe_fails():
    """A dead endpoint must not look like an empty result."""
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                status=500,
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(UpdateFailed) as excinfo:
                await collect_returns(client, None)
    assert (excinfo.value.translation_domain, excinfo.value.translation_key) == (
        "bitpanda", "history_unavailable"
    )


async def test_collect_returns_drops_a_boolean_percentage():
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            payload = {"data": {"return_percentage":
                                True if timeframe == "DAY" else 1.5}}
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json=payload,
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert "DAY" not in result.values
    assert len(result.values) == len(PORTFOLIO_TIMEFRAMES) - 1
    # Answered, just without a usable figure: not a failed request.
    assert result.failed == frozenset()


async def test_collect_returns_parses_a_numeric_string_percentage():
    """The API now sends return_percentage as a JSON string; numbers must
    still work too, so each timeframe here uses a different value shape."""
    values = {
        "DAY": "0.73",
        "WEEK": " 7.22 ",
        "MONTH": 1.5,
        "SIX_MONTH": 2,
        "YEAR": "3.14",
    }
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json={"data": {"return_percentage": values[timeframe]}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert result.values == {
        "DAY": 0.73,
        "WEEK": 7.22,
        "MONTH": 1.5,
        "SIX_MONTH": 2.0,
        "YEAR": 3.14,
    }


async def test_collect_returns_drops_unparsable_or_non_finite_percentage_strings():
    """A string must parse to a finite number or the timeframe is dropped,
    same as today's rule for every other unusable value."""
    values = {
        "DAY": "n/a",
        "WEEK": "nan",
        "MONTH": "inf",
        "SIX_MONTH": 1.0,
        "YEAR": 1.0,
    }
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json={"data": {"return_percentage": values[timeframe]}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert result == PortfolioReturns(
        values={"SIX_MONTH": 1.0, "YEAR": 1.0}, failed=frozenset()
    )


class _Returns:
    """Fake API client answering each timeframe with its own value."""

    def __init__(self, values):
        self._values = values

    async def async_get_portfolio_history(self, *, timeframe, equivalent_currency_id=None):
        return {"return_percentage": self._values[timeframe]}


async def test_collect_returns_drops_non_finite_numbers():
    """A JSON number goes through the same finite check as a numeric string:
    Python's json module reads the literals Infinity and NaN as floats."""
    values = {
        "DAY": float("inf"),
        "WEEK": float("-inf"),
        "MONTH": float("nan"),
        "SIX_MONTH": 1.0,
        "YEAR": 2,
    }
    assert await collect_returns(_Returns(values), None) == PortfolioReturns(
        values={"SIX_MONTH": 1.0, "YEAR": 2.0}, failed=frozenset()
    )


async def test_collect_returns_is_quiet_when_history_is_genuinely_empty():
    """All five answer, none carries a usable value. Not an outage."""
    with mock_aiohttp_client() as mocker:
        for timeframe in PORTFOLIO_TIMEFRAMES:
            mocker.get(
                f"{API_BASE_URL}/portfolio-history?timeframe={timeframe}",
                json={"data": {"datapoints": [],
                                "return_percentage": None}},
            )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await collect_returns(client, None)
    assert result == PortfolioReturns(values={}, failed=frozenset())


async def test_collect_returns_reraises_auth_error_instead_of_counting_it():
    """An auth error must propagate immediately, not be treated as one of
    five failed timeframes -- otherwise a 401 on every timeframe reads as
    "No portfolio history could be fetched" (UpdateFailed) instead of the
    BitpandaAuthError the coordinator needs to start reauth.

    Only the first timeframe is registered, with a 401. If the
    implementation kept looping past it instead of re-raising, the next
    request would hit an unregistered URL and this test would fail for a
    different reason, which is exactly the point of leaving it unregistered
    (see test_api_scopes.py for the same technique).
    """
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/portfolio-history?"
            f"timeframe={PORTFOLIO_TIMEFRAMES[0]}",
            status=401,
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaAuthError):
                await collect_returns(client, None)


# ---------------------------------------------------------------------------
# HistoryCoordinator._async_update_data
#
# DataUpdateCoordinator.__init__ only stores `hass`, so hass=None/entry=None
# is enough to drive _async_update_data() directly.
# ---------------------------------------------------------------------------


class _FakeClient:
    """Fake API client whose async_get_portfolio_history always fails alike."""

    def __init__(self, error):
        self._error = error

    async def async_get_portfolio_history(
        self, *, timeframe, equivalent_currency_id=None
    ):
        raise self._error


async def test_history_coordinator_raises_config_entry_auth_failed_on_401():
    client = _FakeClient(BitpandaAuthError("Unauthorized for /portfolio-history"))
    coordinator = HistoryCoordinator(
        hass=None, entry=None, client=client, currency_id=None
    )

    with pytest.raises(ConfigEntryAuthFailed) as excinfo:
        await coordinator._async_update_data()
    assert (excinfo.value.translation_domain, excinfo.value.translation_key) == (
        "bitpanda", "api_key_rejected"
    )


class _Recording:
    """Fake API client that answers every timeframe and records the currency
    each request asked in."""

    def __init__(self):
        self.currency_ids = []

    async def async_get_portfolio_history(self, *, timeframe, equivalent_currency_id=None):
        self.currency_ids.append(equivalent_currency_id)
        return {"return_percentage": 1.0}


async def test_history_refresh_asks_in_the_portfolio_currency():
    client = _Recording()
    coordinator = HistoryCoordinator(
        hass=None, entry=None, client=client, currency_id="uuid-usd"
    )
    await coordinator._async_update_data()
    assert client.currency_ids == ["uuid-usd"] * len(PORTFOLIO_TIMEFRAMES)


# ---------------------------------------------------------------------------
# HistoryCoordinator.async_refresh: a timeframe whose own request fails
#
# With `hass` a refresh keeps its data and counts its failures
# (tolerance.py). Nothing listens, so no refresh is scheduled: each test
# moves the clock and refreshes by itself.
# ---------------------------------------------------------------------------

# A scripted request that fails.
_DOWN = "down"


class _Scripted:
    """Fake API client scripted per timeframe: each request takes the next
    item of its timeframe's script -- a return, or _DOWN for a request that
    fails. A timeframe without a script answers 1.0."""

    def __init__(self, **scripts):
        self._scripts = {timeframe: list(script) for timeframe, script in scripts.items()}

    async def async_get_portfolio_history(self, *, timeframe, equivalent_currency_id=None):
        item = self._scripts[timeframe].pop(0) if timeframe in self._scripts else 1.0
        if item == _DOWN:
            raise BitpandaApiError(
                "HTTP 503 from /portfolio-history",
                kind="http_status", path="/portfolio-history", status=503,
            )
        return {"return_percentage": item}


def _scripted_history(hass, **scripts) -> HistoryCoordinator:
    return HistoryCoordinator(hass, entry=None, client=_Scripted(**scripts), currency_id=None)


async def _refresh(coordinator, freezer, pace=PORTFOLIO_UPDATE_INTERVAL) -> None:
    """One refresh, `pace` after the one before."""
    freezer.tick(pace)
    await coordinator.async_refresh()


@contextmanager
def _listening(coordinator):
    """The data the coordinator's listeners found each time it told them,
    while the block runs. A listener makes the coordinator schedule its next
    refresh; leaving the block removes the listener, and with it that timer,
    which Home Assistant's test harness would fail the test for."""
    seen: list[PortfolioReturns] = []
    unsubscribe = coordinator.async_add_listener(lambda: seen.append(coordinator.data))
    try:
        yield seen
    finally:
        unsubscribe()


async def test_the_coordinator_carries_a_failing_timeframe(hass, freezer):
    """The week answers, then its own requests fail while the others answer:
    its last return stays through two refreshes at the regular pace, and
    the third confirms the failure. Its next answer brings it back."""
    coordinator = _scripted_history(hass, WEEK=[2.0, _DOWN, _DOWN, _DOWN, 3.0])
    await coordinator.async_refresh()
    for _ in range(2):
        await _refresh(coordinator, freezer)
        assert coordinator.data.values["WEEK"] == 2.0
        assert "WEEK" not in coordinator.data.failed
    await _refresh(coordinator, freezer)
    assert "WEEK" in coordinator.data.failed
    assert "WEEK" not in coordinator.data.values
    await _refresh(coordinator, freezer)
    assert coordinator.data.values["WEEK"] == 3.0
    assert "WEEK" not in coordinator.data.failed


async def test_a_history_refresh_failing_as_a_whole_counts_for_every_timeframe(
    hass, freezer
):
    """The week fails, then every request of a refresh fails -- the refresh
    fails, its data unchanged (tolerance.py) -- then the week fails again:
    three refreshes without a fresh return for the week, two intervals from
    the first to the last, confirm its failure."""
    scripts = {timeframe: [1.0, 1.0, _DOWN, 1.0] for timeframe in PORTFOLIO_TIMEFRAMES}
    scripts["WEEK"] = [2.0, _DOWN, _DOWN, _DOWN]
    coordinator = _scripted_history(hass, **scripts)
    await coordinator.async_refresh()
    await _refresh(coordinator, freezer)
    carried = coordinator.data

    await _refresh(coordinator, freezer)
    assert coordinator.last_update_success is False
    assert coordinator.data is carried

    await _refresh(coordinator, freezer)
    assert coordinator.last_update_success is True
    assert "WEEK" in coordinator.data.failed
    assert "WEEK" not in coordinator.data.values


async def test_a_refresh_failing_as_a_whole_counts_once_for_each_timeframe(hass, freezer):
    """Two refreshes fail as a whole, ten minutes apart -- a refresh was
    missed between them. Each counts once for every timeframe, and two
    failures confirm nothing, however far apart: the returns are still
    carried."""
    scripts = {timeframe: [1.0, _DOWN, _DOWN] for timeframe in PORTFOLIO_TIMEFRAMES}
    coordinator = _scripted_history(hass, **scripts)
    await coordinator.async_refresh()
    carried = coordinator.data
    await _refresh(coordinator, freezer)
    await _refresh(coordinator, freezer, pace=2 * PORTFOLIO_UPDATE_INTERVAL)
    assert coordinator.data is carried


async def test_a_first_refresh_failing_as_a_whole_leaves_nothing_to_show(hass):
    """No last return to carry: no data, nothing available -- yet the
    refresh counts for every timeframe."""
    coordinator = _scripted_history(
        hass, **{timeframe: [_DOWN] for timeframe in PORTFOLIO_TIMEFRAMES}
    )
    await coordinator.async_refresh()
    assert (coordinator.data, coordinator.data_available) == (None, False)
    assert coordinator.failing_timeframes == set(PORTFOLIO_TIMEFRAMES)


async def test_a_whole_failure_that_confirms_a_carried_timeframe_fails_it_at_once(
    hass, freezer
):
    """The week's own request fails while the others answer: its last return
    is carried. Then two refreshes fail as a whole, and count for the week
    too: the second confirms its failure, ten minutes after its first, while
    the whole update's failure is not confirmed yet. The week is failed in
    that very refresh, the others still carried, and the listeners are told
    -- after a failure Home Assistant would not tell them."""
    scripts = {timeframe: [1.0, 1.0, _DOWN, _DOWN] for timeframe in PORTFOLIO_TIMEFRAMES}
    scripts["WEEK"] = [2.0, _DOWN, _DOWN, _DOWN]
    coordinator = _scripted_history(hass, **scripts)
    carried = PortfolioReturns(
        values={"DAY": 1.0, "WEEK": 2.0, "MONTH": 1.0, "SIX_MONTH": 1.0, "YEAR": 1.0}
    )
    week_failed = PortfolioReturns(
        values={"DAY": 1.0, "MONTH": 1.0, "SIX_MONTH": 1.0, "YEAR": 1.0},
        failed=frozenset({"WEEK"}),
    )
    with _listening(coordinator) as seen:
        await coordinator.async_refresh()
        for _ in range(3):
            await _refresh(coordinator, freezer)
    assert (coordinator.data, coordinator.data_available) == (week_failed, True)
    assert seen == [carried] * 3 + [week_failed]


async def test_a_timeframe_still_failing_after_a_confirmed_outage_is_unavailable_at_once(
    hass, freezer
):
    """Three refreshes in a row fail as a whole, at the regular pace: the
    outage is confirmed. At the next refresh the others answer and the week
    fails: it has had no fresh return for four refreshes, so its return from
    before the outage never comes back -- failed at once."""
    scripts = {timeframe: [1.0, *[_DOWN] * 3, 1.0] for timeframe in PORTFOLIO_TIMEFRAMES}
    scripts["WEEK"] = [2.0, *[_DOWN] * 4]
    coordinator = _scripted_history(hass, **scripts)
    await coordinator.async_refresh()
    for _ in range(3):
        await _refresh(coordinator, freezer)
    assert coordinator.data_available is False

    await _refresh(coordinator, freezer)
    assert coordinator.data == PortfolioReturns(
        values={"DAY": 1.0, "MONTH": 1.0, "SIX_MONTH": 1.0, "YEAR": 1.0},
        failed=frozenset({"WEEK"}),
    )


async def test_the_failing_timeframes_are_those_whose_requests_fail_now(hass, freezer):
    """What the diagnostics report as failed: every timeframe whose requests
    fail now -- the week while it is carried over, all five after a refresh
    that fails as a whole -- and none once they answer again."""
    scripts = {timeframe: [1.0, 1.0, _DOWN, 1.0] for timeframe in PORTFOLIO_TIMEFRAMES}
    scripts["WEEK"] = [2.0, _DOWN, _DOWN, 3.0]
    coordinator = _scripted_history(hass, **scripts)
    await coordinator.async_refresh()
    seen = [coordinator.failing_timeframes]
    for _ in range(3):
        await _refresh(coordinator, freezer)
        seen.append(coordinator.failing_timeframes)
    assert seen == [set(), {"WEEK"}, set(PORTFOLIO_TIMEFRAMES), set()]


async def test_quick_refreshes_never_confirm_a_timeframes_failure_sooner(hass, freezer):
    """Five failures of the week within two minutes -- refreshes asked for
    by hand (homeassistant.update_entity), where the regular pace would have
    brought one: it keeps its last return."""
    coordinator = _scripted_history(hass, WEEK=[2.0, *[_DOWN] * 5])
    await coordinator.async_refresh()
    for _ in range(5):
        await _refresh(coordinator, freezer, pace=timedelta(seconds=20))
    assert coordinator.data.values["WEEK"] == 2.0
    assert "WEEK" not in coordinator.data.failed
