"""Tests for symbol resolution, disambiguation and categorisation."""
from custom_components.bitpanda.assets import asset_label, is_legacy_supported, pick_legacy

from tests.conftest import load_fixture


def _asset(symbol, asset_id, type_, group):
    return {"id": asset_id, "symbol": symbol, "name": symbol,
            "type": type_, "group": group}


def _catalogue() -> list[dict]:
    return load_fixture("assets-sample.json")


def _by_symbol(symbol: str) -> list[dict]:
    return [a for a in _catalogue() if a["symbol"] == symbol]


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
# tests/fixtures/assets-sample.json -- the exact collision, measured live, that
# once pointed a migrated gold wallet at a stock.


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
    legacy-supported types alone, so this is synthesised.
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
    legacy-supported types, so this pins the prefix narrowing itself
    (crypto/metal/index) rather than relying on real data to exercise it.
    Without the narrowing, both `cryptocoin_` and `commodity_metal_` would
    see two legacy-supported survivors and return None instead of the right
    one.
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
