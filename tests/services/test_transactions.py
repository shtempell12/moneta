from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Event, Transaction
from app.domain.enums import CategorySource
from app.repositories import merchant_rules
from app.services import categories as categories_service
from app.services import transactions
from app.services.categories import CategoryError
from app.services.imports import import_statement
from app.services.transactions import NotFoundError
from tests.services.conftest import row, statement

OCTOBER = date(2026, 10, 1)


def category_id(session: Session, name: str) -> int:
    return session.scalars(select(Category.id).where(Category.name == name)).one()


def transaction_id(session: Session, description: str) -> int:
    return (
        session.scalars(
            select(Transaction.id).where(Transaction.description == description)
        ).first()
        or 0
    )


def test_fixing_one_transaction_fixes_the_whole_merchant_and_is_remembered(
    session: Session, user_id: int
) -> None:
    import_statement(
        session,
        user_id,
        "october.csv",
        statement(
            row(1, "-1500", "Студия Лето 1", "Образование"),
            row(8, "-1500", "СТУДИЯ ЛЕТО 2", "Образование"),
            row(15, "-1500", "студия лето", "Образование"),
        ),
    )
    kids = categories_service.add_category(session, user_id, "Развивашки")

    also_changed = transactions.change_category(
        session, user_id, transaction_id(session, "Студия Лето 1"), kids.id
    )

    assert also_changed == 2
    sources = session.scalars(select(Transaction.category_source).order_by(Transaction.date))
    assert list(sources) == [CategorySource.MANUAL, CategorySource.HISTORY, CategorySource.HISTORY]
    assert merchant_rules.as_dict(session, user_id) == {"студия лето": kids.id}

    import_statement(
        session,
        user_id,
        "november.csv",
        statement(row(5, "-1500", "СТУДИЯ ЛЕТО 9", "Образование", month=11)),
    )
    november = session.scalars(
        select(Transaction).where(Transaction.description == "СТУДИЯ ЛЕТО 9")
    ).one()
    assert (november.category_id, november.category_source) == (kids.id, CategorySource.HISTORY)


def test_manual_choice_is_not_overwritten_by_a_later_fix(session: Session, user_id: int) -> None:
    import_statement(
        session,
        user_id,
        "october.csv",
        statement(row(1, "-300", "ВКУСВИЛЛ"), row(2, "-5000", "ВКУСВИЛЛ 2")),
    )
    groceries, gifts = category_id(session, "Продукты"), category_id(session, "Подарки")
    transactions.change_category(session, user_id, transaction_id(session, "ВКУСВИЛЛ 2"), gifts)

    transactions.change_category(session, user_id, transaction_id(session, "ВКУСВИЛЛ"), groceries)

    big_purchase = session.get_one(Transaction, transaction_id(session, "ВКУСВИЛЛ 2"))
    assert big_purchase.category_id == gifts


def test_one_unusual_purchase_does_not_move_the_whole_merchant(
    session: Session, user_id: int
) -> None:
    import_statement(
        session,
        user_id,
        "october.csv",
        statement(*(row(day, "-500", f"АПТЕКА РИГЛА {day}", "Аптеки") for day in range(1, 7))),
    )
    health, beauty = category_id(session, "Здоровье"), category_id(session, "Красота")
    for day in (1, 2):
        transactions.change_category(
            session, user_id, transaction_id(session, f"АПТЕКА РИГЛА {day}"), health
        )

    also_changed = transactions.change_category(
        session, user_id, transaction_id(session, "АПТЕКА РИГЛА 3"), beauty
    )

    assert also_changed == 0
    assert merchant_rules.as_dict(session, user_id) == {"аптека ригла": health}
    categories_by_day = session.scalars(select(Transaction.category_id).order_by(Transaction.date))
    assert list(categories_by_day) == [health, health, beauty, health, health, health]


def test_switching_back_and_forth_follows_the_latest_choice_on_a_tie(
    session: Session, user_id: int
) -> None:
    import_statement(
        session,
        user_id,
        "october.csv",
        statement(*(row(day, "-500", f"АПТЕКА РИГЛА {day}", "Аптеки") for day in range(1, 5))),
    )
    health, beauty = category_id(session, "Здоровье"), category_id(session, "Красота")
    transactions.change_category(
        session, user_id, transaction_id(session, "АПТЕКА РИГЛА 1"), beauty
    )

    transactions.change_category(
        session, user_id, transaction_id(session, "АПТЕКА РИГЛА 2"), health
    )

    categories_by_day = session.scalars(select(Transaction.category_id).order_by(Transaction.date))
    assert list(categories_by_day) == [beauty, health, health, health]


def test_correction_is_logged_for_accuracy_research(session: Session, user_id: int) -> None:
    import_statement(
        session, user_id, "october.csv", statement(row(1, "-100", "ПЯТЕРОЧКА", "Супермаркеты"))
    )
    cafe = category_id(session, "Кафе и рестораны")

    transactions.change_category(session, user_id, transaction_id(session, "ПЯТЕРОЧКА"), cafe)

    event = session.scalars(select(Event).where(Event.type == "category_corrected")).one()
    assert event.payload["from_source"] == "bank"
    assert event.payload["from_category_id"] == category_id(session, "Продукты")
    assert event.payload["to_category_id"] == cafe


def test_cannot_use_another_users_category(session: Session, user_id: int) -> None:
    import_statement(session, user_id, "october.csv", statement(row(1, "-100", "МЕТРО")))

    with pytest.raises(NotFoundError):
        transactions.change_category(session, user_id, transaction_id(session, "МЕТРО"), 999_999)


def test_month_summary_counts_auto_and_manual(session: Session, user_id: int) -> None:
    import_statement(
        session,
        user_id,
        "october.csv",
        statement(
            row(1, "-3000", "ПЯТЕРОЧКА", "Супермаркеты"),
            row(2, "-1000", "WILDBERRIES", "Маркетплейсы"),
            row(3, "85000", "ЗАРПЛАТА", "Пополнения"),
            row(4, "-999", "ТАКСИ", "Такси", month=11),
        ),
    )
    clothes = category_id(session, "Одежда")
    transactions.change_category(session, user_id, transaction_id(session, "WILDBERRIES"), clothes)

    summary = transactions.month_summary(session, user_id, OCTOBER)

    assert summary.spent == 4000
    assert summary.income == 85000
    assert [(c.name, c.percent) for c in summary.by_category] == [("Продукты", 75), ("Одежда", 25)]
    assert (summary.auto_percent, summary.manual_percent) == (50, 50)


def test_new_category_names_are_cleaned_and_unique(session: Session, user_id: int) -> None:
    category = categories_service.add_category(session, user_id, "  Бьюти   услуги ")

    assert category.name == "Бьюти услуги"
    with pytest.raises(CategoryError, match="уже есть"):
        categories_service.add_category(session, user_id, "Бьюти услуги")
    with pytest.raises(CategoryError, match="название"):
        categories_service.add_category(session, user_id, "   ")
