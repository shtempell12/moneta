from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Event, Transaction
from app.domain.entries import EntryError, EntryForm
from app.domain.enums import CategorySource
from app.repositories import merchant_rules
from app.repositories import transactions as transactions_repo
from app.services import transactions
from app.services.imports import import_statement
from app.services.transactions import NotEditableError, NotFoundError
from tests.services.conftest import row, statement


def category_id(session: Session, name: str) -> int:
    return session.scalars(select(Category.id).where(Category.name == name)).one()


def cash(session: Session, amount: str = "700", category: str = "Продукты") -> EntryForm:
    return EntryForm(
        date="2026-10-05",
        amount=amount,
        description="Рынок, овощи",
        category_id=category_id(session, category),
        spender="жена",
    )


def test_cash_purchase_is_added_as_a_manual_expense(session: Session, user_id: int) -> None:
    transaction = transactions.add_transaction(session, user_id, cash(session))

    assert (transaction.date, transaction.amount) == (date(2026, 10, 5), Decimal("-700.00"))
    assert transaction.category_source == CategorySource.MANUAL
    assert transaction.spender == "жена"
    assert transaction.added_by_hand
    summary = transactions.month_summary(session, user_id, date(2026, 10, 1))
    assert summary.spent == 700
    assert session.scalars(select(Event.type)).all()[-1] == "transaction_added"


def test_hand_typed_description_does_not_create_merchant_rules(
    session: Session, user_id: int
) -> None:
    transactions.add_transaction(session, user_id, cash(session))

    assert merchant_rules.as_dict(session, user_id) == {}


def test_hand_added_transaction_can_be_edited_and_deleted(session: Session, user_id: int) -> None:
    added = transactions.add_transaction(session, user_id, cash(session))

    edited = transactions.edit_transaction(
        session, user_id, added.id, cash(session, amount="85 000", category="Зарплата")
    )
    assert edited.amount == Decimal("85000.00")

    transactions.delete_transaction(session, user_id, added.id)
    assert session.scalars(select(Transaction)).all() == []


def test_bank_transaction_cannot_be_edited_or_deleted_but_gets_a_spender(
    session: Session, user_id: int
) -> None:
    import_statement(session, user_id, "october.csv", statement(row(1, "-100", "МЕТРО")))
    bank = session.scalars(select(Transaction)).one()

    with pytest.raises(NotEditableError):
        transactions.edit_transaction(session, user_id, bank.id, cash(session))
    with pytest.raises(NotEditableError):
        transactions.delete_transaction(session, user_id, bank.id)

    transactions.set_spender(session, user_id, bank.id, " муж ")
    assert bank.spender == "муж"
    assert transactions_repo.spenders(session, user_id) == ["муж"]


def test_invalid_amount_is_not_saved(session: Session, user_id: int) -> None:
    with pytest.raises(EntryError):
        transactions.add_transaction(session, user_id, cash(session, amount="сто"))

    assert session.scalars(select(Transaction)).all() == []


def test_cannot_add_to_another_users_category(session: Session, user_id: int) -> None:
    form = EntryForm(date="2026-10-05", amount="100", description="", category_id=999_999)

    with pytest.raises(NotFoundError):
        transactions.add_transaction(session, user_id, form)
