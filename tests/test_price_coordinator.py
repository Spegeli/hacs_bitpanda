"""Tests for the keyless ticker coordinator and the ECB coordinator."""
import asyncio
from contextlib import contextmanager
from datetime import timedelta
import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.ecb import EcbError, EcbRates
from custom_components.bitpanda.price_coordinator import (
    EcbCoordinator,
    TickerCoordinator,
    async_delete_price_interval_issue,
    async_report_price_interval,
    convert_price,
    price_interval,
)

from tests.conftest import assert_issue_texts_render, raised_issues

BTC = "b86c034b-efe3-11eb-b56f-0691764446a7"
SOL = "b86da33d-efe3-11eb-b56f-0691764446a7"
_TRACKED = {BTC: "Bitcoin (BTC)", SOL: "Solana (SOL)"}


# --- price_interval -----------------------------------------------------------


def test_interval_is_sixty_seconds_up_to_thirty_assets():
    assert price_interval(0) == timedelta(seconds=60)
    assert price_interval(30) == timedelta(seconds=60)


def test_interval_stretches_above_thirty_assets():
    assert price_interval(31) > timedelta(seconds=60)
    assert price_interval(60) == timedelta(seconds=120)


def test_interval_keeps_every_count_inside_the_budget():
    for count in (1, 30, 31, 100, 900, 5000):
        per_hour = count * 3600 / price_interval(count).total_seconds()
        assert per_hour <= 1800 + 1e-6


# --- convert_price ---------------------------------------------------------------


def test_convert_price_without_rate_is_the_eur_price():
    assert convert_price("73188.51648958", None) == 73188.51648958


def test_convert_price_applies_the_rate_and_rounds():
    assert convert_price("0.10000000", 3.0) == 0.3
    assert convert_price("100.00000000", 1.1367) == 113.67


def test_convert_price_of_garbage_is_none():
    assert convert_price("n/a", None) is None
    assert convert_price(None, 1.1) is None


def test_convert_price_of_a_non_finite_number_is_none():
    """"inf" and "nan" parse as floats, but Home Assistant refuses a
    non-finite sensor value."""
    assert convert_price("inf", None) is None
    assert convert_price("nan", None) is None
    assert convert_price("-inf", 1.1) is None


# --- TickerCoordinator -------------------------------------------------------------

# The regular pace of the rounds: price_interval of two tracked assets.
_PACE = timedelta(seconds=60)


class _Client:
    """Answers each asset's /tickers request with its price in `prices`, or
    "n/a" -- no usable price -- without one. While `rate_limited` every
    request gets a 429; an asset in `errors` fails with a BitpandaApiError of
    that kind (const.API_ERROR_KINDS) -- "timeout" and "connection" get no
    answer at all, "http_status" is an HTTP 503 --, and one in `failing` with
    an HTTP 404. `calls` records the requests in order."""

    def __init__(self, prices=None, failing=(), rate_limited=False, errors=None):
        self.prices = prices or {}
        self.failing = set(failing)
        self.rate_limited = rate_limited
        self.errors = dict(errors or {})
        self.calls: list[str] = []

    async def async_get_ticker(self, asset_id):
        self.calls.append(asset_id)
        path = f"/tickers/{asset_id}"
        if self.rate_limited:
            raise BitpandaRateLimitError(f"Rate limited on {path}")
        if asset_id in self.errors:
            kind = self.errors[asset_id]
            raise BitpandaApiError(
                f"Request to {path} failed", kind=kind, path=path,
                status=503 if kind == "http_status" else None,
            )
        if asset_id in self.failing:
            raise BitpandaApiError(
                f"HTTP 404 from {path}", kind="http_status", path=path, status=404
            )
        return {"price": self.prices.get(asset_id, "n/a")}


def _coordinator(client, tracked=None) -> TickerCoordinator:
    return TickerCoordinator(None, None, client, _TRACKED if tracked is None else tracked)


async def _round(coordinator) -> dict:
    """One round. Without Home Assistant, _async_update_data stores nothing:
    its data is kept here, as DataUpdateCoordinator keeps it, for the next
    round to carry last prices over from. A round that fails raises and
    leaves the data as it was."""
    coordinator.data = await coordinator._async_update_data()
    return coordinator.data


async def _next_round(coordinator, freezer, pace=_PACE) -> dict:
    """The next round, `pace` after the one before."""
    freezer.tick(pace)
    return await _round(coordinator)


async def _phases(coordinator, client, freezer, *phases) -> None:
    """Rounds at the regular pace, phase by phase: each phase names the
    assets whose requests fail and how many rounds it lasts."""
    for failing, rounds in phases:
        client.failing = failing
        for _ in range(rounds):
            await _next_round(coordinator, freezer)


def _lines(caplog, level: int, text: str) -> list[str]:
    """The price coordinator's log lines at `level` that mention `text`."""
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "custom_components.bitpanda.price_coordinator"
        and record.levelno == level
        and text in record.getMessage()
    ]


