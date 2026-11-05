from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import BudgetLine, Category, Event, Goal, MerchantRule, Transaction, User
from app.domain.enums import CategorySource, UserRole


def make_user(session: Session, email: str = "anna@example.com") -> User:
    user = User(email=email, password_hash="hash", pd_consent_at=datetime.now(UTC))
    session.add(user)
    session.flush()
    return user


def test_new_user_gets_default_role(session: Session) -> None:
    user = make_user(session)

    assert user.role == UserRole.USER


def test_email_is_unique(session: Session) -> None:
    make_user(session, "anna@example.com")

    with pytest.raises(IntegrityError):
        make_user(session, "anna@example.com")


def test_amount_keeps_kopecks_exactly(session: Session) -> None:
    user = make_user(session)
    session.add(
        Transaction(
            user_id=user.id,
            date=date(2026, 10, 15),
            amount=Decimal("-1234.56"),
            description="ПЯТЕРОЧКА 1234",
        )
    )
    session.flush()

    total = session.scalar(select(func.sum(Transaction.amount)))

    assert total == Decimal("-1234.56")
    assert isinstance(total, Decimal)


def test_category_names_are_unique_per_user(session: Session) -> None:
    anna = make_user(session, "anna@example.com")
    olga = make_user(session, "olga@example.com")
    session.add_all(
        [Category(user_id=anna.id, name="Развивашки"), Category(user_id=olga.id, name="Развивашки")]
    )
    session.flush()

    session.add(Category(user_id=anna.id, name="Развивашки"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_merchant_rule_is_unique_per_user_and_merchant(session: Session) -> None:
    user = make_user(session)
    category = Category(user_id=user.id, name="Развивашки")
    session.add(category)
    session.flush()
    session.add(MerchantRule(user_id=user.id, merchant_key="детский мир", category_id=category.id))
    session.flush()

    session.add(MerchantRule(user_id=user.id, merchant_key="детский мир", category_id=category.id))
    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_category_keeps_transaction_without_category(session: Session) -> None:
    user = make_user(session)
    category = Category(user_id=user.id, name="Кафе")
    session.add(category)
    session.flush()
    transaction = Transaction(
        user_id=user.id,
        date=date(2026, 10, 1),
        amount=Decimal("-450.00"),
        description="КОФЕЙНЯ",
        category_id=category.id,
        category_source=CategorySource.MANUAL,
    )
    session.add(transaction)
    session.flush()

    session.delete(category)
    session.flush()
    session.refresh(transaction)

    assert transaction.category_id is None


def test_deleting_user_removes_all_their_data(session: Session) -> None:
    # 152-FZ: a user can delete the account together with all personal data.
    user = make_user(session)
    category = Category(user_id=user.id, name="Продукты")
    session.add(category)
    session.flush()
    session.add_all(
        [
            Transaction(
                user_id=user.id,
                date=date(2026, 10, 1),
                amount=Decimal("-100.00"),
                description="ПЯТЕРОЧКА",
                category_id=category.id,
            ),
            MerchantRule(user_id=user.id, merchant_key="пятерочка", category_id=category.id),
            Event(user_id=user.id, type="login", payload={"ok": True}),
            BudgetLine(
                user_id=user.id,
                category_id=category.id,
                month=date(2026, 10, 1),
                amount=Decimal("30000.00"),
            ),
            Goal(user_id=user.id, name="Отпуск", target_amount=Decimal("120000.00")),
        ]
    )
    session.flush()

    session.delete(user)
    session.flush()
    session.expunge_all()

    for model in (Category, Transaction, MerchantRule, Event, BudgetLine, Goal):
        assert session.scalar(select(func.count()).select_from(model)) == 0


def test_plan_amount_must_be_positive(session: Session) -> None:
    user = make_user(session)
    category = Category(user_id=user.id, name="Продукты")
    session.add(category)
    session.flush()

    session.add(
        BudgetLine(
            user_id=user.id, category_id=category.id, month=date(2026, 10, 1), amount=Decimal("0")
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
