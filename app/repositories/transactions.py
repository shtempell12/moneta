from collections import Counter
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import Category, Transaction
from app.domain.enums import CategorySource

# A statement row matches an imported transaction if all three fields are equal.
DuplicateKey = tuple[date, Decimal, str]


def existing_key_counts(
    session: Session, user_id: int, first_day: date, last_day: date
) -> Counter[DuplicateKey]:
    """How many transactions with each (date, amount, description) the user already has."""
    rows = session.execute(
        select(Transaction.date, Transaction.amount, Transaction.description).where(
            Transaction.user_id == user_id,
            Transaction.date >= first_day,
            Transaction.date <= last_day,
        )
    )
    return Counter((row.date, row.amount, row.description) for row in rows)


def list_with_category(
    session: Session, user_id: int, first_day: date, before_day: date
) -> list[tuple[Transaction, str | None]]:
    """Transactions in [first_day, before_day) with their category name, newest first."""
    rows = session.execute(
        select(Transaction, Category.name)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= first_day,
            Transaction.date < before_day,
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    return [(transaction, category_name) for transaction, category_name in rows]


def get_for_user(session: Session, user_id: int, transaction_id: int) -> Transaction | None:
    return session.scalar(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )


def apply_category_to_merchant(
    session: Session, user_id: int, merchant_key: str, category_id: int
) -> int:
    """Re-categorize the merchant's other transactions, keeping ones the user set by hand.

    Returns how many transactions were changed.
    """
    changed_ids = session.scalars(
        update(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.merchant_key == merchant_key,
            Transaction.category_id.is_distinct_from(category_id),
            Transaction.category_source.is_distinct_from(CategorySource.MANUAL),
        )
        .values(category_id=category_id, category_source=CategorySource.HISTORY)
        .returning(Transaction.id)
    ).all()
    return len(changed_ids)


def months_with_data(session: Session, user_id: int) -> list[date]:
    """First days of the months that have transactions, newest first."""
    month = func.date_trunc("month", Transaction.date)
    rows = session.scalars(
        select(month).where(Transaction.user_id == user_id).distinct().order_by(month.desc())
    )
    return [value.date() for value in rows]
