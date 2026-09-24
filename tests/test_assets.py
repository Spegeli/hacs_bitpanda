"""Tests for symbol resolution and categorisation."""
import aiohttp
from aioresponses import aioresponses

from custom_components.bitpanda.api import BitpandaApiClient
from custom_components.bitpanda.assets import AssetResolver, category_of
from custom_components.bitpanda.const import API_BASE_URL


def _asset(symbol, asset_id, type_, group):
    return {"id": asset_id, "symbol": symbol, "name": symbol,
            "type": type_, "group": group}


async def test_resolve_calls_api_once_then_caches():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        resolver = AssetResolver(client, {})
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/assets?page_size=100&symbol=BTC",
                payload={"data": [_asset("BTC", "uuid-btc", "cryptocoin", "coin")],
                         "has_next_page": False},
            )
            first = await resolver.async_resolve("BTC")
            second = await resolver.async_resolve("BTC")
    assert first["id"] == "uuid-btc"
    assert second["id"] == "uuid-btc"


async def test_resolve_unknown_symbol_returns_none():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        resolver = AssetResolver(client, {})
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/assets?page_size=100&symbol=NOPE",
                payload={"data": [], "has_next_page": False},
            )
            assert await resolver.async_resolve("NOPE") is None


async def test_get_cached_by_id():
    resolver = AssetResolver(None, {"BTC": _asset("BTC", "uuid-btc",
                                                 "cryptocoin", "coin")})
    assert resolver.get_cached("uuid-btc")["symbol"] == "BTC"
    assert resolver.get_cached("uuid-missing") is None


def test_category_of_covers_every_observed_group():
    assert category_of(_asset("BTC", "i", "cryptocoin", "coin")) == "crypto"
    assert category_of(_asset("GHST", "i", "cryptocoin", "token")) == "crypto"
    assert category_of(_asset("BTC2L", "i", "cryptocoin", "leveraged_token")) == "crypto"
    assert category_of(_asset("XAU", "i", "commodity", "metal")) == "metal"
    assert category_of(_asset("BCI5", "i", "index", "index")) == "index"
    assert category_of(_asset("ESSITYB", "i", "security", "stock")) == "stock"
    assert category_of(_asset("517", "i", "equity_security", "equity_stock")) == "stock"
    assert category_of(_asset("SXR8", "i", "security", "etf")) == "etf"
    assert category_of(_asset("EXIA", "i", "equity_security", "equity_etf")) == "etf"
    assert category_of(_asset("ALUMINIUM", "i", "security", "etc")) == "commodity"
    assert category_of(_asset("BCPEUR", "i", "security", "fiat_earn")) == "cash_plus"


def test_category_of_unknown_group_does_not_raise():
    assert category_of(_asset("X", "i", "brand_new", "never_seen")) == "other"
