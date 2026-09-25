"""Tests for FX rate derivation from the two portfolio responses.

PortfolioCoordinator fetches /portfolio twice for a non-EUR display currency:
once valued in EUR, once in the target currency. The rate is the ratio of the
same position in both.
"""
from custom_components.bitpanda.fx import derive_rate

_USD_RATE = 1.13755257  # measured 2026-09-24 from a 0.01 EUR balance


def _fiat(balance, available, currency_id="cur-eur"):
    """A fiat entry. Its nested currency_id labels stay at the wallet's own
    currency even when the values are converted -- as the API does it."""
    return {
        "currency_id": currency_id,
        "balance": {"value": balance, "currency_id": currency_id},
        "available_balance": {"value": available, "currency_id": currency_id},
    }


def _asset(asset_id="a", value="10"):
    return {"asset_id": asset_id, "balance": {"value": "1"},
            "available_balance": {"value": "1"},
            "currency_balance": {"value": value}}


# --- Fiat pairs ------------------------------------------------------------


def test_derive_rate_matches_measured_usd_rate():
    """0.01 EUR -> 0.0113755257 USD, measured 2026-09-24."""
    rate = derive_rate([_fiat("0.01", "0.01")], [_fiat("0.01", "0.0113755257")])
    assert abs(rate - _USD_RATE) < 1e-9


def test_derive_rate_uses_available_not_balance():
    """`balance` is rounded to 2 decimals and would give 11.0 instead of 11.26."""
    rate = derive_rate([_fiat("0.01", "0.01")], [_fiat("0.11", "0.1125987633")])
    assert abs(rate - 11.25987633) < 1e-9


def test_derive_rate_uses_available_not_balance_on_base_side():
    """A base-side bug reading `balance` would halve the rate here."""
    rate = derive_rate([_fiat("0.02", "0.0125")], [_fiat("0.01", "0.025")])
    assert abs(rate - 2.0) < 1e-9


def test_derive_rate_pairs_fiat_wallets_by_currency_id_not_position():
    """Two fiat wallets, listed in a different order in the two responses.
    Pairing the first entry of each would divide the USD wallet's value by
    the EUR wallet's -- a rate of about 455.
    """
    eur_side = [
        _fiat("0.01", "0.01", "cur-eur"),
        _fiat("4.00", "4.00", "cur-usd"),
    ]
    usd_side = [
        _fiat("4.55", "4.55021028", "cur-usd"),
        _fiat("0.01", "0.0113755257", "cur-eur"),
    ]
    assert abs(derive_rate(eur_side, usd_side) - _USD_RATE) < 1e-9


def test_derive_rate_prefers_the_largest_fiat_pair():
    """Of several usable pairs the largest carries the least rounding."""
    eur_side = [_fiat("0.01", "0.01", "cur-eur"), _fiat("4.00", "4.00", "cur-usd")]
    usd_side = [_fiat("0.01", "0.0114", "cur-eur"), _fiat("4.55", "4.55021028", "cur-usd")]
    assert derive_rate(eur_side, usd_side) == 4.55021028 / 4.00


def test_derive_rate_prefers_a_fiat_pair_over_holdings():
    eur_side = [_fiat("0.01", "0.01"), _asset("a1", "836.46")]
    usd_side = [_fiat("0.01", "0.0113755257"), _asset("a1", "951.54")]
    assert abs(derive_rate(eur_side, usd_side) - _USD_RATE) < 1e-9


# --- Unusable values: never a zero, negative or non-finite rate ----------------


def test_derive_rate_returns_none_on_zero_base():
    assert derive_rate([_fiat("0", "0")], [_fiat("0", "0")]) is None


def test_derive_rate_returns_none_on_zero_target():
    """A 0.0 rate would turn every converted price into 0."""
    assert derive_rate([_fiat("0.01", "0.01")], [_fiat("0", "0")]) is None


def test_derive_rate_returns_none_on_negative_values():
    assert derive_rate([_fiat("-0.01", "-0.01")], [_fiat("0.01", "0.0113")]) is None
    assert derive_rate([_fiat("0.01", "0.01")], [_fiat("-0.01", "-0.0113")]) is None


def test_derive_rate_returns_none_on_unparsable_value():
    assert derive_rate([_fiat("0.01", "x")], [_fiat("0.01", "0.02")]) is None


def test_derive_rate_returns_none_on_non_finite_base():
    """float() parses "nan" and "inf" happily; they must not reach the division."""
    for bad in ("nan", "inf", "-inf"):
        assert derive_rate([_fiat("0.01", bad)], [_fiat("0.01", "0.02")]) is None


def test_derive_rate_returns_none_on_non_finite_target():
    for bad in ("nan", "inf", "-inf"):
        assert derive_rate([_fiat("0.01", "0.01")], [_fiat("0.01", bad)]) is None


# --- No usable cash: fall back to the largest holding ---------------------------


def test_derive_rate_falls_back_to_the_largest_holding_without_fiat():
    """A fully invested account has no fiat entry at all. The same holding
    valued in both currencies gives the rate, at no extra request.
    """
    eur_side = [_asset("small", "2.04"), _asset("big", "836.46")]
    usd_side = [_asset("big", "951.54"), _asset("small", "2.32")]
    assert derive_rate(eur_side, usd_side) == 951.54 / 836.46


def test_derive_rate_falls_back_to_holdings_when_the_fiat_balance_is_zero():
    eur_side = [_fiat("0", "0"), _asset("big", "836.46")]
    usd_side = [_fiat("0", "0"), _asset("big", "951.54")]
    assert derive_rate(eur_side, usd_side) == 951.54 / 836.46


def test_derive_rate_ignores_a_holding_missing_from_either_response():
    eur_side = [_asset("big", "836.46")]
    usd_side = [_asset("big", "951.54"), _asset("new", "99999.00")]
    assert derive_rate(eur_side, usd_side) == 951.54 / 836.46


def test_derive_rate_skips_holdings_valued_at_zero():
    eur_side = [_asset("dust", "0.00"), _asset("big", "836.46")]
    usd_side = [_asset("dust", "0.00"), _asset("big", "951.54")]
    assert derive_rate(eur_side, usd_side) == 951.54 / 836.46


def test_derive_rate_refuses_a_fallback_holding_too_small_for_its_rounding():
    """currency_balance is rounded to cents. A 0.04 EUR holding shown as 0.05
    USD would claim a rate of 1.25 against a true ~1.14 -- a wrong rate
    applied to every converted price. Below the bound there is no rate, and
    unheld prices show no value rather than a wrong one.
    """
    eur_side = [_asset("tiny", "0.04")]
    usd_side = [_asset("tiny", "0.05")]
    assert derive_rate(eur_side, usd_side) is None


def test_derive_rate_fallback_bound_is_inclusive_at_fifty():
    assert derive_rate([_asset("a", "49.99")], [_asset("a", "56.87")]) is None
    assert derive_rate([_asset("a", "50.00")], [_asset("a", "56.88")]) == 56.88 / 50.00


def test_derive_rate_is_none_with_neither_cash_nor_holdings():
    assert derive_rate([], []) is None
    assert derive_rate([_asset("dust", "0.00")], [_asset("dust", "0.00")]) is None
