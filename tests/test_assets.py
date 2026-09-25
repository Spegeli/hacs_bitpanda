"""Tests for symbol resolution, disambiguation and categorisation."""
import asyncio

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from custom_components.bitpanda.assets import (
    AssetResolver,
    asset_label,
    category_of,
    is_legacy_supported,
    pick_legacy,
)
from custom_components.bitpanda.const import API_BASE_URL

from tests.conftest import load_fixture


def _asset(symbol, asset_id, type_, group):
    return {"id": asset_id, "symbol": symbol, "name": symbol,
            "type": type_, "group": group}


def _catalogue() -> list[dict]:
    return load_fixture("assets-sample.json")


def _by_symbol(symbol: str) -> list[dict]:
    return [a for a in _catalogue() if a["symbol"] == symbol]


# --- AssetResolver.async_candidates ------------------------------------------
#
# A symbol is not unique in the 14000-asset catalogue -- XAU alone names both
# a stock and a metal (see task-23-brief.md) -- so candidates returns every
# match instead of guessing. It no longer caches them itself (task-23-review.md,
# finding 9): the migration remembers only whichever one `pick_legacy`
# chooses, so an unrelated candidate sharing the symbol (the stock, say)
# never rides along into the persisted cache next to the one actually picked.


async def test_candidates_returns_every_match():
    xau = _by_symbol("XAU")
    assert len(xau) == 2

    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets?page_size=100&symbol=XAU",
            json={"data": xau, "has_next_page": False},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            resolver = AssetResolver(client, {})
            found = await resolver.async_candidates("XAU")

    assert {a["id"] for a in found} == {a["id"] for a in xau}
    # Not cached by async_candidates itself -- nothing has been chosen yet.
    for asset in xau:
        assert resolver.get_cached(asset["id"]) is None


async def test_candidates_of_unknown_symbol_returns_empty_list():
    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/assets?page_size=100&symbol=NOPE",
            json={"data": [], "has_next_page": False},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            resolver = AssetResolver(client, {})
            assert await resolver.async_candidates("NOPE") == []


async def test_candidates_propagates_auth_error():
    """A bad key must not look like a missing symbol."""
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/assets?page_size=100&symbol=BTC", status=401)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            resolver = AssetResolver(client, {})
            with pytest.raises(BitpandaAuthError):
                await resolver.async_candidates("BTC")


async def test_candidates_propagates_rate_limit_error():
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/assets?page_size=100&symbol=BTC", status=429)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            resolver = AssetResolver(client, {})
            with pytest.raises(BitpandaRateLimitError):
                await resolver.async_candidates("BTC")


async def test_candidates_propagates_a_plain_api_error():
    """A 5xx, timeout or reset connection is not "no such symbol" either.
    Only an empty 200 may read as that -- the migration, the sole caller,
    drops an asset for good on it, but aborts and retries on an error.
    """
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/assets?page_size=100&symbol=BTC", status=503)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            resolver = AssetResolver(client, {})
            with pytest.raises(BitpandaApiError):
                await resolver.async_candidates("BTC")


async def test_candidates_without_client_returns_empty_list():
    resolver = AssetResolver(None, {})
    assert await resolver.async_candidates("BTC") == []


async def test_candidates_of_empty_symbol_returns_empty_list_without_a_request():
    """A bare-prefix v1 wallet id (`legacy_symbol("cryptocoin_")` is `""`)
    must never reach the API: an empty `symbol` drops the query filter
    entirely (`api.py`'s `if symbol:`) and would page through the whole
    ~14,000-asset catalogue instead of finding nothing (task-23-review.md,
    finding 10). No mock is registered below, so an attempted request raises
    instead of silently succeeding.
    """
    with mock_aiohttp_client() as mocker:
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            client = BitpandaApiClient("key", session)
            resolver = AssetResolver(client, {})
            assert await resolver.async_candidates("") == []
        assert mocker.call_count == 0


# --- AssetResolver: cache and remember ---------------------------------------


def test_get_cached_by_id():
    resolver = AssetResolver(
        None, {"uuid-btc": _asset("BTC", "uuid-btc", "cryptocoin", "coin")}
    )
    assert resolver.get_cached("uuid-btc")["symbol"] == "BTC"
    assert resolver.get_cached("uuid-missing") is None


def test_resolver_heals_a_symbol_keyed_cache_from_an_earlier_build():
    """An earlier dev build persisted `asset_cache` keyed by symbol instead
    of by id. Trusting the cache's own outer keys would keep only the
    portfolio sensor working and silently drop every tracked price/wallet
    sensor at setup (task-23-review.md, finding 6). Re-keying from each
    record's own `id` heals such an entry at zero cost, the same idiom
    `portfolio_breakdown` and the options flow's `remove` step already use.
    """
    symbol_keyed_cache = {"BTC": _asset("BTC", "uuid-btc", "cryptocoin", "coin")}
    resolver = AssetResolver(None, symbol_keyed_cache)
    assert resolver.get_cached("uuid-btc")["symbol"] == "BTC"


def test_remember_adds_to_cache_by_id():
    resolver = AssetResolver(None, {})
    resolver.remember(_asset("BTC", "uuid-btc", "cryptocoin", "coin"))
    assert resolver.get_cached("uuid-btc")["symbol"] == "BTC"


def test_remember_ignores_an_asset_with_no_id():
    resolver = AssetResolver(None, {})
    resolver.remember({"symbol": "BTC"})
    assert resolver.as_dict() == {}


