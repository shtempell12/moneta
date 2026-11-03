from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.domain.statement import ParsedStatement, StatementRow
from app.services import auth


@pytest.fixture
def user_id(session: Session) -> int:
    """A registered user with the default categories."""
    auth.register(session, "anna@mail.ru", "надёжный-пароль", pd_consent=True)
    return session.scalars(select(User.id)).one()


def row(
    day: int, amount: str, description: str, bank_category: str | None = None, month: int = 10
) -> StatementRow:
    return StatementRow(
        date=date(2026, month, day),
        amount=Decimal(amount),
        description=description,
        bank_category=bank_category,
    )


def statement(*rows: StatementRow) -> ParsedStatement:
    return ParsedStatement(rows=list(rows), errors=[])
