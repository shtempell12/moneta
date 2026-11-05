from datetime import date
from decimal import Decimal

import pytest

from app.domain.goals import GoalError, goal_progress, make_goal, monthly_saving, months_until

TODAY = date(2026, 11, 5)


def test_vacation_by_june_needs_fifteen_thousand_a_month() -> None:
    progress = goal_progress(Decimal("120000"), Decimal("15000"), date(2027, 6, 1), TODAY)

    assert progress.left == Decimal("105000")
    assert progress.months_left == 7
    assert progress.monthly == Decimal("15000")
    assert progress.percent == 13


def test_monthly_amount_is_rounded_up_to_whole_rubles() -> None:
    assert monthly_saving(Decimal("100000"), 3) == Decimal("33334")


@pytest.mark.parametrize(
    ("deadline", "months"),
    [
        (date(2027, 6, 1), 7),
        (date(2026, 11, 30), 1),
        (date(2026, 12, 1), 1),
        (date(2026, 11, 1), None),
        (None, None),
    ],
)
def test_months_until_deadline(deadline: date | None, months: int | None) -> None:
    assert months_until(TODAY, deadline) == months


def test_reached_goal_needs_nothing_more() -> None:
    progress = goal_progress(Decimal("50000"), Decimal("52000"), date(2027, 1, 1), TODAY)

    assert progress.reached
    assert (progress.left, progress.percent, progress.monthly) == (0, 100, None)


def test_goal_without_deadline_shows_only_progress() -> None:
    progress = goal_progress(Decimal("80000"), Decimal("20000"), None, TODAY)

    assert (progress.percent, progress.monthly) == (25, None)


def test_new_goal_form_is_cleaned() -> None:
    goal = make_goal("  Отпуск  в Сочи ", "120 000", "01.06.2027", TODAY)

    assert (goal.name, goal.target, goal.deadline) == (
        "Отпуск в Сочи",
        Decimal("120000.00"),
        date(2027, 6, 1),
    )
    assert make_goal("Подушка", "50000", "", TODAY).deadline is None


@pytest.mark.parametrize(
    ("name", "target", "deadline", "message"),
    [
        ("", "1000", "", "Назовите"),
        ("Отпуск", "много", "", "числом"),
        ("Отпуск", "0", "", "больше нуля"),
        ("Отпуск", "1000", "вчера", "дата"),
        ("Отпуск", "1000", "01.01.2026", "прошёл"),
    ],
)
def test_invalid_goal_is_rejected(name: str, target: str, deadline: str, message: str) -> None:
    with pytest.raises(GoalError, match=message):
        make_goal(name, target, deadline, TODAY)
