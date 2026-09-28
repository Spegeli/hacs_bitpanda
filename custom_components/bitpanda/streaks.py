"""Pure rule for confirming a streak of same answers by count and time: no
Home Assistant, no network. A wallet's empty answers and a coordinator's
failed refreshes are both counted this way -- portfolio_model.confirmed is
this module's rule under the wallet's own names.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .const import FAILURE_TOLERANCE

# Two regular refreshes are asked for an update interval apart at the least,
# yet the wall clock can read a hair less between them. A few seconds of
# grace keep the answer that completes the regular pace confirming -- fewer
# than the cooldown between two refreshes by hand (const.REFRESH_MIN_COOLDOWN).
CLOCK_GRACE = timedelta(seconds=5)


def streak_confirmed(
    count: int, since: datetime, now: datetime, *, needed: int, interval: timedelta
) -> bool:
    """Whether `count` answers in a row -- the first asked for at `since`,
    the last at `now` -- confirm the streak: `needed` of them at the least,
    spread over (`needed` - 1) `interval`s at the least.

    At the regular pace the answer that completes the count confirms it,
    while answers brought in by hand, however many, never confirm it sooner
    than that pace would (CLOCK_GRACE aside).
    """
    return count >= needed and now - since >= (needed - 1) * interval - CLOCK_GRACE


@dataclass
class FailureStreak:
    """A run of failed refreshes in a row, counted from the first of them.

    `add` records one more failure at the time it was asked for. `first` and
    `last` are the earliest and the latest of those times, whatever order
    the failures come in: refreshes that overlap can end in any order.
    `confirmed` says whether the streak so far -- FAILURE_TOLERANCE of them,
    spread over the regular pace at the least -- outweighs whatever a
    coordinator held before; False while nothing has been added yet, rather
    than confirming an empty streak.
    """

    count: int = 0
    first: datetime | None = None
    last: datetime | None = None

    def add(self, at: datetime) -> None:
        self.first = at if self.first is None else min(self.first, at)
        self.last = at if self.last is None else max(self.last, at)
        self.count += 1

    def confirmed(self, interval: timedelta) -> bool:
        # add() sets first and last together, so they are None together:
        # checking both only narrows their types.
        if self.first is None or self.last is None:
            return False
        return streak_confirmed(
            self.count, self.first, self.last, needed=FAILURE_TOLERANCE, interval=interval
        )