async def test_tickers_return_eur_prices():
    client = _Client({BTC: "73188.51648958", SOL: "150.00000000"})
    assert await _coordinator(client)._async_update_data() == {
        BTC: 73188.51648958,
        SOL: 150.0,
    }


async def test_nothing_tracked_makes_no_request():
    client = _Client()
    assert await _coordinator(client, tracked={})._async_update_data() == {}
    assert client.calls == []


async def test_a_failing_asset_keeps_its_last_price_for_two_rounds(caplog, freezer):
    """Bitcoin's own request fails while Solana's answers: its last price
    stays through two rounds at the regular pace. The third, two minutes
    after the first, confirms the failure: Bitcoin is left out -- only its
    own sensors go unavailable -- and warned about once."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    await _round(coordinator)
    client.failing = {BTC}
    with caplog.at_level(logging.WARNING):
        for _ in range(2):
            assert await _next_round(coordinator, freezer) == {BTC: 1.0, SOL: 2.0}
        assert _lines(caplog, logging.WARNING, "Bitcoin (BTC)") == []
        assert await _next_round(coordinator, freezer) == {SOL: 2.0}
    assert _lines(caplog, logging.WARNING, "Bitcoin (BTC)") == [
        "No price for Bitcoin (BTC); its price sensors are unavailable until it returns"
    ]


async def test_quick_rounds_never_confirm_an_assets_failure_sooner(caplog, freezer):
    """Five failures of Bitcoin's request, ten seconds apart -- rounds asked
    for by hand, which homeassistant.update_entity allows every ten seconds,
    where the regular pace brings one a minute: it keeps its last price, and
    nothing is warned about."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    await _round(coordinator)
    client.failing = {BTC}
    with caplog.at_level(logging.WARNING):
        for _ in range(5):
            data = await _next_round(coordinator, freezer, pace=timedelta(seconds=10))
    assert data == {BTC: 1.0, SOL: 2.0}
    assert _lines(caplog, logging.WARNING, "Bitcoin (BTC)") == []


async def test_a_fresh_price_ends_an_assets_streak(freezer):
    """Bitcoin fails twice, answers with a new price, then fails twice more,
    at the regular pace: never three rounds in a row without a fresh price,
    so it keeps its latest price throughout."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    await _round(coordinator)
    await _phases(coordinator, client, freezer, ({BTC}, 2))
    client.prices[BTC] = "3.00000000"
    await _phases(coordinator, client, freezer, (set(), 1), ({BTC}, 2))
    assert coordinator.data == {BTC: 3.0, SOL: 2.0}


async def test_the_tolerance_stretches_with_the_price_interval(freezer):
    """Sixty tracked assets are asked for every two minutes (price_interval),
    and an asset's failures are timed in that interval: failing a minute
    apart -- rounds asked for by hand -- it keeps its last price until its
    failures span two such intervals."""
    tracked = {f"asset-{number}": f"Asset {number}" for number in range(60)}
    client = _Client(dict.fromkeys(tracked, "1.00000000"))
    coordinator = _coordinator(client, tracked)
    await _round(coordinator)
    client.failing = {"asset-0"}
    carried = []
    for _ in range(5):
        carried.append("asset-0" in await _next_round(coordinator, freezer))
    assert carried == [True, True, True, True, False]


async def test_a_failing_asset_is_warned_about_once_its_failure_is_confirmed(caplog, freezer):
    """Bitcoin fails from the first round on, so it has no last price to
    keep: it is left out of every round. Its failure is warned about once it
    is confirmed, in the third round, and not again while it lasts."""
    client = _Client({SOL: "150.00000000"}, failing={BTC})
    coordinator = _coordinator(client)
    warned = []
    with caplog.at_level(logging.WARNING):
        for _ in range(4):
            assert await _next_round(coordinator, freezer) == {SOL: 150.0}
            warned.append(len(_lines(caplog, logging.WARNING, "Bitcoin (BTC)")))
    assert warned == [0, 0, 1, 1]


async def test_an_unreadable_price_counts_as_a_failure():
    client = _Client({SOL: "150.00000000"})  # BTC answers "n/a"
    assert await _coordinator(client)._async_update_data() == {SOL: 150.0}


async def test_a_non_finite_price_counts_as_a_failure():
    client = _Client({BTC: "nan", SOL: "150.00000000"})
    assert await _coordinator(client)._async_update_data() == {SOL: 150.0}


async def test_a_recovered_asset_is_warned_about_again_when_it_fails_again(caplog, freezer):
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    with caplog.at_level(logging.WARNING):
        await _phases(coordinator, client, freezer, ({BTC}, 3), (set(), 1), ({BTC}, 3))
    assert caplog.text.count("Bitcoin (BTC)") == 2


async def test_a_price_that_returns_is_logged_once_at_info(caplog, freezer):
    """The outage window is readable from the log: one WARNING once the
    price's failure is confirmed, one INFO when it returns -- neither
    repeated while the state lasts. An asset that never failed is never
    announced."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    with caplog.at_level(logging.INFO):
        await _phases(coordinator, client, freezer, ({BTC}, 3), (set(), 2))
    assert len(_lines(caplog, logging.WARNING, "Bitcoin (BTC)")) == 1
    assert _lines(caplog, logging.INFO, "Bitcoin (BTC)") == [
        "Price for Bitcoin (BTC) is back; its price sensors are available again"
    ]
    assert _lines(caplog, logging.INFO, "Solana (SOL)") == []


