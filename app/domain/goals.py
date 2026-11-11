"""Saving goals: how much is saved and how much to put aside each month."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from app.domain.entries import MAX_AMOUNT
from app.domain.parsing import parse_amount, parse_date

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


MAX_NAME_LENGTH = 100


class GoalError(ValueError):
    """Invalid goal field; the message is safe to show to the user."""


@dataclass(frozen=True)
class NewGoal:
    name: str
    target: Decimal
    deadline: date | None


def make_goal(name: str, target: str, deadline: str, today: date) -> NewGoal:
    """Check the «new goal» form: a name, a positive target and an optional future deadline."""
    name = " ".join(name.split())
    if not name:
        raise GoalError("Назовите цель, например «Отпуск»")
    if len(name) > MAX_NAME_LENGTH:
        raise GoalError(f"Название не длиннее {MAX_NAME_LENGTH} символов")
    amount = parse_money(target)
    if not deadline.strip():
        return NewGoal(name=name, target=amount, deadline=None)
    try:
        day = parse_date(deadline)
    except ValueError:
        raise GoalError("Срок — это дата, например 01.06.2027") from None
    if day < today:
        raise GoalError("Срок уже прошёл — выберите дату в будущем")
    return NewGoal(name=name, target=amount, deadline=day)


def parse_money(text: str) -> Decimal:
    """A positive amount typed by the user: «120 000» → 120000.00."""
    try:
        amount = parse_amount(text)
    except ValueError:
        raise GoalError("Сумма должна быть числом, например 120 000") from None
    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
        raise GoalError("Сумма должна быть больше нуля")
    return amount


def months_to_reach(left: Decimal, per_month: Decimal) -> int:
    """How many months it takes at a given pace: 120 000 at 10 000 a month → 12."""
    if per_month <= 0:
        raise ValueError("per_month must be positive")
    return int((left / per_month).to_integral_value(ROUND_CEILING))
