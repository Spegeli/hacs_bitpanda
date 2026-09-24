"""Tests for portfolio normalisation."""
from custom_components.bitpanda.coordinator import parse_portfolio


def _asset_entry(asset_id, balance, available, value, ret_pct="10.5"):
    return {
        "asset_id": asset_id,
        "balance": {"value": balance},
        "available_balance": {"value": available},
        "currency_balance": {"value": value},
        "invested_amount": {"value": "100.00"},
        "average_buy_price": {"value": "1.2345"},
        "total_return": {"value": "10.00"},
        "total_return_percent": ret_pct,
    }


def _fiat_entry(currency_id, balance):
    return {
        "currency_id": currency_id,
        "balance": {"value": balance},
        "available_balance": {"value": balance},
    }


def test_parse_splits_asset_and_fiat_entries():
    data = parse_portfolio(
        [_asset_entry("a1", "10", "10", "25.50"), _fiat_entry("cur-eur", "0.01")],
        rate=None,
    )
    assert set(data.holdings) == {"a1"}
    assert data.fiat == {"cur-eur": 0.01}


def test_parse_computes_staked_amount():
    """balance minus available_balance is the amount locked in Earn."""
    data = parse_portfolio([_asset_entry("a1", "21466.95", "0", "836.17")], rate=None)
    assert data.holdings["a1"].staked == 21466.95


def test_parse_marks_liquid_holding_as_unstaked():
    data = parse_portfolio([_asset_entry("a1", "5", "5", "12.00")], rate=None)
    assert data.holdings["a1"].staked == 0.0


def test_parse_reads_performance_fields():
    data = parse_portfolio([_asset_entry("a1", "1", "1", "2", "-67.98")], rate=None)
    h = data.holdings["a1"]
    assert h.invested == 100.00
    assert h.avg_buy_price == 1.2345
    assert h.total_return == 10.00
    assert h.total_return_pct == -67.98


def test_parse_uses_currency_balance_directly_never_multiplying():
    """Issue #7: index and fiat balances are already money. Never multiply."""
    data = parse_portfolio([_asset_entry("bci5", "0.02012", "0.02012", "431.44")],
                           rate=None)
    assert data.holdings["bci5"].value == 431.44


def test_total_sums_holdings_and_fiat():
    data = parse_portfolio(
        [_asset_entry("a1", "1", "1", "10.00"),
         _asset_entry("a2", "1", "1", "5.50"),
         _fiat_entry("cur-eur", "0.01")],
        rate=None,
    )
    assert data.total == 15.51


def test_parse_tolerates_missing_optional_fields():
    """Fiat entries have no currency_balance; assets may lack performance data."""
    minimal = {"asset_id": "a1", "balance": {"value": "1"},
               "available_balance": {"value": "1"}}
    data = parse_portfolio([minimal], rate=None)
    h = data.holdings["a1"]
    assert h.value == 0.0
    assert h.invested is None


def test_parse_skips_unparsable_entry_without_raising():
    bad = {"asset_id": "a1", "balance": {"value": "not-a-number"},
           "available_balance": {"value": "1"}}
    data = parse_portfolio([bad, _asset_entry("a2", "1", "1", "3.00")], rate=None)
    assert set(data.holdings) == {"a2"}