async def test_each_return_of_a_price_is_logged(caplog, freezer):
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    with caplog.at_level(logging.INFO):
        await _phases(
            coordinator, client, freezer, ({BTC}, 3), (set(), 1), ({BTC}, 3), (set(), 1)
        )
    assert len(_lines(caplog, logging.WARNING, "Bitcoin (BTC)")) == 2
    assert len(_lines(caplog, logging.INFO, "Bitcoin (BTC)")) == 2


async def test_a_price_back_after_a_failed_round_is_logged_once(caplog, freezer):
    """A round in which every request fails fails the update: it counts for
    every asset's streak, yet announces nothing. Bitcoin's return is
    announced once, with the next round that brings it back; Solana, never
    announced, is not."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    with caplog.at_level(logging.INFO):
        await _phases(coordinator, client, freezer, ({BTC}, 3))
        client.failing = {BTC, SOL}
        with pytest.raises(UpdateFailed):
            await _next_round(coordinator, freezer)
        client.failing = set()
        await _next_round(coordinator, freezer)
    assert len(_lines(caplog, logging.INFO, "Bitcoin (BTC)")) == 1
    assert _lines(caplog, logging.INFO, "Solana (SOL)") == []


async def test_the_end_of_a_rate_limit_backoff_is_logged_once_at_info(caplog):
    """One WARNING when the backoff starts, one INFO when it ends, naming
    the regular interval it returns to."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"}, rate_limited=True)
    coordinator = _coordinator(client)
    with caplog.at_level(logging.INFO):
        for _ in range(2):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()
        client.rate_limited = False
        await coordinator._async_update_data()
        await coordinator._async_update_data()
    assert len(_lines(caplog, logging.WARNING, "rate-limited")) == 1
    assert _lines(caplog, logging.INFO, "again") == [
        "Bitpanda answers the price requests again; back to polling every 0:01:00"
    ]


async def test_a_round_without_a_backoff_logs_no_end_of_one(caplog):
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    with caplog.at_level(logging.INFO):
        await _coordinator(client)._async_update_data()
    assert caplog.records == []


def _translation(err: Exception) -> tuple:
    return err.translation_domain, err.translation_key, err.translation_placeholders


async def test_every_asset_failing_fails_the_update():
    coordinator = _coordinator(_Client(failing={BTC, SOL}))
    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", "no_prices", None)


async def test_every_request_failing_fails_the_round_even_with_prices_to_carry():
    """Carried prices are no answer: a round in which no request brings a
    fresh price fails as a whole, and the tolerance of the whole update
    takes over (tolerance.py), however many last prices there are."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    await _round(coordinator)
    client.failing = {BTC, SOL}
    with pytest.raises(UpdateFailed) as excinfo:
        await _round(coordinator)
    assert _translation(excinfo.value) == ("bitpanda", "no_prices", None)


async def test_a_round_failing_as_a_whole_counts_once_for_each_asset(freezer):
    """Two rounds fail as a whole, two minutes apart -- a round was missed
    between them. Each counts once for every asset, and two failures
    confirm nothing, however far apart: the prices are still carried."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    await _round(coordinator)
    client.failing = {BTC, SOL}
    for pace in (_PACE, 2 * _PACE):
        with pytest.raises(UpdateFailed):
            await _next_round(coordinator, freezer, pace)
    assert coordinator.data == {BTC: 1.0, SOL: 2.0}


async def test_an_asset_still_failing_after_a_confirmed_outage_is_left_out_at_once(
    caplog, freezer
):
    """Three rounds in a row fail as a whole at the regular pace: nothing is
    warned about per asset, the outage is the whole update's (tolerance.py).
    In the next round Solana answers and Bitcoin fails: it has had no fresh
    price for four rounds, so its price from before the outage never comes
    back -- left out at once, and warned about."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    await _round(coordinator)
    client.failing = {BTC, SOL}
    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            with pytest.raises(UpdateFailed):
                await _next_round(coordinator, freezer)
        assert _lines(caplog, logging.WARNING, "No price for") == []
        client.failing = {BTC}
        assert await _next_round(coordinator, freezer) == {SOL: 2.0}
    assert _lines(caplog, logging.WARNING, "No price for") == [
        "No price for Bitcoin (BTC); its price sensors are unavailable until it returns"
    ]


async def test_the_failing_assets_are_those_without_a_fresh_price_now(freezer):
    """What the diagnostics report as failed: every asset without a fresh
    price in the latest round -- Bitcoin while its last price is carried
    over, every asset after a round that fails as a whole -- and none once
    they answer again."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    await _round(coordinator)
    seen = [coordinator.failing_assets]
    client.failing = {BTC}
    assert await _next_round(coordinator, freezer) == {BTC: 1.0, SOL: 2.0}
    seen.append(coordinator.failing_assets)
    client.failing = {BTC, SOL}
    with pytest.raises(UpdateFailed):
        await _next_round(coordinator, freezer)
    seen.append(coordinator.failing_assets)
    client.failing = set()
    await _next_round(coordinator, freezer)
    seen.append(coordinator.failing_assets)
    assert seen == [set(), {BTC}, {BTC, SOL}, set()]


