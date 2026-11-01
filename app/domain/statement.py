"""Reading bank statements (CSV / Excel) into a uniform list of rows."""

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd

from app.domain.parsing import parse_amount, parse_date

# Banks put a few lines of preamble (account number, period) above the table.
_HEADER_SEARCH_ROWS = 20
_HEADER_HINTS = ("дата", "сумма", "описание", "категория")

# Keywords for each field, most specific first. "Сумма платежа" goes before "сумма операции":
# for purchases abroad it is the amount actually charged in rubles.
_COLUMN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "date": ("дата операции", "дата"),
    "amount": ("сумма платежа", "сумма операции", "сумма"),
    "description": ("описание", "назначение", "наименование", "контрагент", "магазин"),
    "bank_category": ("категория",),
}


@dataclass(frozen=True)
class ColumnMapping:
    """Which column of the file holds which field."""

    date: str
    amount: str
    description: str
    bank_category: str | None = None


@dataclass(frozen=True)
class StatementRow:
    date: date
    amount: Decimal
    description: str
    bank_category: str | None


@dataclass(frozen=True)
class RowError:
    line: int
    message: str


@dataclass(frozen=True)
class ParsedStatement:
    rows: list[StatementRow]
    errors: list[RowError]


class StatementFormatError(ValueError):
    """The file cannot be read as a statement; the message is safe to show to the user."""


def read_table(content: bytes, file_name: str) -> pd.DataFrame:
    """Read a CSV or Excel file into a table with the header row detected automatically."""
    if file_name.lower().endswith((".xlsx", ".xlsm")):
        raw = pd.read_excel(io.BytesIO(content), header=None, dtype=object)
    elif file_name.lower().endswith((".csv", ".txt")):
        text = _decode(content)
        raw = pd.read_csv(
            io.StringIO(text),
            sep=_detect_separator(text),
            header=None,
            dtype=str,
            keep_default_na=False,
            skip_blank_lines=True,
            engine="python",
        )
    else:
        raise StatementFormatError("Поддерживаются файлы CSV и Excel (.xlsx)")

    header_index = _find_header_row(raw)
    table = raw.iloc[header_index + 1 :].reset_index(drop=True)
    table.columns = [str(name).strip() for name in raw.iloc[header_index]]
    table.attrs["first_data_line"] = header_index + 2
    return table


def guess_columns(columns: list[str]) -> dict[str, str | None]:
    """Guess which column is the date, amount, description and bank category."""
    guess: dict[str, str | None] = {}
    used: set[str] = set()
    for field, keywords in _COLUMN_KEYWORDS.items():
        guess[field] = None
        for keyword in keywords:
            match = next(
                (c for c in columns if keyword in c.lower() and c not in used),
                None,
            )
            if match:
                guess[field] = match
                used.add(match)
                break
    return guess


def parse_rows(table: pd.DataFrame, mapping: ColumnMapping) -> ParsedStatement:
    """Turn table rows into statement rows; bad rows are reported, not silently dropped."""
    first_line = int(table.attrs.get("first_data_line", 2))
    rows: list[StatementRow] = []
    errors: list[RowError] = []
    for index, record in enumerate(table.to_dict("records")):
        if all(_is_blank(value) for value in record.values()):
            continue
        try:
            description = str(record[mapping.description]).strip()
            if not description:
                raise ValueError("Пустое описание операции")
            bank_category = (
                str(record[mapping.bank_category]).strip() or None
                if mapping.bank_category
                else None
            )
            rows.append(
                StatementRow(
                    date=parse_date(record[mapping.date]),
                    amount=parse_amount(record[mapping.amount]),
                    description=description,
                    bank_category=bank_category,
                )
            )
        except ValueError as error:
            errors.append(RowError(line=first_line + index, message=str(error)))
    return ParsedStatement(rows=rows, errors=errors)


def _decode(content: bytes) -> str:
    # Most banks export UTF-8, some still use Windows-1251.
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1251")


def _detect_separator(text: str) -> str:
    sample = "\n".join(text.splitlines()[:_HEADER_SEARCH_ROWS])
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
    except csv.Error:
        return ";"


def _find_header_row(raw: pd.DataFrame) -> int:
    for index in range(min(_HEADER_SEARCH_ROWS, len(raw))):
        cells = " ".join(str(value).lower() for value in raw.iloc[index].tolist())
        if sum(hint in cells for hint in _HEADER_HINTS) >= 2:
            return index
    raise StatementFormatError(
        "Не нашли в файле таблицу операций: нужны колонки с датой, суммой и описанием"
    )


def _is_blank(value: object) -> bool:
    return (
        value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ""
    )
