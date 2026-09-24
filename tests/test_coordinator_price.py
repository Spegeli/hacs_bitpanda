"""Tests for the adaptive price interval and ticker conversion."""
from datetime import timedelta

from custom_components.bitpanda.coordinator import convert_price, price_interval


def test_interval_stays_at_base_for_small_sets():
    assert price_interval(0) == timedelta(seconds=60)
    assert price_interval(10) == timedelta(seconds=60)
    assert price_interval(30) == timedelta(seconds=60)


def test_interval_lengthens_past_the_budget():
    """1800 price requests/hour is the share reserved for tickers."""
    assert price_interval(60) > timedelta(seconds=60)


def test_interval_keeps_every_size_inside_the_budget():
    for count in (1, 10, 30, 50, 100, 500):
        interval = price_interval(count)
        per_hour = count * (3600 / interval.total_seconds())
        assert per_hour <= 1800 + 1


def test_interval_is_never_absurdly_long():
    assert price_interval(5000) <= timedelta(minutes=30)


def test_convert_price_returns_eur_unchanged_when_no_rate():
    assert convert_price("73188.51648958", None) == 73188.51648958


def test_convert_price_applies_rate():
    assert abs(convert_price("100.00000000", 1.13755257) - 113.755257) < 1e-9


def test_convert_price_returns_none_on_garbage():
    assert convert_price("not-a-number", None) is None