async def test_a_rate_limit_doubles_the_interval_and_is_logged_once(caplog):
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"}, rate_limited=True)
    coordinator = _coordinator(client)
    base = coordinator.update_interval
    with caplog.at_level(logging.WARNING):
        with pytest.raises(UpdateFailed) as excinfo:
            await coordinator._async_update_data()
        assert _translation(excinfo.value) == ("bitpanda", "prices_rate_limited", None)
        assert coordinator.update_interval == base * 2
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator.update_interval == base * 4
    assert caplog.text.count("rate-limited") == 1
    # The first 429 stops the round: no further requests after it. Bitcoin,
    # whose request got it, is asked for last in the next round.
    assert client.calls == [BTC, SOL]

    client.rate_limited = False
    await coordinator._async_update_data()
    assert coordinator.update_interval == base


async def test_a_rate_limit_backoff_is_capped():
    coordinator = _coordinator(_Client(rate_limited=True))
    base = coordinator.update_interval
    for _ in range(10):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    assert coordinator.update_interval == base * 16


async def test_a_rate_limited_round_counts_for_every_asset(caplog, freezer):
    """A 429 stops the round: it raises, and nothing is logged per asset.
    Yet it brought no fresh price, so it counts for every asset's streak:
    Bitcoin, failing in the rounds before and after it, is confirmed in the
    round after it, two minutes after its first failure."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client)
    await _round(coordinator)
    client.failing = {BTC}
    await _next_round(coordinator, freezer)
    client.rate_limited = True
    with caplog.at_level(logging.WARNING):
        with pytest.raises(UpdateFailed):
            await _next_round(coordinator, freezer)
        assert _lines(caplog, logging.WARNING, "Bitcoin (BTC)") == []
        client.rate_limited = False
        assert await _next_round(coordinator, freezer) == {SOL: 2.0}
    assert len(_lines(caplog, logging.WARNING, "Bitcoin (BTC)")) == 1


# --- A round without an answer -------------------------------------------------------
#
# Every request waits for its own timeout (api.py): a round that went on
# through a hanging connection would take one timeout per tracked asset, and
# stretch the tolerance with their number. A first round, before any data,
# has no tolerance to stretch: it asks for every asset.

# Five tracked assets, asked for in this order while each one's latest
# request brought a fresh price.
_FIVE = {f"asset-{number}": f"Asset {number}" for number in range(5)}


async def _asked_for(coordinator, client, freezer) -> list[str]:
    """The assets the next round asks for, in order."""
    client.calls.clear()
    await _next_round(coordinator, freezer)
    return list(client.calls)


async def _try_round(coordinator, client, freezer) -> tuple[list[str], bool]:
    """The assets the next round asks for, in order, and whether it returned
    data -- False when it failed as a whole."""
    client.calls.clear()
    try:
        await _next_round(coordinator, freezer)
    except UpdateFailed:
        return list(client.calls), False
    return list(client.calls), True


@pytest.mark.parametrize(
    "kinds",
    [("timeout", "timeout"), ("connection", "connection"), ("timeout", "connection")],
    ids=["timeouts", "no_connection", "mixed"],
)
async def test_two_unanswered_requests_before_any_price_stop_the_round(kinds):
    """After a first round, the first two requests get no answer -- a
    timeout, or no connection at all: the round stops, the other assets
    unasked. It fails as a whole, like a round without a fresh price, and
    counts for every asset; the last prices stay."""
    first, second, *_ = _FIVE
    client = _Client(dict.fromkeys(_FIVE, "1.00000000"))
    coordinator = _coordinator(client, _FIVE)
    await _round(coordinator)
    client.errors = {first: kinds[0], second: kinds[1]}
    client.calls.clear()
    with pytest.raises(UpdateFailed) as excinfo:
        await _round(coordinator)
    assert _translation(excinfo.value) == ("bitpanda", "no_prices", None)
    assert client.calls == [first, second]
    assert coordinator.failing_assets == set(_FIVE)
    assert coordinator.data == dict.fromkeys(_FIVE, 1.0)


async def test_unanswered_requests_after_a_fresh_price_never_stop_the_round():
    """After a first round: a timeout, a price, then two timeouts in a row.
    A fresh price has shown that Bitpanda answers, so the round goes on to
    the end."""
    first, second, third, fourth, fifth = _FIVE
    client = _Client(dict.fromkeys(_FIVE, "1.00000000"))
    coordinator = _coordinator(client, _FIVE)
    await _round(coordinator)
    client.errors = {first: "timeout", third: "timeout", fourth: "timeout"}
    client.calls.clear()
    await _round(coordinator)
    assert client.calls == list(_FIVE)
    assert coordinator.failing_assets == {first, third, fourth}


@pytest.mark.parametrize("answer", ["http_404", "unreadable", "no_usable_price"])
async def test_an_answered_request_breaks_a_run_of_unanswered_ones(answer):
    """After a first round: a timeout, then a request that is answered, if
    uselessly -- with an HTTP 404, an unreadable body, no usable price --,
    then a timeout. Not two in a row, so the round goes on to the end."""
    first, second, third, fourth, fifth = _FIVE
    client = _Client(dict.fromkeys(_FIVE, "1.00000000"))
    coordinator = _coordinator(client, _FIVE)
    await _round(coordinator)
    client.errors = {first: "timeout", third: "timeout"}
    if answer == "http_404":
        client.failing = {second}
    elif answer == "unreadable":
        client.errors[second] = "unreadable"
    else:
        del client.prices[second]
    client.calls.clear()
    await _round(coordinator)
    assert client.calls == list(_FIVE)
    assert coordinator.failing_assets == {first, second, third}


@pytest.mark.parametrize("failure", ["http_404", "timeout", "no_usable_price"])
async def test_the_assets_without_a_fresh_price_are_asked_for_last(freezer, failure):
    """The first and the third asset get no fresh price -- their requests
    fail, or are answered without a usable price: from the next round on
    they are asked for after the others, which keep their tracked order, the
    first before the third, as they were marked -- and all in tracked order
    again once their prices are back."""
    first, second, third, fourth, fifth = _FIVE
    client = _Client(dict.fromkeys(_FIVE, "1.00000000"))
    coordinator = _coordinator(client, _FIVE)

    def without_a_fresh_price(assets):
        client.failing = set(assets) if failure == "http_404" else set()
        client.errors = dict.fromkeys(assets, "timeout") if failure == "timeout" else {}
        for asset in _FIVE:
            unusable = failure == "no_usable_price" and asset in assets
            client.prices[asset] = "n/a" if unusable else "1.00000000"

    asked = []
    for assets in ({first, third}, {first, third}, set(), set()):
        without_a_fresh_price(assets)
        asked.append(await _asked_for(coordinator, client, freezer))
    late = [second, fourth, fifth, first, third]
    assert asked == [list(_FIVE), late, late, list(_FIVE)]


async def test_an_asset_that_never_answers_cannot_stop_the_rounds(freezer):
    """Tracked first, one asset's requests always time out. From the second
    round on it is asked for last, so its timeout never follows another one
    before a price: in the fourth round Bitcoin's request times out too, and
    Solana's price comes in between. No round fails as a whole, and the
    other assets keep their prices -- Bitcoin's carried in the fourth."""
    tracked = {"hanging": "Hanging (HNG)", **_TRACKED}
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = _coordinator(client, tracked)
    asked, shown = [], []
    for errors in ({}, {}, {}, {BTC: "timeout"}):
        client.errors = {"hanging": "timeout", **errors}
        asked.append(await _asked_for(coordinator, client, freezer))
        shown.append(coordinator.data)
    assert asked == [["hanging", BTC, SOL]] + [[BTC, SOL, "hanging"]] * 3
    assert shown == [{BTC: 1.0, SOL: 2.0}] * 4


