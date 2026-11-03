from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.entries import MAX_AMOUNT
from app.domain.enums import CategoryKind
from app.domain.months import month_param
from app.domain.parsing import parse_amount
from app.domain.plan import PlanFact, plan_vs_fact
from app.repositories import budget_lines, categories, events
from app.services.transactions import month_summary


class PlanError(Exception):
    """Invalid plan; the message is safe to show to the user."""


def month_plan(session: Session, user_id: int, month: date) -> dict[int, Decimal]:
    return budget_lines.for_month(session, user_id, month)


def month_plan_fact(session: Session, user_id: int, month: date) -> PlanFact:
    spent = {item.name: item.spent for item in month_summary(session, user_id, month).by_category}
    return plan_vs_fact(budget_lines.by_name_for_month(session, user_id, month), spent)


def save_plan(session: Session, user_id: int, month: date, typed: Mapping[int, str]) -> None:
    """Save the month plan from the form: «category id → amount as typed».

    An empty field or zero means «no plan for this category».
    """
    expense_ids = {
        category.id
        for category in categories.list_for_user(session, user_id)
        if category.kind == CategoryKind.EXPENSE
    }
    amounts: dict[int, Decimal] = {}
    for category_id, text in typed.items():
        if category_id not in expense_ids:
            raise PlanError("Категория не найдена")
        amount = _parse_plan_amount(text)
        if amount:
            amounts[category_id] = amount

    budget_lines.replace_month(session, user_id, month, amounts)
    events.add(
        session,
        "plan_updated",
        user_id,
        {"month": month_param(month), "categories": len(amounts)},
    )
    session.commit()


def copy_previous_plan(session: Session, user_id: int, month: date) -> int:
    """Start the month with the closest earlier plan; returns how many categories were copied."""
    if budget_lines.for_month(session, user_id, month):
        raise PlanError("План на этот месяц уже есть")
    previous = budget_lines.latest_month_before(session, user_id, month)
    if previous is None:
        raise PlanError("Раньше плана не было — заполните его в первый раз")
    amounts = budget_lines.for_month(session, user_id, previous)
    budget_lines.replace_month(session, user_id, month, amounts)
    events.add(
        session,
        "plan_copied",
        user_id,
        {"month": month_param(month), "from_month": month_param(previous)},
    )
    session.commit()
    return len(amounts)


def _parse_plan_amount(text: str) -> Decimal | None:
    if not text.strip():
        return None
    try:
        amount = parse_amount(text)
    except ValueError:
        raise PlanError(f"«{text}» — не сумма. Пишите числом, например 30 000") from None
    if not amount.is_finite() or amount < 0 or amount > MAX_AMOUNT:
        raise PlanError("Сумма плана должна быть положительным числом")
    return amount or None