def test_as_dict_is_keyed_by_asset_id_and_holds_two_records_sharing_a_symbol():
    xau = _by_symbol("XAU")
    resolver = AssetResolver(None, {})
    for asset in xau:
        resolver.remember(asset)
    result = resolver.as_dict()
    assert set(result) == {a["id"] for a in xau}
    for asset in xau:
        assert result[asset["id"]]["id"] == asset["id"]


# --- is_legacy_supported ------------------------------------------------------
#
# What the legacy (v1) API could ever have tracked: crypto, indices and
# metals -- never a stock or an ETF, which the legacy API never offered.


def test_is_legacy_supported_true_for_crypto_index_and_metal():
    assert is_legacy_supported(_asset("BTC", "i", "cryptocoin", "coin")) is True
    assert is_legacy_supported(_asset("BCI5", "i", "index", "index")) is True
    assert is_legacy_supported(_asset("XAU", "i", "commodity", "metal")) is True


def test_is_legacy_supported_false_for_a_stock():
    assert is_legacy_supported(_asset("XAU", "i", "equity_security", "equity_stock")) is False


# --- pick_legacy --------------------------------------------------------------
#
# Uses the real XAU (stock + metal) and BNB (stock + coin) pairs committed to
# tests/fixtures/assets-sample.json -- the exact collision measured live
# (task-23-brief.md) that pointed a migrated gold wallet at a stock.


def test_pick_legacy_xau_bare_symbol_gives_the_metal():
    """prefix=None is what a v1 price tracker (a bare symbol) supplies."""
    result = pick_legacy(_by_symbol("XAU"), None)
    assert result is not None
    assert result["group"] == "metal"


def test_pick_legacy_xau_with_metal_wallet_prefix_gives_the_metal():
    result = pick_legacy(_by_symbol("XAU"), "commodity_metal_")
    assert result is not None
    assert result["group"] == "metal"


def test_pick_legacy_bnb_with_cryptocoin_prefix_gives_the_coin():
    result = pick_legacy(_by_symbol("BNB"), "cryptocoin_")
    assert result is not None
    assert result["type"] == "cryptocoin"


def test_pick_legacy_fiat_prefix_is_always_none():
    """A currency is not an /assets record at all -- fiat_ keeps nothing,
    regardless of what candidates happen to be passed in.
    """
    assert pick_legacy(_by_symbol("XAU"), "fiat_") is None


def test_pick_legacy_two_legacy_survivors_is_none():
    """Contrived: the real catalogue has zero symbol collisions within the
    legacy-supported types alone (task-23-brief.md), so this is synthesised.
    Dropping with a warning beats silently guessing.
    """
    candidates = [
        _asset("DUP", "id-1", "cryptocoin", "coin"),
        _asset("DUP", "id-2", "index", "index"),
    ]
    assert pick_legacy(candidates, None) is None


def test_pick_legacy_no_candidates_is_none():
    assert pick_legacy([], None) is None


def test_pick_legacy_only_a_stock_candidate_is_none():
    """A stock can never be what a v1 identifier meant -- the legacy API
    never offered one -- so filtering it out must leave zero survivors, not
    fall back to returning it anyway.
    """
    assert pick_legacy(_by_symbol("BNB"), None) is not None  # sanity: BNB has a coin
    stock_only = [a for a in _by_symbol("BNB") if a["type"] == "equity_security"]
    assert pick_legacy(stock_only, None) is None


def test_pick_legacy_narrows_by_prefix_between_two_legacy_types():
    """Synthetic: the real catalogue has zero symbols shared between two
    legacy-supported types (task-23-brief.md), so this pins the prefix
    narrowing itself (crypto/metal/index) rather than relying on real data to
    exercise it (task-23-review.md, finding 12, mutation b2). Without the
    narrowing, both `cryptocoin_` and `commodity_metal_` would see two
    legacy-supported survivors and return None instead of the right one.
    """
    crypto = _asset("DUP", "id-crypto", "cryptocoin", "coin")
    metal = _asset("DUP", "id-metal", "commodity", "metal")
    candidates = [crypto, metal]

    assert pick_legacy(candidates, "cryptocoin_") == crypto
    assert pick_legacy(candidates, "commodity_metal_") == metal
    assert pick_legacy(candidates, None) is None


def test_pick_legacy_index_wallet_prefix_narrows_to_the_index():
    """`index_index_` is the prefix the legacy flow really stored for index
    wallets (index -> index nesting). Synthetic three-way collision, for the
    same reason as the test above: only the narrowing can pick the index.
    """
    crypto = _asset("DUP", "id-crypto", "cryptocoin", "coin")
    metal = _asset("DUP", "id-metal", "commodity", "metal")
    index = _asset("DUP", "id-index", "index", "index")

    assert pick_legacy([crypto, metal, index], "index_index_") == index


# --- category_of ---------------------------------------------------------


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


# --- asset_label ---------------------------------------------------------
#
# One label for both the add_asset and add_wallet pickers: name, symbol and
# -- where one exists -- ISIN, so a user can recognise and search an asset
# by any of the three. The picker's search runs over the label, which is
# what makes ISIN search work.


def test_asset_label_with_isin():
    asset = {"name": "Accenture PLC", "symbol": "ACN", "isin": "IE00B4BNMY34"}
    assert asset_label(asset) == "Accenture PLC / ACN / IE00B4BNMY34"


def test_asset_label_without_isin():
    asset = {"name": "Bitcoin", "symbol": "BTC"}
    assert asset_label(asset) == "Bitcoin / BTC"


def test_asset_label_falls_back_to_symbol_when_name_is_empty():
    asset = {"name": "", "symbol": "XYZ"}
    assert asset_label(asset) == "XYZ / XYZ"