async def test_a_first_round_never_stops(freezer):
    """The first two tracked assets never answer. A first round -- no data
    yet, so no last price whose tolerance they could stretch -- asks for
    every asset all the same: the others' prices come, and setup cannot
    stall on the two. From the next round on they are asked for last."""
    first, second, third, fourth, fifth = _FIVE
    client = _Client(
        dict.fromkeys(_FIVE, "1.00000000"), errors={first: "timeout", second: "timeout"}
    )
    coordinator = _coordinator(client, _FIVE)
    asked, shown = [], []
    for _ in range(3):
        asked.append(await _asked_for(coordinator, client, freezer))
        shown.append(coordinator.data)
    assert asked == [list(_FIVE)] + [[third, fourth, fifth, first, second]] * 2
    assert shown == [{third: 1.0, fourth: 1.0, fifth: 1.0}] * 3


async def test_a_first_round_without_any_answer_asks_for_every_asset():
    """Nothing answers a first round: it asks for every asset before it
    fails as a whole, and leaves no data -- there is no last price."""
    client = _Client(errors=dict.fromkeys(_FIVE, "timeout"))
    coordinator = _coordinator(client, _FIVE)
    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", "no_prices", None)
    assert client.calls == list(_FIVE)
    assert coordinator.failing_assets == set(_FIVE)
    assert coordinator.data is None


