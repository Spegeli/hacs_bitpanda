"""Tests for cursor pagination and the /operations cursor workaround.

/operations cursors are base64 of an ISO-8601 timestamp meaning "records
strictly older than this". The server silently ignores a cursor whose
timestamp has no fractional seconds -- it answers with page 1 and a 200 --
and it emits such cursors itself whenever a page boundary falls on a whole
second. That gives two failure shapes for a plain cursor loop:

- self-loop: the first boundary is whole-second, page 1 comes back with the
  same next_cursor that was just sent;
- two-cycle: a later boundary is whole-second, page 1 comes back with the
  first page's cursor, and the loop alternates between pages 1 and 2.

Mock notes: AiohttpClientMocker never consumes a registration and matches
query strings by subset, so every cursor-bearing registration is made before
the bare one it would otherwise be shadowed by, and the exact parameters sent
are asserted from `mock_calls`. A regression in the loop guards spins without
yielding to the event loop, so every test that could loop carries
`pytest.mark.timeout`.
"""
import asyncio
import base64
import re
from datetime import UTC, datetime, timedelta

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda import api
from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
    normalize_operations_cursor,
)
from custom_components.bitpanda.const import API_BASE_URL, MAX_PAGE_SIZE


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("ascii")).decode("ascii")


# Boundary timestamps in the forms the API emits them.
_WHOLE = "2026-02-17T16:19:29Z"  # record #100 of the research dump
_WHOLE_FIXED = "2026-02-17T16:19:29.000Z"
_MILLIS = "2026-09-09T18:31:22.080Z"
_WHOLE_LATER = "2026-09-08T16:32:02Z"
_WHOLE_LATER_FIXED = "2026-09-08T16:32:02.000Z"


def _ops_page(ids: list[str], next_cursor: str | None = None) -> dict:
    body: dict = {
        "data": [{"operation_id": i, "operation_type": "reward"} for i in ids],
        "has_next_page": next_cursor is not None,
    }
    if next_cursor is not None:
        body["next_cursor"] = next_cursor
    return body


def _id_page(ids: list[str], next_cursor: str | None = None) -> dict:
    body: dict = {"data": [{"id": i} for i in ids], "has_next_page": next_cursor is not None}
    if next_cursor is not None:
        body["next_cursor"] = next_cursor
    return body


# --- normalize_operations_cursor ----------------------------------------------


def test_normalize_adds_milliseconds_to_a_whole_second_cursor():
    # Literal values, not computed with the same helper as the code under test.
    assert _b64(_WHOLE_LATER) == "MjAyNi0wOS0wOFQxNjozMjowMlo="
    assert (
        normalize_operations_cursor("MjAyNi0wOS0wOFQxNjozMjowMlo=")
        == "MjAyNi0wOS0wOFQxNjozMjowMi4wMDBa"
    )
    assert base64.b64decode("MjAyNi0wOS0wOFQxNjozMjowMi4wMDBa") == (
        b"2026-09-08T16:32:02.000Z"
    )


def test_normalize_accepts_a_cursor_sent_without_padding():
    assert (
        normalize_operations_cursor("MjAyNi0wOS0wOFQxNjozMjowMlo")
        == "MjAyNi0wOS0wOFQxNjozMjowMi4wMDBa"
    )


def test_normalize_leaves_a_cursor_with_milliseconds_unchanged():
    cursor = "MjAyNi0wOS0wOVQxODozMToyMi4wODBa"  # 2026-09-09T18:31:22.080Z
    assert base64.b64decode(cursor) == _MILLIS.encode()
    assert normalize_operations_cursor(cursor) == cursor


@pytest.mark.parametrize(
    "cursor",
    [
        "",
        "not base64!",
        "abc",  # decodes once padded, but not to text
        "MjAy*A==",
        _b64("some-opaque-token"),
        _b64("2026-09-08T16:32:02+00:00"),  # an offset, not Z
        _b64("2026-09-08T16:32Z"),  # no seconds: ".000" would not be ISO
        _b64("2026-13-45T16:32:02Z"),  # right shape, impossible date
        base64.b64encode(b"\xff\xfe\xfd").decode("ascii"),  # not text
    ],
)
def test_normalize_leaves_anything_else_unchanged(cursor):
    assert normalize_operations_cursor(cursor) == cursor


