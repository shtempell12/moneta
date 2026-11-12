"""The user's own budget table (Excel or Google Sheets): «Когда», «Что», «Статья», «Сколько».

Families who keep a budget in a table have already filed every purchase under their own
category. Read and matched with the bank statement, the table gives the categorizer the
family's history from day one (hypothesis H-DEV3).
"""

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from app.domain.matching import TableRow
from app.domain.parsing import parse_amount, parse_date
from app.domain.statement import RowError

# Words that mark the header row of a budget table, to tell it from title lines above it.
TABLE_HEADER_HINTS = ("дата", "когда", "сумма", "сколько", "категория", "статья", "бюджет")

# Keywords for each field, most specific first; a column is used for one field only.
_COLUMN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "date": ("дата", "когда"),
    "amount": ("сумма", "сколько", "rur", "руб"),
    "category": ("категория", "статья", "бюджет"),
    "note": ("что", "описание", "назначение", "комментарий"),
    "spender": ("кто",),
}


@dataclass(frozen=True)
class TableMapping:
    date: str
    amount: str
    category: str
    note: str | None = None
    spender: str | None = None


@dataclass(frozen=True)
class ParsedTable:
    rows: list[TableRow]
    errors: list[RowError]


def guess_table_columns(columns: Sequence[str]) -> dict[str, str | None]:
    """Guess which column is the date, amount, category, note and «who spent»."""
    guess: dict[str, str | None] = {}
    used: set[str] = set()
    for field, keywords in _COLUMN_KEYWORDS.items():
        guess[field] = next(
            (
                column
                for keyword in keywords
                for column in columns
                if keyword in column.lower() and column not in used
            ),
            None,
        )
        if guess[field]:
            used.add(guess[field] or "")
    return guess


def parse_table_rows(table: pd.DataFrame, mapping: TableMapping) -> ParsedTable:
    """Rows with a date, an amount and a category; empty lines are skipped, bad ones reported.

    Lines without a category (subtotals, blank months) are not purchases and are skipped.
    """
    first_line = int(table.attrs.get("first_data_line", 2))
    rows: list[TableRow] = []
    errors: list[RowError] = []
    for index, record in enumerate(table.to_dict("records")):
        category = _text(record.get(mapping.category))
        if not category:
            continue
        try:
            rows.append(
                TableRow(
                    date=parse_date(record[mapping.date]),
                    amount=abs(parse_amount(record[mapping.amount])),
                    category=category[:100],
                    note=_text(record.get(mapping.note)) if mapping.note else "",
                    spender=(_text(record.get(mapping.spender)) or None)
                    if mapping.spender
                    else None,
                )
            )
        except ValueError as error:
            errors.append(RowError(line=first_line + index, message=str(error)))
    return ParsedTable(rows=rows, errors=errors)


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return " ".join(str(value).split())
