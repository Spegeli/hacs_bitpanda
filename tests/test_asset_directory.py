"""Tests for the asset directory that names the holdings."""
import logging

from custom_components.bitpanda.api import BitpandaApiError, BitpandaRateLimitError
from custom_components.bitpanda.assets import AssetDirectory, slim_asset

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
    def __init__(self, records=None, fail=None, rate_limit=False):
        self.records = records or {}
        self.fail = fail or set()
        self.rate_limit = rate_limit
        self.calls: list[str] = []

    async def async_get_assets(self, *, asset_id=None, **_):
        self.calls.append(asset_id)
        if self.rate_limit:
            raise BitpandaRateLimitError("Rate limited on /assets")
        if asset_id in self.fail:
            raise BitpandaApiError("Timeout for /assets")
        record = self.records.get(asset_id)
        return [record] if record else []


def test_slim_asset_keeps_only_catalogue_fields():
    assert slim_asset(VSN) == {
        "id": VSN["id"], "symbol": "VSN", "name": "Vision",
        "type": "cryptocoin", "group": "token", "isin": None,
    }


async def test_resolve_caches_slim_records():
    cache: dict = {}
    client = _Client({VSN["id"]: VSN})
    directory = AssetDirectory(client, cache)
    await directory.async_resolve([VSN["id"]])
    assert directory.get(VSN["id"]) == slim_asset(VSN)
    assert cache == {VSN["id"]: slim_asset(VSN)}


async def test_resolve_skips_cached_ids():
    client = _Client({VSN["id"]: VSN})
    directory = AssetDirectory(client, {VSN["id"]: slim_asset(VSN)})
    await directory.async_resolve([VSN["id"]])
    assert client.calls == []


async def test_one_failed_lookup_does_not_stop_the_others():
    client = _Client({BTC["id"]: BTC}, fail={VSN["id"]})
    directory = AssetDirectory(client, {})
    await directory.async_resolve([VSN["id"], BTC["id"]])
    assert directory.get(VSN["id"]) is None
    assert directory.get(BTC["id"]) == slim_asset(BTC)


async def test_a_rate_limit_stops_the_round():
    client = _Client({VSN["id"]: VSN, BTC["id"]: BTC}, rate_limit=True)
    directory = AssetDirectory(client, {})
    await directory.async_resolve([VSN["id"], BTC["id"]])
    assert client.calls == [VSN["id"]]


async def test_an_asset_missing_from_the_catalogue_is_asked_for_once(caplog):
    client = _Client({})
    directory = AssetDirectory(client, {})
    with caplog.at_level(logging.WARNING):
        await directory.async_resolve([VSN["id"]])
        await directory.async_resolve([VSN["id"]])
    assert client.calls == [VSN["id"]]
    assert caplog.text.count(VSN["id"]) == 1