def test_normalize_leaves_a_non_string_unchanged():
    assert normalize_operations_cursor(None) is None


def test_normalized_cursor_is_alphabet_and_padding_neutral():
    """Whatever base64 form the server uses, the fixed cursor fits it.

    A whole-second timestamp with ".000" is 24 ASCII bytes drawn from digits,
    "-", ":", "T", "." and "Z". Base64 of that is always 32 plain letters and
    digits: no padding, and none of "+", "/", "-", "_" -- the only characters
    on which the standard and URL-safe alphabets differ. Sampled across six
    years of timestamps rather than asserted from the argument alone.
    """
    start = datetime(2021, 1, 1, tzinfo=UTC)
    for seconds in range(0, 6 * 366 * 24 * 3600, 7919):
        stamp = (start + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        fixed = normalize_operations_cursor(_b64(stamp))
        assert re.fullmatch(r"[A-Za-z0-9]{32}", fixed), stamp
        assert base64.b64decode(fixed).decode("ascii") == stamp[:-1] + ".000Z"


# --- /operations: both failure shapes, walked with the normalised cursor -----


@pytest.mark.timeout(5)
async def test_operations_self_loop_shape_collects_every_page():
    """First boundary without milliseconds -- the shape of the live run, which
    published VSN rewards_net 751.49 over the first 100 operations instead of
    the true 1765.53 over all of them.
    """
    page_one = _ops_page(["o1", "o2", "o3"], next_cursor=_b64(_WHOLE))
    with mock_aiohttp_client() as mocker:
        # The server's bug: the raw whole-second cursor is ignored.
        mocker.get(f"{API_BASE_URL}/operations?cursor={_b64(_WHOLE)}", json=page_one)
        mocker.get(
            f"{API_BASE_URL}/operations?cursor={_b64(_WHOLE_FIXED)}",
            # Pages overlap by one record on this endpoint.
            json=_ops_page(["o3", "o4", "o5"]),
        )
        mocker.get(f"{API_BASE_URL}/operations", json=page_one)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_operations()

    assert [o["operation_id"] for o in result] == ["o1", "o2", "o3", "o4", "o5"]
    assert mocker.call_count == 2
    assert mocker.mock_calls[0][1].query_string == "page_size=100"
    assert mocker.mock_calls[1][1].query_string == (
        f"page_size=100&cursor={_b64(_WHOLE_FIXED)}"
    )


@pytest.mark.timeout(5)
async def test_operations_two_cycle_shape_collects_every_page():
    """First boundary carries milliseconds, the second does not. Unfixed, the
    ignored second cursor re-serves page 1, whose cursor leads to page 2
    again -- alternating until the server answers 429.
    """
    page_one = _ops_page(["o1", "o2"], next_cursor=_b64(_MILLIS))
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/operations?cursor={_b64(_WHOLE_LATER)}", json=page_one
        )
        mocker.get(
            f"{API_BASE_URL}/operations?cursor={_b64(_WHOLE_LATER_FIXED)}",
            json=_ops_page(["o3", "o4"]),
        )
        mocker.get(
            f"{API_BASE_URL}/operations?cursor={_b64(_MILLIS)}",
            json=_ops_page(["o2", "o3"], next_cursor=_b64(_WHOLE_LATER)),
        )
        mocker.get(f"{API_BASE_URL}/operations", json=page_one)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            result = await client.async_get_operations()

    assert [o["operation_id"] for o in result] == ["o1", "o2", "o3", "o4"]
    assert mocker.call_count == 3
    assert [call[1].query_string for call in mocker.mock_calls] == [
        "page_size=100",
        f"page_size=100&cursor={_b64(_MILLIS)}",
        f"page_size=100&cursor={_b64(_WHOLE_LATER_FIXED)}",
    ]