async def test_the_marked_assets_are_asked_for_oldest_mark_first(freezer):
    """The third asset fails in a first round; then a short outage stops the
    next round after the first two requests. Once Bitpanda answers again,
    the assets without a mark come first, in tracked order -- the fourth and
    the fifth, which the stopped round did not ask -- then the marked ones,
    the oldest mark first: the third before the first and the second, which
    the stopped round moved behind every other. With every price back, all
    are asked for in tracked order again."""
    first, second, third, fourth, fifth = _FIVE
    client = _Client(dict.fromkeys(_FIVE, "1.00000000"), failing={third})
    coordinator = _coordinator(client, _FIVE)
    assert await _asked_for(coordinator, client, freezer) == list(_FIVE)
    client.failing = set()
    client.errors = dict.fromkeys(_FIVE, "connection")
    with pytest.raises(UpdateFailed):
        await _asked_for(coordinator, client, freezer)
    assert client.calls == [first, second]
    client.errors = {}
    assert await _asked_for(coordinator, client, freezer) == [
        fourth, fifth, third, first, second
    ]
    assert await _asked_for(coordinator, client, freezer) == list(_FIVE)


async def test_an_http_error_round_cannot_leave_two_hanging_assets_in_front(freezer):
    """h1 and h2, tracked first, never answer; a and b do, except in one
    round in which both get an HTTP 503. That round fails -- no fresh price
    -- and leaves every asset marked, a and b before h1 and h2. So the
    rounds after it still ask for a and b first, and complete: that round
    is the only one that fails."""
    tracked = {"h1": "H1", "h2": "H2", "a": "A", "b": "B"}
    hanging = {"h1": "timeout", "h2": "timeout"}
    client = _Client(dict.fromkeys(("a", "b"), "1.00000000"))
    coordinator = _coordinator(client, tracked)
    http_503 = {"a": "http_status", "b": "http_status"}
    rounds = []
    for errors in ({}, {}, http_503, {}, {}, {}):
        client.errors = {**hanging, **errors}
        rounds.append(await _try_round(coordinator, client, freezer))
    answering_first = (["a", "b", "h1", "h2"], True)
    assert rounds == [
        (["h1", "h2", "a", "b"], True),
        answering_first,
        (["a", "b", "h1", "h2"], False),
        answering_first,
        answering_first,
        answering_first,
    ]
    assert coordinator.data == {"a": 1.0, "b": 1.0}


async def test_an_outage_cannot_leave_two_hanging_assets_in_front(freezer):
    """h1 and h2, tracked first, never answer; a to d do, except in two
    rounds without a connection, which stop after two requests each and
    mark a to d after h1 and h2. Once the connection is back, h1 and h2
    hold the oldest marks: the first round asks for them first and stops,
    which moves them behind every other asset, and the rounds after it
    complete. One round stops after the outage, no more."""
    tracked = {name: name.upper() for name in ("h1", "h2", "a", "b", "c", "d")}
    hanging = {"h1": "timeout", "h2": "timeout"}
    client = _Client(dict.fromkeys(("a", "b", "c", "d"), "1.00000000"))
    coordinator = _coordinator(client, tracked)
    rounds = []
    for connected in (True, True, False, False, True, True, True):
        client.errors = hanging if connected else dict.fromkeys(tracked, "connection")
        rounds.append(await _try_round(coordinator, client, freezer))
    answering_first = (["a", "b", "c", "d", "h1", "h2"], True)
    assert rounds == [
        (["h1", "h2", "a", "b", "c", "d"], True),
        answering_first,
        (["a", "b"], False),
        (["c", "d"], False),
        (["h1", "h2"], False),
        answering_first,
        answering_first,
    ]
    assert coordinator.data == dict.fromkeys(("a", "b", "c", "d"), 1.0)


# --- Overlapping rounds ---------------------------------------------------------------
#
# Home Assistant 2025.5 takes no lock around a refresh: a refresh by hand
# (bitpanda.refresh) can run while a scheduled one waits for an answer.


class _HeldClient(_Client):
    """A _Client whose first request for `held` waits: it sets `asked`, and
    answers once `answer` is set."""

    def __init__(self, prices, held):
        super().__init__(prices)
        self.held = held
        self.asked = asyncio.Event()
        self.answer = asyncio.Event()

    async def async_get_ticker(self, asset_id):
        if asset_id == self.held and not self.asked.is_set():
            self.asked.set()
            await self.answer.wait()
        return await super().async_get_ticker(asset_id)


async def test_two_overlapping_rounds_both_return_data():
    """Round A waits for Bitcoin's answer. Meanwhile round B asks for both
    assets -- Solana first, as A has marked Bitcoin -- and completes;
    Bitcoin's fresh price removes its mark. Then Bitcoin answers A, whose
    fresh price finds no mark left to remove: both rounds return data."""
    client = _HeldClient({BTC: "1.00000000", SOL: "2.00000000"}, held=BTC)
    coordinator = _coordinator(client)
    round_a = asyncio.create_task(coordinator._async_update_data())
    await client.asked.wait()
    assert await coordinator._async_update_data() == {BTC: 1.0, SOL: 2.0}
    client.answer.set()
    assert await round_a == {BTC: 1.0, SOL: 2.0}
    assert client.calls == [SOL, BTC, BTC, SOL]


