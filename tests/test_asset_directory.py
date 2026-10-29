"""Tests for the asset directory that names the holdings."""
import asyncio
from datetime import timedelta
import logging

from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from custom_components.bitpanda.assets import AssetDirectory, slim_asset
from custom_components.bitpanda.const import API_BASE_URL, UNKNOWN_ASSET_RETRY

VSN = {
    "id": "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb",
    "symbol": "VSN",
    "name": "Vision",
    "type": "cryptocoin",
    "group": "token",
    "isin": None,
    "tradable": True,
}
BTC = {"id": "b86c034b-efe3-11eb-b56f-0691764446a7", "symbol": "BTC", "name": "Bitcoin",
       "type": "cryptocoin", "group": "coin"}


class _Client:
    def __init__(self, records=None, fail=None, rate_limit=False, refuse=None):
        self.records = records or {}
        self.fail = fail or set()
        self.rate_limit = rate_limit
        # The assets whose lookup Bitpanda answers 401.
        self.refuse = refuse or set()
        self.calls: list[str] = []

    async def async_get_assets(self, *, asset_id=None, **_):
        self.calls.append(asset_id)
        if self.rate_limit:
            raise BitpandaRateLimitError("Rate limited on /assets")
        if asset_id in self.fail:
            raise BitpandaApiError("Timeout for /assets")
        if asset_id in self.refuse:
            raise BitpandaAuthError(
                "Unauthorized for /assets", kind="http_status", path="/assets", status=401
            )
        record = self.records.get(asset_id)
        return [record] if record else []


def _unexpected_refusal():
    raise AssertionError("the key was refused")


def test_slim_asset_keeps_only_catalogue_fields():
    assert slim_asset(VSN) == {
        "id": VSN["id"], "symbol": "VSN", "name": "Vision",
        "type": "cryptocoin", "group": "token", "isin": None,
    }


async def test_resolve_caches_slim_records():
    cache: dict = {}
    client = _Client({VSN["id"]: VSN})
    directory = AssetDirectory(client, cache, _unexpected_refusal)
    await directory.async_resolve([VSN["id"]])
    assert directory.get(VSN["id"]) == slim_asset(VSN)
    assert cache == {VSN["id"]: slim_asset(VSN)}


async def test_a_holding_is_looked_up_by_its_id_alone_with_the_key():
    """What the directory asks the real client for: one page of /assets,
    filtered by the asset's id, with the Portfolio's key -- since 2026-10-28
    Bitpanda names an asset only to a key with Trade (Read). Without the
    filter the lookup would
    still name the holding -- by walking the whole catalogue page by page --
    so the query itself is pinned: the mock matches a registered query as a
    subset and would not notice a parameter lost or added."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/assets", json={"data": [VSN], "has_next_page": False})
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            directory = AssetDirectory(
                BitpandaApiClient("portfolio-key", session), {}, _unexpected_refusal
            )
            await directory.async_resolve([VSN["id"]])
    assert mocker.call_count == 1
    _, url, _, headers = mocker.mock_calls[0]
    assert url.query_string == f"page_size=100&id={VSN['id']}"
    assert {name.lower(): value for name, value in headers.items()}["x-api-key"] == "portfolio-key"
    assert directory.get(VSN["id"]) == slim_asset(VSN)


async def test_a_refused_key_ends_the_pass_and_asks_for_a_new_one():
    """Bitpanda refuses the first lookup: the key lacks Trade (Read), and
    every further lookup would be refused too. The pass ends and the
    directory asks for a new key -- once."""
    refusals = []
    client = _Client({VSN["id"]: VSN, BTC["id"]: BTC}, refuse={VSN["id"], BTC["id"]})
    directory = AssetDirectory(client, {}, lambda: refusals.append(True))
    await directory.async_resolve([VSN["id"], BTC["id"]])
    assert client.calls == [VSN["id"]]
    assert refusals == [True]
    assert directory.get(VSN["id"]) is None


async def test_a_401_after_an_answer_is_that_assets_failure():
    """After a lookup Bitpanda answered, a 401 says nothing about the key:
    that asset's lookup failed, the pass ends, and no new key is asked for."""
    refusals = []
    client = _Client({VSN["id"]: VSN, BTC["id"]: BTC}, refuse={BTC["id"]})
    directory = AssetDirectory(client, {}, lambda: refusals.append(True))
    await directory.async_resolve([VSN["id"], BTC["id"]])
    assert client.calls == [VSN["id"], BTC["id"]]
    assert refusals == []
    assert directory.get(VSN["id"]) == slim_asset(VSN)
    assert directory.get(BTC["id"]) is None


async def test_resolve_skips_cached_ids():
    client = _Client({VSN["id"]: VSN})
    directory = AssetDirectory(client, {VSN["id"]: slim_asset(VSN)}, _unexpected_refusal)
    await directory.async_resolve([VSN["id"]])
    assert client.calls == []


async def test_a_failed_lookup_ends_the_pass_and_is_asked_for_last_next_time():
    """A timeout or a connection error makes the next lookup likely to fail
    the same way: with /assets hanging, going on would hold the first
    refresh -- inside setup -- for up to 15 s per held asset. The pass ends
    there, and the next refresh asks again -- for the one that failed last."""
    client = _Client({VSN["id"]: VSN, BTC["id"]: BTC}, fail={VSN["id"]})
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    await directory.async_resolve([VSN["id"], BTC["id"]])
    assert client.calls == [VSN["id"]]
    assert directory.get(BTC["id"]) is None

    client.fail = set()
    await directory.async_resolve([VSN["id"], BTC["id"]])
    assert client.calls == [VSN["id"], BTC["id"], VSN["id"]]
    assert directory.get(VSN["id"]) == slim_asset(VSN)
    assert directory.get(BTC["id"]) == slim_asset(BTC)


