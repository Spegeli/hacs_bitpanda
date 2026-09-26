"""Tests for symbol resolution, disambiguation and categorisation."""
import pytest

from custom_components.bitpanda.assets import (
    ASSET_CATEGORY_FILTERS,
    CATEGORY_OTHER,
    asset_category,
    asset_label,
    asset_label_map,
    is_legacy_supported,
    pick_legacy,
    resolve_asset,
)

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


# --- asset_label_map / resolve_asset --------------------------------------
#
# The asset picker is a SelectSelector with custom_value=True; the frontend's
# ha-picker-field shows an option's raw VALUE with no way to render its label
# instead (verified in the frontend source). Making the value the label, not
# the id, fixes that -- but labels must stay unique within one listing first.
# Apple listed under both stock families -- same name, symbol and ISIN, only
# type and group differ -- is the real shape of that collision.


def _stock_pair(isin="US0378331005"):
    stock = {
        "id": "11111111-2222-3333-4444-555555555555",
        "symbol": "AAPL",
        "name": "Apple",
        "isin": isin,
        "type": "security",
        "group": "stock",
    }
    equity = {
        "id": "66666666-7777-8888-9999-000000000000",
        "symbol": "AAPL",
        "name": "Apple",
        "isin": isin,
        "type": "equity_security",
        "group": "equity_stock",
    }
    return stock, equity


def test_asset_label_map_passes_unique_labels_through():
    btc = {"id": "btc-id", "symbol": "BTC", "name": "Bitcoin", "type": "cryptocoin", "group": "coin"}
    eth = {"id": "eth-id", "symbol": "ETH", "name": "Ethereum", "type": "cryptocoin", "group": "coin"}
    assert asset_label_map([btc, eth]) == {"Bitcoin / BTC": btc, "Ethereum / ETH": eth}


def test_asset_label_map_suffixes_a_duplicate_label_with_type_and_group():
    stock, equity = _stock_pair()
    assert asset_label_map([stock, equity]) == {
        "Apple / AAPL / US0378331005 · security/stock": stock,
        "Apple / AAPL / US0378331005 · equity_security/equity_stock": equity,
    }


def test_asset_label_map_appends_the_asset_id_when_the_suffix_still_collides():
    """Same name, symbol, type and group too -- only the id still differs."""
    first = {
        "id": "11111111-0000-0000-0000-000000000000",
        "symbol": "DUP", "name": "Duplicate", "type": "cryptocoin", "group": "coin",
    }
    second = {
        "id": "22222222-0000-0000-0000-000000000000",
        "symbol": "DUP", "name": "Duplicate", "type": "cryptocoin", "group": "coin",
    }
    assert asset_label_map([first, second]) == {
        "Duplicate / DUP · cryptocoin/coin · 11111111": first,
        "Duplicate / DUP · cryptocoin/coin · 22222222": second,
    }


def test_asset_label_map_keeps_a_suffixed_label_from_colliding_with_a_plain_one():
    """Uniqueness must be global, not just within each raw-label group: a
    computed type/group suffix can, by construction, equal a *different*
    asset's own unrelated plain label. The escalated asset must move again
    instead of silently overwriting the one already there."""
    lookalike = {
        "id": "aaaaaaaa-0000-0000-0000-000000000000",
        "symbol": "SYM · alpha/one", "name": "Echo", "type": "gamma", "group": "three",
    }
    first = {
        "id": "bbbbbbbb-0000-0000-0000-000000000000",
        "symbol": "SYM", "name": "Echo", "type": "alpha", "group": "one",
    }
    second = {
        "id": "cccccccc-0000-0000-0000-000000000000",
        "symbol": "SYM", "name": "Echo", "type": "beta", "group": "two",
    }
    # By construction: lookalike's own (otherwise-unique) plain label is
    # exactly the string `first` computes as its type/group suffix.
    assert asset_label(lookalike) == "Echo / SYM · alpha/one"

    result = asset_label_map([lookalike, first, second])

    assert len(result) == 3
    assert result["Echo / SYM · alpha/one"] == lookalike
    assert first in result.values()
    assert second in result.values()