# --- TickerCoordinator through Home Assistant's refresh -----------------------------
#
# With `hass` a failed round keeps the data it leaves, and Home Assistant
# tells the listeners as it does for every coordinator (tolerance.py).


async def _refresh(coordinator, freezer, pace=_PACE) -> None:
    """One refresh through Home Assistant, `pace` after the one before."""
    freezer.tick(pace)
    await coordinator.async_refresh()


@contextmanager
def _listening(coordinator):
    """The data the coordinator's listeners found each time it told them,
    while the block runs. A listener makes the coordinator schedule its next
    round; leaving the block removes the listener, and with it that timer,
    which Home Assistant's test harness would fail the test for."""
    seen: list[dict] = []
    unsubscribe = coordinator.async_add_listener(lambda: seen.append(dict(coordinator.data)))
    try:
        yield seen
    finally:
        unsubscribe()


async def test_a_whole_failure_that_confirms_a_carried_price_leaves_it_out_at_once(
    hass, freezer, caplog
):
    """Bitcoin's own request fails while Solana's answers: its last price is
    carried. Then two rounds fail as a whole, and count for Bitcoin too: the
    second confirms its failure, two minutes after its first, while the
    whole update's failure is not confirmed yet. Bitcoin leaves the data in
    that very round, and the listeners are told -- after a failure Home
    Assistant would not tell them. Those rounds log nothing per asset: the
    warning comes with the next round that returns data, Bitcoin still
    failing."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = TickerCoordinator(hass, None, client, _TRACKED)
    with _listening(coordinator) as seen:
        await coordinator.async_refresh()
        client.failing = {BTC}
        await _refresh(coordinator, freezer)
        client.failing = {BTC, SOL}
        caplog.clear()
        with caplog.at_level(logging.DEBUG):
            for _ in range(2):
                await _refresh(coordinator, freezer)
        assert _lines(caplog, logging.DEBUG, "No price for") == []
        assert _lines(caplog, logging.WARNING, "No price for") == []
        assert (coordinator.data, coordinator.data_available) == ({SOL: 2.0}, True)
        assert seen == [{BTC: 1.0, SOL: 2.0}] * 3 + [{SOL: 2.0}]

        client.failing = {BTC}
        with caplog.at_level(logging.WARNING):
            await _refresh(coordinator, freezer)
    assert coordinator.data == {SOL: 2.0}
    assert _lines(caplog, logging.WARNING, "No price for") == [
        "No price for Bitcoin (BTC); its price sensors are unavailable until it returns"
    ]


async def test_a_rate_limit_that_confirms_a_carried_price_leaves_it_out_at_once(
    hass, freezer
):
    """Likewise under a rate limit's back-off: Bitcoin is carried, then two
    rounds are rate-limited, the second after the doubled interval. It
    confirms Bitcoin's failure -- three rounds without a fresh price, three
    minutes from the first -- while the whole update's is not confirmed:
    Bitcoin leaves the data at once, and the listeners are told."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = TickerCoordinator(hass, None, client, _TRACKED)
    with _listening(coordinator) as seen:
        await coordinator.async_refresh()
        client.failing = {BTC}
        await _refresh(coordinator, freezer)
        client.rate_limited = True
        for _ in range(2):
            await _refresh(coordinator, freezer, coordinator.update_interval)
    assert coordinator.update_interval == 4 * _PACE
    assert (coordinator.data, coordinator.data_available) == ({SOL: 2.0}, True)
    assert seen == [{BTC: 1.0, SOL: 2.0}] * 3 + [{SOL: 2.0}]


async def test_rate_limited_rounds_end_the_tolerance_after_about_seven_minutes(
    hass, freezer, caplog
):
    """Every round is rate-limited, each after the backed-off interval: the
    429s at +1 and +3 minutes keep the prices available, the one at +7
    ends the tolerance -- warned about once, not again at +15."""
    client = _Client({BTC: "1.00000000", SOL: "2.00000000"})
    coordinator = TickerCoordinator(hass, None, client, _TRACKED)
    await coordinator.async_refresh()
    start = dt_util.utcnow()
    client.rate_limited = True
    available = {}
    with caplog.at_level(logging.WARNING):
        for _ in range(4):
            await _refresh(coordinator, freezer, coordinator.update_interval)
            available[dt_util.utcnow() - start] = coordinator.data_available
    assert available == {
        timedelta(minutes=1): True,
        timedelta(minutes=3): True,
        timedelta(minutes=7): False,
        timedelta(minutes=15): False,
    }
    assert _lines(caplog, logging.WARNING, "refreshes in a row failed") == [
        "bitpanda_tickers: 3 refreshes in a row failed; its sensors are unavailable "
        "until one succeeds"
    ]


