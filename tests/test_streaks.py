"""Tests for the streak-confirmation rule shared by count and time."""
from datetime import UTC, datetime, timedelta

from custom_components.bitpanda.const import FAILURE_TOLERANCE
from custom_components.bitpanda.portfolio_model import confirmed
from custom_components.bitpanda.streaks import FailureStreak, streak_confirmed

_I = timedelta(minutes=5)
_T0 = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def test_three_in_a_row_two_intervals_apart_confirm():
    assert streak_confirmed(3, _T0, _T0 + 2 * _I, needed=3, interval=_I)


def test_fewer_than_needed_never_confirm():
    assert not streak_confirmed(2, _T0, _T0 + 10 * _I, needed=3, interval=_I)


def test_the_clock_grace_is_five_seconds():
    assert streak_confirmed(3, _T0, _T0 + 2 * _I - timedelta(seconds=5), needed=3, interval=_I)
    assert not streak_confirmed(3, _T0, _T0 + 2 * _I - timedelta(seconds=6), needed=3, interval=_I)


def test_many_quick_ones_never_confirm_sooner():
    assert not streak_confirmed(50, _T0, _T0 + _I, needed=3, interval=_I)


def test_a_failure_streak_counts_from_its_first_request():
    streak = FailureStreak()
    assert not streak.confirmed(_I)
    for minutes in (0, 5, 10):
        streak.add(_T0 + timedelta(minutes=minutes))
    assert (streak.count, streak.first, streak.last) == (3, _T0, _T0 + 2 * _I)
    assert streak.confirmed(_I)


def test_a_failure_streak_spans_its_requests_whatever_order_they_end_in():
    """Refreshes that overlap end in any order: the streak runs from the
    earliest request to the latest, however the failures come in. Added
    as they end here -- asked for at 10, 0 and 5 minutes -- they confirm
    as they would have in order."""
    streak = FailureStreak()
    for minutes in (10, 0, 5):
        streak.add(_T0 + timedelta(minutes=minutes))
    assert (streak.count, streak.first, streak.last) == (3, _T0, _T0 + 2 * _I)
    assert streak.confirmed(_I)


def test_a_failure_streak_needs_failure_tolerance_failures():
    streak = FailureStreak()
    streak.add(_T0)
    streak.add(_T0 + 10 * _I)
    assert FAILURE_TOLERANCE == 3
    assert not streak.confirmed(_I)


def test_the_wallet_rule_is_the_same_rule():
    ten_minutes = timedelta(minutes=10)
    assert confirmed(3, _T0, _T0 + ten_minutes - timedelta(seconds=5))
    assert not confirmed(3, _T0, _T0 + ten_minutes - timedelta(seconds=6))
    assert not confirmed(2, _T0, _T0 + timedelta(hours=1))
