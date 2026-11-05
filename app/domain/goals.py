"""Saving goals: how much is saved and how much to put aside each month."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class GoalProgress:
    target: Decimal
    saved: Decimal
    # None when the goal has no deadline or the deadline has passed.
    months_left: int | None

    @property
    def left(self) -> Decimal:
        """What is still missing; zero once the goal is reached."""
        return max(self.target - self.saved, ZERO)

    @property
    def percent(self) -> int:
        """120 000 goal, 30 000 saved → 25. Never above 100."""
        if self.target <= 0:
            return 0
        share = (self.saved * 100 / self.target).quantize(Decimal("1"), ROUND_HALF_UP)
        return int(min(max(share, Decimal(0)), Decimal(100)))

    @property
    def reached(self) -> bool:
        return self.saved >= self.target

    @property
    def monthly(self) -> Decimal | None:
        """How much to put aside each month to reach the goal by the deadline."""
        if self.months_left is None or self.reached:
            return None
        return monthly_saving(self.left, self.months_left)


def goal_progress(
    target: Decimal, saved: Decimal, deadline: date | None, today: date
) -> GoalProgress:
    """Example: 120 000 ₽ for a vacation by June 2027, 15 000 ₽ saved, today is November 2026
    → 105 000 ₽ left over 7 months → 15 000 ₽ a month."""
    return GoalProgress(target=target, saved=saved, months_left=months_until(today, deadline))


def months_until(today: date, deadline: date | None) -> int | None:
    """Months of saving left before the deadline month: November 2026 → June 2027 is 7.

    A deadline later this month still leaves one month; a past deadline gives None.
    """
    if deadline is None or deadline < today:
        return None
    return max((deadline.year - today.year) * 12 + deadline.month - today.month, 1)


def monthly_saving(left: Decimal, months: int) -> Decimal:
    """Split what is left into equal monthly amounts, rounded up to whole rubles
    so the goal is not missed by kopecks: 100 000 over 3 months → 33 334."""
    return (left / months).quantize(Decimal("1"), ROUND_CEILING)
