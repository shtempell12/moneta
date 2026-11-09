"""Labeled transactions: what the bank exported plus the category the user chose.

CSV columns: user, date (YYYY-MM-DD), amount (signed, «.» as decimal point), description,
bank_category (may be empty), category (the user's own category name).
Real data lives only in data/ (git-ignored) and is anonymized before it gets there.
"""

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.domain.parsing import merchant_key

COLUMNS = ["user", "date", "amount", "description", "bank_category", "category"]


@dataclass(frozen=True)
class LabeledTransaction:
    user: str
    date: date
    amount: Decimal
    description: str
    bank_category: str | None
    category: str

    @property
    def merchant(self) -> str:
        return merchant_key(self.description)


def read_dataset(path: Path) -> list[LabeledTransaction]:
    with path.open(encoding="utf-8", newline="") as file:
        return [
            LabeledTransaction(
                user=row["user"],
                date=date.fromisoformat(row["date"]),
                amount=Decimal(row["amount"]),
                description=row["description"],
                bank_category=row["bank_category"] or None,
                category=row["category"],
            )
            for row in csv.DictReader(file)
        ]


def write_dataset(rows: list[LabeledTransaction], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow(
                [
                    row.user,
                    row.date.isoformat(),
                    row.amount,
                    row.description,
                    row.bank_category or "",
                    row.category,
                ]
            )