def test_asset_label_map_returns_exactly_one_entry_per_asset_in_a_mixed_set():
    """A realistic mixed bag: some assets unique, some needing the
    type/group suffix, some needing the id too. Every asset must still get
    exactly one entry -- none dropped, none merged into another's."""
    btc = {"id": "btc-id", "symbol": "BTC", "name": "Bitcoin", "type": "cryptocoin", "group": "coin"}
    stock, equity = _stock_pair()
    first = {
        "id": "11111111-0000-0000-0000-000000000000",
        "symbol": "DUP", "name": "Duplicate", "type": "cryptocoin", "group": "coin",
    }
    second = {
        "id": "22222222-0000-0000-0000-000000000000",
        "symbol": "DUP", "name": "Duplicate", "type": "cryptocoin", "group": "coin",
    }
    listing = [btc, stock, equity, first, second]

    result = asset_label_map(listing)

    assert len(result) == len(listing)
    assert all(asset in result.values() for asset in listing)


def test_asset_label_map_is_empty_for_an_empty_listing():
    assert asset_label_map([]) == {}


def test_resolve_asset_finds_a_record_by_its_label():
    stock, equity = _stock_pair()
    label_map = asset_label_map([stock, equity])
    assert resolve_asset("Apple / AAPL / US0378331005 · security/stock", label_map, [stock, equity]) is stock


def test_resolve_asset_accepts_a_typed_or_pasted_id_too():
    stock, equity = _stock_pair()
    label_map = asset_label_map([stock, equity])
    assert resolve_asset(equity["id"], label_map, [stock, equity]) is equity


def test_resolve_asset_is_none_for_anything_else():
    stock, equity = _stock_pair()
    label_map = asset_label_map([stock, equity])
    assert resolve_asset("nonsense", label_map, [stock, equity]) is None


# --- asset_category ----------------------------------------------------------
#
# Every catalogue family in tests/fixtures/assets-sample.json, measured live:
# stocks, ETFs and ETCs each come in two families, crypto in several groups.


@pytest.mark.parametrize(
    ("symbol", "type_", "category"),
    [
        ("BTC", "cryptocoin", "crypto"),  # group coin
        ("GHST", "cryptocoin", "crypto"),  # group token
        ("BTC2L", "cryptocoin", "crypto"),  # group leveraged_token
        ("517", "equity_security", "stock"),  # group equity_stock
        ("ESSITYB", "security", "stock"),  # group stock
        ("EXIA", "equity_security", "etf"),  # group equity_etf
        ("XMTH", "equity_security", "etf"),  # group equity_complex_etf
        ("SXR8", "security", "etf"),  # group etf
        ("PPFB", "equity_security", "etc"),  # group equity_complex_etc
        ("ALUMINIUM", "security", "etc"),  # group etc
        ("BCI5", "index", "index"),
        ("XAU", "commodity", "metal"),
        ("BCPEUR", "security", "other"),  # Cash Plus, group fiat_earn
    ],
)
def test_asset_category_of_every_catalogue_family(symbol, type_, category):
    asset = next(a for a in _catalogue() if a["symbol"] == symbol and a["type"] == type_)
    assert asset_category(asset) == category


def test_asset_category_is_other_where_no_filter_fits():
    assert CATEGORY_OTHER == "other"
    assert asset_category({"type": "commodity", "group": "energy"}) == "other"
    assert asset_category({"type": "equity_security"}) == "other"
    assert asset_category({}) == "other"


def test_every_filter_sorts_into_its_own_category():
    """No category's filter is claimed by an earlier category first."""
    for category, filters in ASSET_CATEGORY_FILTERS.items():
        for type_, group in filters:
            assert asset_category({"type": type_, "group": group or "any"}) == category
