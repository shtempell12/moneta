from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Transaction
from app.domain.categorization import merchant_category
from app.domain.entries import EntryForm, clean_spender, make_entry
from app.domain.enums import CategorySource
from app.domain.months import next_month
from app.domain.summary import MonthSummary, SummaryEntry, summarize_month
from app.repositories import categories, events, merchant_rules, transactions


class NotFoundError(Exception):
    """The transaction or category does not exist or belongs to another user."""


class NotEditableError(Exception):
    """Only hand-added transactions can be edited or deleted.

    A bank transaction deleted here would come back with the next import of the statement.
    """


def month_transactions(
    session: Session, user_id: int, month: date
) -> list[tuple[Transaction, str | None]]:
    return transactions.list_with_category(session, user_id, month, next_month(month))


def month_summary(session: Session, user_id: int, month: date) -> MonthSummary:
    rows = month_transactions(session, user_id, month)
    return summarize_month(
        SummaryEntry(category_name=name, amount=item.amount, source=item.category_source)
        for item, name in rows
    )


def change_category(session: Session, user_id: int, transaction_id: int, category_id: int) -> int:
    """Set the category by hand and update what is remembered for this merchant.

    The merchant keeps the category the user chose most often (see merchant_category),
    and its transactions that were not fixed by hand follow it.
    Returns how many other transactions changed along with this one.
    """
    transaction = transactions.get_for_user(session, user_id, transaction_id)
    category = categories.get_for_user(session, user_id, category_id)
    if transaction is None or category is None:
        raise NotFoundError

    previous_category_id, previous_source = transaction.category_id, transaction.category_source
    transaction.category_id = category.id
    transaction.category_source = CategorySource.MANUAL
    also_changed = 0
    if transaction.merchant_key:
        session.flush()
        remembered_id = merchant_category(
            transactions.manual_category_ids(session, user_id, transaction.merchant_key),
            latest_choice=category.id,
        )
        merchant_rules.upsert(session, user_id, transaction.merchant_key, remembered_id)
        session.flush()
        also_changed = transactions.apply_category_to_merchant(
            session, user_id, transaction.merchant_key, remembered_id
        )

    # The correction log is the raw data for measuring categorization accuracy.
    events.add(
        session,
        "category_corrected",
        user_id,
        {
            "transaction_id": transaction.id,
            "from_category_id": previous_category_id,
            "from_source": previous_source.value if previous_source else None,
            "to_category_id": category.id,
            "also_changed": also_changed,
        },
    )
    session.commit()
    return also_changed


def add_transaction(session: Session, user_id: int, form: EntryForm) -> Transaction:
    """Add a transaction by hand, e.g. cash at a market."""
    category = categories.get_for_user(session, user_id, form.category_id)
    if category is None:
        raise NotFoundError
    entry = make_entry(form, category.kind, category.name)
    transaction = Transaction(
        user_id=user_id,
        date=entry.date,
        amount=entry.amount,
        description=entry.description,
        spender=entry.spender,
        category_id=category.id,
        category_source=CategorySource.MANUAL,
        # A typed note like «рынок» is not a bank merchant name,
        # so it must not create rules for statement rows.
        merchant_key="",
    )
    session.add(transaction)
    session.flush()
    events.add(session, "transaction_added", user_id, {"transaction_id": transaction.id})
    session.commit()
    return transaction


def edit_transaction(
    session: Session, user_id: int, transaction_id: int, form: EntryForm
) -> Transaction:
    transaction = _hand_added(session, user_id, transaction_id)
    category = categories.get_for_user(session, user_id, form.category_id)
    if category is None:
        raise NotFoundError
    entry = make_entry(form, category.kind, category.name)
    transaction.date = entry.date
    transaction.amount = entry.amount
    transaction.description = entry.description
    transaction.spender = entry.spender
    transaction.category_id = category.id
    events.add(session, "transaction_edited", user_id, {"transaction_id": transaction.id})
    session.commit()
    return transaction


def set_spender(session: Session, user_id: int, transaction_id: int, spender: str) -> None:
    """Set «Кто потратил». Bank transactions allow it, as it is not in the statement."""
    transaction = transactions.get_for_user(session, user_id, transaction_id)
    if transaction is None:
        raise NotFoundError
    transaction.spender = clean_spender(spender)
    session.commit()


def delete_transaction(session: Session, user_id: int, transaction_id: int) -> None:
    transaction = _hand_added(session, user_id, transaction_id)
    session.delete(transaction)
    events.add(session, "transaction_deleted", user_id, {"transaction_id": transaction_id})
    session.commit()


def _hand_added(session: Session, user_id: int, transaction_id: int) -> Transaction:
    transaction = transactions.get_for_user(session, user_id, transaction_id)
    if transaction is None:
        raise NotFoundError
    if not transaction.added_by_hand:
        raise NotEditableError
    return transaction
