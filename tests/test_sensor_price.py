"""Tests for price sensor display precision."""
from custom_components.bitpanda.sensor import display_precision


def test_precision_for_large_values():
    assert display_precision(73331.48806018) == 2
    assert display_precision(29955.20592928) == 2
    assert display_precision(23.395) == 2
    assert display_precision(10.0) == 2


def test_precision_scales_down_for_small_values():
    assert display_precision(5.0) == 4
    assert display_precision(0.5) == 5
    assert display_precision(0.05810025) == 6
    assert display_precision(0.0005) == 7
    assert display_precision(0.00000032) == 8


def test_precision_never_derived_from_decimal_count():
    """Every API price has exactly 8 decimals, so counting them is useless."""
    assert display_precision(90.93000000) == 2


def test_precision_handles_zero_and_none():
    assert display_precision(0.0) == 2
    assert display_precision(None) == 2
