from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Transaction
from app.domain.enums import CategorySource
from app.domain.months import next_month
from app.domain.summary import MonthSummary, SummaryEntry, summarize_month
from app.repositories import categories, events, merchant_rules, transactions


class NotFoundError(Exception):
    """The transaction or category does not exist or belongs to another user."""


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
    """Set the category by hand and remember it for this merchant.

    The merchant's other transactions that were not fixed by hand get the same category.
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
        merchant_rules.upsert(session, user_id, transaction.merchant_key, category.id)
        session.flush()
        also_changed = transactions.apply_category_to_merchant(
            session, user_id, transaction.merchant_key, category.id
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
