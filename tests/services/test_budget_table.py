from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Event, Transaction
from app.domain.budget_table import ParsedTable
from app.domain.enums import CategoryKind, CategorySource
from app.domain.matching import TableRow
from app.repositories import merchant_rules
from app.services import transactions
from app.services.budget_table import import_table
from app.services.imports import import_statement
from tests.services.conftest import row, statement


def table_row(day: int, amount: str, category: str, spender: str | None = None) -> TableRow:
    return TableRow(
        date=date(2026, 10, day), amount=Decimal(amount), category=category, spender=spender
    )


def by_description(session: Session, description: str) -> Transaction:
    return session.scalars(select(Transaction).where(Transaction.description == description)).one()


def test_table_categories_are_given_to_matched_statement_rows(
    session: Session, user_id: int
) -> None:
    import_statement(
        session,
        user_id,
        "october.csv",
        statement(
            row(3, "-4000", "СТУДИЯ ЛУЧИК", "Образование"),
            row(6, "-1500", "ПЯТЕРОЧКА 12", "Супермаркеты"),
            row(15, "85000", "ЗАРПЛАТА"),
        ),
    )
    table = ParsedTable(
        rows=[
            table_row(2, "4000", "развивашки", spender="Жена"),
            table_row(5, "1500", "Повар и продукты"),
            table_row(15, "85000", "Зарплата"),
            table_row(20, "700", "Рынок наличными"),
        ],
        errors=[],
    )

    result = import_table(session, user_id, table)

    assert (result.rows, result.matched, result.unmatched) == (4, 3, 1)
    studio = by_description(session, "СТУДИЯ ЛУЧИК")
    assert studio.category_source == CategorySource.TABLE
    assert session.get_one(Category, studio.category_id).name == "развивашки"
    assert studio.spender == "Жена"
    # «Зарплата» already exists, so it is not created twice; «Рынок наличными» is new.
    assert result.categories_created == 3
    names = session.scalars(select(Category.name)).all()
    assert names.count("Зарплата") == 1
    assert "студия лучик" in merchant_rules.as_dict(session, user_id)
    event = session.scalars(select(Event).where(Event.type == "budget_table_imported")).one()
    assert event.payload["matched"] == 3


def test_new_statements_follow_the_table_from_day_one(session: Session, user_id: int) -> None:
    import_statement(session, user_id, "october.csv", statement(row(3, "-4000", "СТУДИЯ ЛУЧИК")))
    import_table(
        session, user_id, ParsedTable(rows=[table_row(3, "4000", "Развивашки")], errors=[])
    )

    import_statement(
        session, user_id, "november.csv", statement(row(3, "-4000", "СТУДИЯ ЛУЧИК", month=11))
    )

    november = session.scalars(
        select(Transaction).where(Transaction.date == date(2026, 11, 3))
    ).one()
    assert session.get_one(Category, november.category_id).name == "Развивашки"
    assert november.category_source == CategorySource.HISTORY


def test_table_does_not_overwrite_categories_fixed_by_hand(session: Session, user_id: int) -> None:
    import_statement(session, user_id, "october.csv", statement(row(3, "-900", "АПТЕКА")))
    beauty = session.scalars(select(Category.id).where(Category.name == "Красота")).one()
    transactions.change_category(session, user_id, by_description(session, "АПТЕКА").id, beauty)

    result = import_table(
        session, user_id, ParsedTable(rows=[table_row(3, "900", "Здоровье")], errors=[])
    )

    assert result.matched == 0
    assert by_description(session, "АПТЕКА").category_id == beauty


def test_income_only_category_from_the_table_is_created_as_income(
    session: Session, user_id: int
) -> None:
    import_statement(
        session, user_id, "october.csv", statement(row(10, "15000", "ПЕРЕВОД ОТ МАМЫ"))
    )

    import_table(
        session, user_id, ParsedTable(rows=[table_row(10, "15000", "Помощь родителей")], errors=[])
    )

    help_category = session.scalars(
        select(Category).where(Category.name == "Помощь родителей")
    ).one()
    assert help_category.kind == CategoryKind.INCOME
