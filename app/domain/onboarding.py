"""First-run questions: a goal, the family income and the user's own categories."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.goals import GoalError, NewGoal, make_goal, parse_money

MAX_CATEGORY_NAME = 100
MAX_NEW_CATEGORIES = 10
# Offered as checkboxes: categories families named in interviews that banks do not have.
SUGGESTED_CATEGORIES = ("Развивашки", "Бюджет мужа", "Бюджет жены", "Питомец", "Кредит и ипотека")
CURRENT_TOOLS = {
    "excel": "Таблица Excel или Google",
    "app": "Приложение для учёта",
    "bank": "Только приложение банка",
    "none": "Пока никак",
}


class OnboardingError(ValueError):
    """Invalid answer; the message is safe to show to the user."""


@dataclass(frozen=True)
class BudgetRule:
    """The 50/30/20 rule: needs, wants and savings out of the monthly income."""

    needs: Decimal
    wants: Decimal
    savings: Decimal


@dataclass(frozen=True)
class Answers:
    goal: NewGoal | None
    income: Decimal | None
    categories: list[str]
    current_tool: str | None


def budget_rule(income: Decimal) -> BudgetRule:
    """100 000 ₽ a month → 50 000 on needs, 30 000 on wants, 20 000 put aside.

    Parts are whole rubles and always add up to the income exactly.
    """
    needs = (income * Decimal("0.5")).quantize(Decimal("1"), ROUND_HALF_UP)
    wants = (income * Decimal("0.3")).quantize(Decimal("1"), ROUND_HALF_UP)
    return BudgetRule(needs=needs, wants=wants, savings=income - needs - wants)


def make_answers(
    *,
    goal_name: str,
    goal_target: str,
    goal_deadline: str,
    income: str,
    categories: Sequence[str],
    custom_category: str,
    current_tool: str,
    today: date,
) -> Answers:
    """Check the onboarding form. Every question may be left empty."""
    try:
        goal = (
            make_goal(goal_name, goal_target, goal_deadline, today)
            if goal_name.strip() or goal_target.strip()
            else None
        )
        monthly_income = parse_money(income) if income.strip() else None
    except GoalError as error:
        raise OnboardingError(str(error)) from None
    return Answers(
        goal=goal,
        income=monthly_income,
        categories=_clean_categories([*categories, custom_category]),
        current_tool=current_tool if current_tool in CURRENT_TOOLS else None,
    )


def _clean_categories(names: Sequence[str]) -> list[str]:
    cleaned: list[str] = []
    for name in names:
        name = " ".join(name.split())
        if not name:
            continue
        if len(name) > MAX_CATEGORY_NAME:
            raise OnboardingError(f"Название категории не длиннее {MAX_CATEGORY_NAME} символов")
        if name.lower() not in {existing.lower() for existing in cleaned}:
            cleaned.append(name)
    if len(cleaned) > MAX_NEW_CATEGORIES:
        raise OnboardingError(f"Сразу можно добавить не больше {MAX_NEW_CATEGORIES} категорий")
    return cleaned
