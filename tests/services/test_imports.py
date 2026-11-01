from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Event, Transaction
from app.domain.enums import CategorySource
from app.domain.statement import ParsedStatement, RowError
from app.repositories import merchant_rules
from app.services.imports import import_statement
from tests.services.conftest import row, statement


def category_of(session: Session, description: str) -> tuple[str | None, CategorySource | None]:
    transaction = session.scalars(
        select(Transaction).where(Transaction.description == description)
    ).one()
    name = (
        session.get_one(Category, transaction.category_id).name if transaction.category_id else None
    )
    return name, transaction.category_source


def test_import_uses_bank_category_for_new_merchants(session: Session, user_id: int) -> None:
    result = import_statement(
        session,
        user_id,
        "october.csv",
        statement(
            row(1, "-1234.56", "ПЯТЕРОЧКА 1234", "Супермаркеты"),
            row(2, "-2990.00", "WILDBERRIES", "Маркетплейсы"),
        ),
    )

    assert result.imported == 2
    assert result.by_source == {"bank": 1, "none": 1}
    assert result.latest_month == date(2026, 10, 1)
    assert category_of(session, "ПЯТЕРОЧКА 1234") == ("Продукты", CategorySource.BANK)
    assert category_of(session, "WILDBERRIES") == (None, None)


def test_users_history_wins_over_bank_category(session: Session, user_id: int) -> None:
    kids = session.scalars(select(Category).where(Category.name == "Дети")).one()
    merchant_rules.upsert(session, user_id, "детский мир", kids.id)

    import_statement(
        session, user_id, "october.csv", statement(row(3, "-4500", "ДЕТСКИЙ МИР 77", "Одежда"))
    )

    assert category_of(session, "ДЕТСКИЙ МИР 77") == ("Дети", CategorySource.HISTORY)


def test_same_file_imported_twice_does_not_double_spending(session: Session, user_id: int) -> None:
    october = statement(row(1, "-100", "МЕТРО"), row(2, "-100", "МЕТРО"))

    import_statement(session, user_id, "october.csv", october)
    second = import_statement(session, user_id, "october.csv", october)

    assert second.imported == 0
    assert second.duplicates == 2
    assert len(session.scalars(select(Transaction)).all()) == 2


def test_import_is_logged_as_event_with_counts(session: Session, user_id: int) -> None:
    parsed = ParsedStatement(
        rows=[row(1, "-100", "ПЯТЕРОЧКА", "Супермаркеты")],
        errors=[RowError(line=5, message="Не удалось разобрать дату: 'вчера'")],
    )

    result = import_statement(session, user_id, "october.csv", parsed)

    event = session.scalars(select(Event).where(Event.type == "statement_imported")).one()
    assert event.payload["imported"] == 1
    assert event.payload["errors"] == 1
    assert event.payload["by_source"] == {"bank": 1}
    assert result.errors[0].line == 5


def test_empty_statement_imports_nothing(session: Session, user_id: int) -> None:
    result = import_statement(session, user_id, "empty.csv", statement())

    assert result.imported == 0
    assert result.latest_month is None
