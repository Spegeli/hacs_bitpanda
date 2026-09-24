"""Tests for FX rate derivation from the portfolio fiat entry."""
from custom_components.bitpanda.fx import derive_rate, fiat_entry


def _fiat(balance, available):
    return {
        "currency_id": "cur-eur",
        "balance": {"value": balance, "currency_id": "cur-eur"},
        "available_balance": {"value": available, "currency_id": "cur-eur"},
    }


def _asset():
    return {"asset_id": "a", "balance": {"value": "1"},
            "available_balance": {"value": "1"},
            "currency_balance": {"value": "10"}}


def test_fiat_entry_picks_the_entry_without_asset_id():
    entries = [_asset(), _fiat("0.01", "0.01")]
    assert fiat_entry(entries)["currency_id"] == "cur-eur"


def test_fiat_entry_returns_none_when_only_assets():
    assert fiat_entry([_asset()]) is None


def test_derive_rate_matches_measured_usd_rate():
    """0.01 EUR -> 0.0113755257 USD, measured 2026-09-24."""
    rate = derive_rate([_fiat("0.01", "0.01")], [_fiat("0.01", "0.0113755257")])
    assert abs(rate - 1.13755257) < 1e-9


def test_derive_rate_uses_available_not_balance():
    """`balance` is rounded to 2 decimals and would give 11.0 instead of 11.26."""
    rate = derive_rate([_fiat("0.01", "0.01")], [_fiat("0.11", "0.1125987633")])
    assert abs(rate - 11.25987633) < 1e-9


def test_derive_rate_uses_available_not_balance_on_base_side():
    """A base-side bug reading `balance` would halve the rate here."""
    rate = derive_rate([_fiat("0.02", "0.0125")], [_fiat("0.01", "0.025")])
    assert abs(rate - 2.0) < 1e-9


def test_derive_rate_returns_none_without_fiat_entry():
    assert derive_rate([_asset()], [_asset()]) is None


def test_derive_rate_returns_none_on_zero_base():
    assert derive_rate([_fiat("0", "0")], [_fiat("0", "0")]) is None


def test_derive_rate_returns_none_on_unparsable_value():
    assert derive_rate([_fiat("0.01", "x")], [_fiat("0.01", "0.02")]) is None


def test_derive_rate_returns_none_on_non_finite_base():
    """float() parses "nan" and "inf" happily; they must not reach the division."""
    for bad in ("nan", "inf", "-inf"):
        assert derive_rate([_fiat("0.01", bad)], [_fiat("0.01", "0.02")]) is None


def test_derive_rate_returns_none_on_non_finite_target():
    for bad in ("nan", "inf", "-inf"):
        assert derive_rate([_fiat("0.01", "0.01")], [_fiat("0.01", bad)]) is None
