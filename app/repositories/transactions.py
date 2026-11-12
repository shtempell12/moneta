from collections import Counter
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.db.models import Category, Transaction
from app.domain.enums import CategorySource

# Categories that come from the user, never overwritten by automatic categorization.
USER_CHOICES = (CategorySource.MANUAL, CategorySource.TABLE)

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


def manual_category_ids(session: Session, user_id: int, merchant_key: str) -> list[int]:
    """Categories the user chose for this merchant (by hand or in the budget table),
    one entry per transaction, oldest first."""
    return list(
        session.scalars(
            select(Transaction.category_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.merchant_key == merchant_key,
                Transaction.category_source.in_(USER_CHOICES),
                Transaction.category_id.is_not(None),
            )
            .order_by(Transaction.date, Transaction.id)
        )
    )


def apply_category_to_merchant(
    session: Session, user_id: int, merchant_key: str, category_id: int
) -> int:
    """Re-categorize the merchant's other transactions, keeping the ones the user chose.

    Returns how many transactions were changed.
    """
    changed_ids = session.scalars(
        update(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.merchant_key == merchant_key,
            Transaction.category_id.is_distinct_from(category_id),
            or_(
                Transaction.category_source.is_(None),
                Transaction.category_source.not_in(USER_CHOICES),
            ),
        )
        .values(category_id=category_id, category_source=CategorySource.HISTORY)
        .returning(Transaction.id)
    ).all()
    return len(changed_ids)


def bank_rows_for_matching(session: Session, user_id: int) -> Sequence[Transaction]:
    """Statement transactions a budget table may categorize: not the ones fixed by hand."""
    return session.scalars(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.import_id.is_not(None),
            or_(
                Transaction.category_source.is_(None),
                Transaction.category_source != CategorySource.MANUAL,
            ),
        )
    ).all()


def clear_category(session: Session, user_id: int, category_id: int) -> None:
    """Make the category's transactions uncategorized, e.g. before the category is deleted."""
    session.execute(
        update(Transaction)
        .where(Transaction.user_id == user_id, Transaction.category_id == category_id)
        .values(category_id=None, category_source=None)
    )


def spenders(session: Session, user_id: int) -> list[str]:
    """Labels the user has already used in «Кто потратил», to suggest them in forms."""
    return list(
        session.scalars(
            select(Transaction.spender)
            .where(Transaction.user_id == user_id, Transaction.spender.is_not(None))
            .distinct()
            .order_by(Transaction.spender)
        )
    )


def months_with_data(session: Session, user_id: int) -> list[date]:
    """First days of the months that have transactions, newest first."""
    month = func.date_trunc("month", Transaction.date)
    rows = session.scalars(
        select(month).where(Transaction.user_id == user_id).distinct().order_by(month.desc())
    )
    return [value.date() for value in rows]
