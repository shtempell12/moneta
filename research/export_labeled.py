"""Export one participant's categorized transactions from the local database for H-ML1.

The participant uploads statements into Moneta and checks every transaction, fixing wrong
categories; after that each category is the participant's own choice — the label.
The email is replaced with a pseudonym, and only counts are printed.

Usage:
    make export-labeled EMAIL=participant@mail.ru NAME=participant-1
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Category, Transaction, User
from research.dataset import LabeledTransaction, read_dataset, write_dataset

OUTPUT = Path("data/labeled.csv")


def labeled_transactions(session: Session, email: str, name: str) -> list[LabeledTransaction]:
    rows = session.execute(
        select(Transaction, Category.name)
        .join(Category, Category.id == Transaction.category_id)
        .join(User, User.id == Transaction.user_id)
        .where(User.email == email.strip().lower())
        .order_by(Transaction.date, Transaction.id)
    )
    return [
        LabeledTransaction(
            user=name,
            date=transaction.date,
            amount=transaction.amount,
            description=transaction.description,
            bank_category=transaction.bank_category,
            category=category,
        )
        for transaction, category in rows
    ]


def main(argv: Sequence[str]) -> None:
    email, name = argv
    with Session(create_engine(get_settings().database_url)) as session:
        rows = labeled_transactions(session, email, name)
    # Other participants already in the file are kept; this one is replaced.
    others = [row for row in read_dataset(OUTPUT) if row.user != name] if OUTPUT.exists() else []
    write_dataset(others + rows, OUTPUT)
    months = sorted({row.date.strftime("%Y-%m") for row in rows})
    print(f"{name}: {len(rows)} операций с категориями, месяцы: {', '.join(months)}")
    print(f"Участников в {OUTPUT}: {len({row.user for row in others + rows})}")


if __name__ == "__main__":
    main(sys.argv[1:])