def test_a_slow_interval_is_announced_at_construction(caplog):
    tracked = {f"asset-{i}": f"Asset {i}" for i in range(1000)}
    with caplog.at_level(logging.WARNING):
        coordinator = TickerCoordinator(None, None, _Client(), tracked)
    assert coordinator.update_interval == price_interval(1000)
    assert "1000 price trackers" in caplog.text


# --- The slow interval as a repair issue ------------------------------------------------


def _interval_issue(hass) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue("bitpanda", "slow_price_interval")


async def test_an_interval_above_thirty_minutes_is_a_repair_issue(hass):
    """A warning -- prices still come, only slowly -- naming the number of
    tracked assets and the interval, in whole minutes rounded up, so it
    never reads as 30. Raised again at every setup while it lasts, so not
    kept across restarts; nothing to fix in a dialog."""
    async_report_price_interval(hass, 1000)
    issue = _interval_issue(hass)
    assert (issue.translation_key, issue.translation_placeholders) == (
        "slow_price_interval", {"count": "1000", "minutes": "34"}
    )
    assert (
        issue.severity, issue.is_fixable, issue.is_persistent, issue.learn_more_url,
        issue.issue_domain,
    ) == (ir.IssueSeverity.WARNING, False, False, None, None)


async def test_just_above_thirty_minutes_reads_as_thirty_one(hass):
    async_report_price_interval(hass, 901)
    assert _interval_issue(hass).translation_placeholders == {"count": "901", "minutes": "31"}


@pytest.mark.parametrize("count", [0, 30, 900])
async def test_thirty_minutes_or_less_raise_no_issue(hass, count):
    async_report_price_interval(hass, count)
    assert _interval_issue(hass) is None


async def test_the_issue_goes_once_the_interval_is_thirty_minutes_or_less(hass):
    async_report_price_interval(hass, 950)
    assert _interval_issue(hass) is not None
    async_report_price_interval(hass, 900)
    assert _interval_issue(hass) is None


async def test_the_issue_can_be_deleted_outright(hass):
    """For when the Price Tracker itself goes."""
    async_report_price_interval(hass, 950)
    async_delete_price_interval_issue(hass)
    assert _interval_issue(hass) is None


async def test_the_issue_text_renders_in_every_language(hass):
    async_report_price_interval(hass, 1000)
    raised = raised_issues(hass)
    assert set(raised) == {"slow_price_interval"}
    assert_issue_texts_render(raised)


# --- EcbCoordinator ------------------------------------------------------------------

_RATES = EcbRates(date="2026-09-24", rates={"USD": 1.1367})


_TIMEOUT = EcbError("Timeout fetching the ECB rates", kind="timeout")


async def test_ecb_retries_sooner_while_no_rates_were_ever_loaded():
    coordinator = EcbCoordinator(None, None, object())
    with patch(
        "custom_components.bitpanda.price_coordinator.async_fetch_ecb_rates",
        AsyncMock(side_effect=[_TIMEOUT, _RATES]),
    ):
        with pytest.raises(UpdateFailed) as excinfo:
            await coordinator._async_update_data()
        assert _translation(excinfo.value) == ("bitpanda", "ecb_rates_failed_timeout", None)
        assert coordinator.update_interval == timedelta(minutes=15)
        await coordinator._async_update_data()
    assert coordinator.update_interval == timedelta(hours=6)


@pytest.mark.parametrize(
    ("error", "key", "placeholders"),
    [
        (EcbError("x", kind="timeout"), "ecb_rates_failed_timeout", None),
        (EcbError("x", kind="connection"), "ecb_rates_failed_connection", None),
        (
            EcbError("x", kind="http_status", status=503),
            "ecb_rates_failed_http_status",
            {"status": "503"},
        ),
        (EcbError("x", kind="unreadable"), "ecb_rates_failed_unreadable", None),
        (EcbError("x"), "ecb_rates_failed", None),
        (EcbError("x", kind="http_status"), "ecb_rates_failed", None),
    ],
    ids=["timeout", "connection", "http_status", "unreadable", "no_kind", "no_status"],
)
async def test_a_failed_ecb_fetch_is_translated_by_what_failed(error, key, placeholders):
    """One text per kind of failure, with an HTTP status as the only
    placeholder; a failure that says too little gets the plain text. The
    English message never reaches a placeholder."""
    coordinator = EcbCoordinator(None, None, object())
    with patch(
        "custom_components.bitpanda.price_coordinator.async_fetch_ecb_rates",
        AsyncMock(side_effect=error),
    ), pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", key, placeholders)


async def test_ecb_coordinator_keeps_the_last_rates_when_a_fetch_fails(hass):
    coordinator = EcbCoordinator(hass, None, object())
    with patch(
        "custom_components.bitpanda.price_coordinator.async_fetch_ecb_rates",
        AsyncMock(side_effect=[_RATES, _TIMEOUT]),
    ):
        await coordinator.async_refresh()
        assert coordinator.data == _RATES
        await coordinator.async_refresh()
    assert coordinator.last_update_success is False
    assert coordinator.data == _RATES
