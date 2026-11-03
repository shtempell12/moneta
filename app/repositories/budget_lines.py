from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import BudgetLine, Category


def for_month(session: Session, user_id: int, month: date) -> dict[int, Decimal]:
    """The month plan as «category id → rubles»."""
    lines = session.scalars(
        select(BudgetLine).where(BudgetLine.user_id == user_id, BudgetLine.month == month)
    )
    return {line.category_id: line.amount for line in lines}


def by_name_for_month(session: Session, user_id: int, month: date) -> dict[str, Decimal]:
    """The month plan as «category name → rubles», to compare with spending by category."""
    rows = session.execute(
        select(Category.name, BudgetLine.amount)
        .join(Category, Category.id == BudgetLine.category_id)
        .where(BudgetLine.user_id == user_id, BudgetLine.month == month)
    )
    return {name: amount for name, amount in rows}


def replace_month(
    session: Session, user_id: int, month: date, amounts: Mapping[int, Decimal]
) -> None:
    """Replace the whole month plan; categories missing from `amounts` lose their plan."""
    session.execute(
        delete(BudgetLine).where(BudgetLine.user_id == user_id, BudgetLine.month == month)
    )
    session.add_all(
        BudgetLine(user_id=user_id, category_id=category_id, month=month, amount=amount)
        for category_id, amount in amounts.items()
    )


def latest_month_before(session: Session, user_id: int, month: date) -> date | None:
    """The closest earlier month that has a plan."""
    return session.scalar(
        select(func.max(BudgetLine.month)).where(
            BudgetLine.user_id == user_id, BudgetLine.month < month
        )
    )
