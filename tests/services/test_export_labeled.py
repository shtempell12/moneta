from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import Transaction
from app.services.imports import import_statement
from research.export_labeled import labeled_transactions
from tests.services.conftest import row, statement


def test_only_categorized_transactions_are_exported_under_a_pseudonym(
    session: Session, user_id: int
) -> None:
    import_statement(
        session,
        user_id,
        "october.csv",
        statement(row(3, "-1500", "ПЯТЕРОЧКА", "Супермаркеты"), row(4, "-300", "ИП СМИРНОВА")),
    )

    rows = labeled_transactions(session, " Anna@mail.ru ", "participant-1")

    assert [(r.user, r.date, r.amount, r.category) for r in rows] == [
        ("participant-1", date(2026, 10, 3), Decimal("-1500.00"), "Продукты")
    ]
    assert session.query(Transaction).count() == 2
