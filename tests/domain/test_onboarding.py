from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import pytest

from app.domain.goals import months_to_reach
from app.domain.onboarding import Answers, OnboardingError, budget_rule, make_answers

TODAY = date(2026, 11, 11)


def answers(
    goal_name: str = "",
    goal_target: str = "",
    income: str = "",
    categories: Sequence[str] = (),
    custom_category: str = "",
    current_tool: str = "",
) -> Answers:
    return make_answers(
        goal_name=goal_name,
        goal_target=goal_target,
        goal_deadline="",
        income=income,
        categories=categories,
        custom_category=custom_category,
        current_tool=current_tool,
        today=TODAY,
    )


def test_rule_50_30_20_splits_income_into_whole_rubles() -> None:
    rule = budget_rule(Decimal("100000"))
    assert (rule.needs, rule.wants, rule.savings) == (50000, 30000, 20000)

    odd = budget_rule(Decimal("85555"))
    assert odd.needs + odd.wants + odd.savings == Decimal("85555")


def test_saving_ten_thousand_a_month_reaches_120_thousand_in_a_year() -> None:
    assert months_to_reach(Decimal("120000"), Decimal("10000")) == 12
    assert months_to_reach(Decimal("120001"), Decimal("10000")) == 13
    with pytest.raises(ValueError):
        months_to_reach(Decimal("100"), Decimal("0"))


def test_all_questions_can_be_skipped() -> None:
    result = answers()

    assert (result.goal, result.income, result.categories, result.current_tool) == (
        None,
        None,
        [],
        None,
    )


def test_full_answers_are_cleaned() -> None:
    result = answers(
        goal_name="Отпуск",
        goal_target="120 000",
        income="95 000",
        categories=["Развивашки", "Питомец"],
        custom_category="  развивашки ",
        current_tool="excel",
    )

    assert result.goal is not None and result.goal.target == Decimal("120000.00")
    assert result.income == Decimal("95000.00")
    assert result.categories == ["Развивашки", "Питомец"]
    assert result.current_tool == "excel"


def test_wrong_answers_give_a_clear_message() -> None:
    with pytest.raises(OnboardingError, match="числом"):
        answers(income="много")
    with pytest.raises(OnboardingError, match="Назовите"):
        answers(goal_target="1000")
    assert answers(current_tool="hack").current_tool is None
