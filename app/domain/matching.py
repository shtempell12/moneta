"""Matching the user's own budget table with bank statement rows (hypothesis H-DEV3).

A family that keeps its budget in Excel already has every card purchase filed under its own
category. If a table row finds its bank row, that bank row gets the family's category,
and the categorizer learns from day one instead of after a month of corrections.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.parsing import merchant_key

# The table usually has the purchase date and the bank the posting date, 1–3 days later.
DEFAULT_WINDOW_DAYS = 3


@dataclass(frozen=True)
class TableRow:
    """A row of the user's budget table: «Когда», «Что», «Статья», «Сколько»."""

    date: date
    amount: Decimal
    category: str
    note: str = ""


@dataclass(frozen=True)
class BankRow:
    key: int
    date: date
    amount: Decimal
    description: str


@dataclass(frozen=True)
class Match:
    table_index: int
    bank_key: int
    days_apart: int


def match_rows(
    table: Sequence[TableRow],
    bank: Sequence[BankRow],
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> list[Match]:
    """Pair table rows with bank rows of the same amount within ±window_days.

    Amounts are compared without sign: tables often write an expense of 1 500 as «1500».
    When several pairs are possible, the closest dates win, then the more similar text
    («Студия Лучик» in the table, «СТУДИЯ ЛУЧИК» in the bank).
    Each row is used at most once. window_days=0 is exact matching — the baseline.
    Rows without a pair (cash, transfers) are simply left out.
    """
    candidates = [
        (
            abs((row.date - bank_row.date).days),
            -_similarity(row.note, bank_row.description),
            index,
            bank_row.key,
        )
        for index, row in enumerate(table)
        for bank_row in bank
        if abs(row.amount) == abs(bank_row.amount)
        and abs((row.date - bank_row.date).days) <= window_days
    ]
    matches: list[Match] = []
    used_table: set[int] = set()
    used_bank: set[int] = set()
    for days_apart, _, index, bank_key in sorted(candidates):
        if index in used_table or bank_key in used_bank:
            continue
        matches.append(Match(table_index=index, bank_key=bank_key, days_apart=days_apart))
        used_table.add(index)
        used_bank.add(bank_key)
    return sorted(matches, key=lambda match: match.table_index)


def _similarity(note: str, description: str) -> float:
    """Share of common three-letter pieces of the two names: 0 — nothing in common, 1 — same."""
    left, right = _trigrams(note), _trigrams(description)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _trigrams(text: str) -> set[str]:
    key = merchant_key(text).replace(" ", "")
    return {key[i : i + 3] for i in range(len(key) - 2)}