def _healthy(number: int) -> dict:
    return {"id": f"{number:08d}-0000-0000-0000-000000000000", "symbol": f"H{number}",
            "name": f"Healthy {number}", "type": "cryptocoin", "group": "coin"}


async def test_an_asset_whose_lookup_keeps_failing_holds_up_no_other():
    """Ahead of four healthy holdings in /portfolio's order, one asset whose
    own lookup always fails: each pass still makes at most one failed
    request, and the next pass asks for the others first."""
    bad = "ffffffff-0000-0000-0000-000000000000"
    healthy = [_healthy(number) for number in range(1, 5)]
    client = _Client({record["id"]: record for record in healthy}, fail={bad})
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    held = [bad, *(record["id"] for record in healthy)]

    for _ in range(2):
        before = len(client.calls)
        await directory.async_resolve(held)
        assert client.calls[before:].count(bad) <= 1

    assert [directory.get(record["id"]) for record in healthy] == [
        slim_asset(record) for record in healthy
    ]


async def test_assets_whose_lookups_keep_failing_take_turns():
    """Asked for last does not mean never again: of two failing assets, the
    one that failed longer ago goes first, so each is retried in turn, and
    one that recovers is resolved on its next turn at the latest."""
    first, second = (f"{letter * 8}-0000-0000-0000-000000000000" for letter in "ef")
    client = _Client({}, fail={first, second})
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    for _ in range(4):
        await directory.async_resolve([first, second])
    assert client.calls == [first, second, first, second]

    client.fail = {first}
    client.records = {second: {**_healthy(9), "id": second}}
    for _ in range(2):
        await directory.async_resolve([first, second])
    assert directory.get(second) is not None


async def test_an_asset_missing_from_the_catalogue_does_not_end_the_pass():
    """An empty answer is a real answer, not a failure: that asset is marked
    unknown and the next one is asked for."""
    client = _Client({BTC["id"]: BTC})
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    await directory.async_resolve([VSN["id"], BTC["id"]])
    assert client.calls == [VSN["id"], BTC["id"]]
    assert directory.get(BTC["id"]) == slim_asset(BTC)


async def test_a_rate_limit_stops_the_round():
    client = _Client({VSN["id"]: VSN, BTC["id"]: BTC}, rate_limit=True)
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    await directory.async_resolve([VSN["id"], BTC["id"]])
    assert client.calls == [VSN["id"]]


async def test_an_asset_missing_from_the_catalogue_is_asked_for_again_a_day_later(freezer):
    """Not in the catalogue -- at least not yet: not asked for again at every
    refresh, but a day later, and named once the catalogue lists it. The
    wallet then comes without a restart."""
    client = _Client({})
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    await directory.async_resolve([VSN["id"]])
    freezer.tick(UNKNOWN_ASSET_RETRY - timedelta(seconds=1))
    await directory.async_resolve([VSN["id"]])
    assert client.calls == [VSN["id"]]
    assert directory.is_unlisted(VSN["id"])

    client.records = {VSN["id"]: VSN}
    freezer.tick(timedelta(seconds=1))
    await directory.async_resolve([VSN["id"]])
    assert client.calls == [VSN["id"], VSN["id"]]
    assert directory.get(VSN["id"]) == slim_asset(VSN)
    assert not directory.is_unlisted(VSN["id"])


async def test_an_asset_still_missing_a_day_later_waits_another_day(freezer):
    """Each answer without the asset starts the day again: one request a
    day, never one at every refresh."""
    client = _Client({})
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    await directory.async_resolve([VSN["id"]])
    freezer.tick(UNKNOWN_ASSET_RETRY)
    await directory.async_resolve([VSN["id"]])
    freezer.tick(timedelta(minutes=5))
    await directory.async_resolve([VSN["id"]])
    assert client.calls == [VSN["id"], VSN["id"]]


async def test_a_failed_daily_lookup_tells_nothing(freezer):
    """The catalogue did not list the asset; a day later its lookup fails.
    That changes nothing: the asset stays unlisted, and the next refresh
    asks again -- until an answer without it restarts the day."""
    client = _Client({})
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    await directory.async_resolve([VSN["id"]])
    freezer.tick(UNKNOWN_ASSET_RETRY)
    client.fail = {VSN["id"]}
    await directory.async_resolve([VSN["id"]])
    assert directory.is_unlisted(VSN["id"])

    client.fail = set()
    freezer.tick(timedelta(minutes=5))
    await directory.async_resolve([VSN["id"]])
    freezer.tick(timedelta(minutes=5))
    await directory.async_resolve([VSN["id"]])
    assert client.calls == [VSN["id"]] * 3
    assert directory.is_unlisted(VSN["id"])


async def test_an_asset_missing_from_the_catalogue_is_logged_once_at_info(caplog, freezer):
    """Nothing the user can do about it, so info, not a warning -- and once,
    not again at every daily retry."""
    client = _Client({})
    directory = AssetDirectory(client, {}, _unexpected_refusal)
    with caplog.at_level(logging.DEBUG):
        await directory.async_resolve([VSN["id"]])
        freezer.tick(UNKNOWN_ASSET_RETRY)
        await directory.async_resolve([VSN["id"]])
    assert client.calls == [VSN["id"], VSN["id"]]
    assert [
        (record.levelno, record.getMessage())
        for record in caplog.records
        if record.levelno >= logging.INFO and VSN["id"] in record.getMessage()
    ] == [
        (
            logging.INFO,
            f"Held asset {VSN['id']} is not in Bitpanda's asset catalogue, at least not"
            " yet: it gets no wallet device until it is, and its value still counts in"
            " Total value",
        )
    ]