# --- Paths without the workaround: the same shapes raise, bounded ------------


@pytest.mark.timeout(5)
async def test_self_loop_shape_without_normalisation_raises_after_two_requests():
    page_one = _id_page(["a1", "a2"], next_cursor=_b64(_WHOLE))
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/assets?cursor={_b64(_WHOLE)}", json=page_one)
        mocker.get(f"{API_BASE_URL}/assets", json=page_one)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaApiError, match="/assets"):
                await client.async_get_assets()

    assert mocker.call_count == 2
    # The cursor went out exactly as received: the workaround is
    # /operations-only. Compared decoded, since its "=" padding travels
    # percent-encoded.
    assert list(mocker.mock_calls[1][1].query.items()) == [
        ("page_size", "100"),
        ("cursor", _b64(_WHOLE)),
    ]


@pytest.mark.timeout(5)
async def test_two_cycle_shape_without_normalisation_raises_after_three_requests():
    page_one = _id_page(["c1"], next_cursor=_b64(_MILLIS))
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/earn/configs?cursor={_b64(_WHOLE_LATER)}", json=page_one
        )
        mocker.get(
            f"{API_BASE_URL}/earn/configs?cursor={_b64(_MILLIS)}",
            json=_id_page(["c2"], next_cursor=_b64(_WHOLE_LATER)),
        )
        mocker.get(f"{API_BASE_URL}/earn/configs", json=page_one)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaApiError, match="/earn/configs"):
                await client.async_get_earn_configs()

    assert mocker.call_count == 3


@pytest.mark.timeout(5)
async def test_operations_cycle_the_workaround_cannot_fix_raises():
    """A cursor that already carries milliseconds and still repeats is a
    server fault normalisation cannot repair: raise, never return page 1 as
    the whole history.
    """
    page_one = _ops_page(["o1"], next_cursor=_b64(_MILLIS))
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/operations?cursor={_b64(_MILLIS)}", json=page_one)
        mocker.get(f"{API_BASE_URL}/operations", json=page_one)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaApiError, match="/operations"):
                await client.async_get_operations()

    assert mocker.call_count == 2


# --- Page cap and a missing cursor --------------------------------------------


@pytest.mark.timeout(5)
async def test_paginate_raises_when_the_page_cap_is_reached(monkeypatch):
    """Ever-new cursors never repeat, so only the cap stops them."""
    monkeypatch.setattr(api, "_MAX_PAGES", 3)
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/assets?cursor=C2", json=_id_page(["c"], "C3"))
        mocker.get(f"{API_BASE_URL}/assets?cursor=C1", json=_id_page(["b"], "C2"))
        mocker.get(f"{API_BASE_URL}/assets", json=_id_page(["a"], "C1"))
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaApiError, match="/assets"):
                await client.async_get_assets()

    assert mocker.call_count == 3


def test_page_cap_is_far_above_any_real_listing():
    """The whole 14,054-asset catalogue is 141 pages of 100 and a five-year
    operation history 13; the cap must leave a wide margin above both.
    """
    assert api._MAX_PAGES * MAX_PAGE_SIZE >= 3 * 14054


@pytest.mark.timeout(5)
async def test_paginate_raises_when_another_page_is_announced_without_a_cursor():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets",
            json={"data": [{"id": "a"}], "has_next_page": True},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            with pytest.raises(BitpandaApiError, match="/assets"):
                await client.async_get_assets()

    assert mocker.call_count == 1


@pytest.mark.timeout(5)
async def test_pagination_errors_never_carry_the_api_key():
    secret = "totally-secret-key"
    page_one = _id_page(["a1"], next_cursor="STUCK")
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/assets?cursor=STUCK", json=page_one)
        mocker.get(f"{API_BASE_URL}/assets", json=page_one)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient(secret, session)
            with pytest.raises(BitpandaApiError) as excinfo:
                await client.async_get_assets()

    assert secret not in str(excinfo.value)
    assert excinfo.value.__cause__ is None
