from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Event
from app.services import plan
from app.services.imports import import_statement
from app.services.plan import PlanError
from tests.services.conftest import row, statement

OCTOBER, NOVEMBER = date(2026, 10, 1), date(2026, 11, 1)


def category_id(session: Session, name: str) -> int:
    return session.scalars(select(Category.id).where(Category.name == name)).one()


def test_plan_is_saved_and_compared_with_spending(session: Session, user_id: int) -> None:
    import_statement(
        session,
        user_id,
        "october.csv",
        statement(
            row(1, "-21500", "ПЯТЕРОЧКА", "Супермаркеты"),
            row(2, "-6000", "ШОКОЛАДНИЦА", "Рестораны"),
        ),
    )
    groceries, cafe = category_id(session, "Продукты"), category_id(session, "Кафе и рестораны")

    plan.save_plan(session, user_id, OCTOBER, {groceries: "30 000", cafe: "5000"})

    result = plan.month_plan_fact(session, user_id, OCTOBER)
    assert [(r.name, r.left) for r in result.rows] == [
        ("Продукты", Decimal("8500.00")),
        ("Кафе и рестораны", Decimal("-1000.00")),
    ]
    assert result.left == Decimal("7500.00")
    assert session.scalars(select(Event.type)).all()[-1] == "plan_updated"


def test_empty_or_zero_field_removes_the_plan(session: Session, user_id: int) -> None:
    groceries, cafe = category_id(session, "Продукты"), category_id(session, "Кафе и рестораны")
    plan.save_plan(session, user_id, OCTOBER, {groceries: "30000", cafe: "5000"})

    plan.save_plan(session, user_id, OCTOBER, {groceries: "", cafe: "0"})

    assert plan.month_plan(session, user_id, OCTOBER) == {}


@pytest.mark.parametrize("typed", ["тридцать", "-100", "NaN"])
def test_invalid_plan_amount_is_rejected(session: Session, user_id: int, typed: str) -> None:
    with pytest.raises(PlanError):
        plan.save_plan(session, user_id, OCTOBER, {category_id(session, "Продукты"): typed})


def test_income_and_foreign_categories_cannot_be_planned(session: Session, user_id: int) -> None:
    with pytest.raises(PlanError):
        plan.save_plan(session, user_id, OCTOBER, {category_id(session, "Зарплата"): "1000"})
    with pytest.raises(PlanError):
        plan.save_plan(session, user_id, OCTOBER, {999_999: "1000"})


def test_previous_plan_is_copied_into_an_empty_month(session: Session, user_id: int) -> None:
    groceries = category_id(session, "Продукты")
    plan.save_plan(session, user_id, OCTOBER, {groceries: "30000"})

    copied = plan.copy_previous_plan(session, user_id, NOVEMBER)

    assert copied == 1
    assert plan.month_plan(session, user_id, NOVEMBER) == {groceries: Decimal("30000.00")}
    with pytest.raises(PlanError, match="уже есть"):
        plan.copy_previous_plan(session, user_id, NOVEMBER)


def test_nothing_to_copy_without_earlier_plan(session: Session, user_id: int) -> None:
    with pytest.raises(PlanError, match="Раньше плана не было"):
        plan.copy_previous_plan(session, user_id, NOVEMBER)
