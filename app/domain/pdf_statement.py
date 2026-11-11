"""Bank statements in PDF: most people download them this way, not as CSV or Excel.

Two layouts are supported:
- a drawn table with a header row (e.g. Ozon Bank) — rows are taken as they are;
- a text layout without table lines (e.g. Sberbank) — every operation is two lines:
  «31.10.2026 14:22 Супермаркеты 1 234,56 10 000,00» (date, time, bank category, amount, balance)
  «31.10.2026 123456 PYATEROCHKA 1234. Операция по карте ****1234» (date, code, description).
  Expenses have no sign there and income has «+».
The result is the same list of rows as a CSV file gives, so the rest of the import does not
need to know where the statement came from.
"""

import io
import re
from collections.abc import Sequence

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException

Row = list[str]

_HEADER_HINTS = ("дата", "сумма", "описание", "назначение", "категория")
_DATE = r"\d{2}\.\d{2}\.\d{4}"
_MONEY = r"\d{1,3}(?:[  ]\d{3})*,\d{2}"
_TEXT_OPERATION = re.compile(rf"^({_DATE}) \d{{2}}:\d{{2}} (.+?) (\+?{_MONEY}) {_MONEY}$")
_TEXT_DETAILS = re.compile(rf"^{_DATE} \d{{6}} (.*)$")
_CARD_TAIL = re.compile(r"\.?\s*Операция по (карте|сч[её]ту).*$")
TEXT_COLUMNS = ["Дата операции", "Категория", "Описание", "Сумма"]


def read_pdf_rows(content: bytes) -> list[Row]:
    """All rows of the statement, the header row first; empty if no operations are found.

    Raises ValueError if the file is not a readable PDF.
    """
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            tables = [table for page in pdf.pages for table in page.extract_tables()]
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except PdfminerException:
        raise ValueError("not a readable PDF") from None
    return table_rows(tables) if tables else text_rows(text)


def table_rows(tables: Sequence[Sequence[Sequence[str | None]]]) -> list[Row]:
    """Join the tables of all pages: one header, then every row that starts with a date."""
    header: Row | None = None
    rows: list[Row] = []
    for table in tables:
        for raw in table:
            cells = [" ".join(str(cell or "").split()) for cell in raw]
            if header is None and _looks_like_header(cells):
                header = [cell or f"Колонка {i + 1}" for i, cell in enumerate(cells)]
            elif header is not None and cells and re.match(_DATE, cells[0]):
                rows.append(cells)
    return [header, *rows] if header else []


def text_rows(text: str) -> list[Row]:
    """Rows of a statement laid out as text, with expenses made negative."""
    rows: list[Row] = []
    description: list[str] | None = None
    for line in (line.strip() for line in text.splitlines()):
        operation = _TEXT_OPERATION.match(line)
        details = _TEXT_DETAILS.match(line)
        if operation:
            day, category, amount = operation.groups()
            signed = amount.lstrip("+") if amount.startswith("+") else f"-{amount}"
            rows.append([day, category, category, signed])
            description = None
        elif details and rows:
            description = [details.group(1)]
            rows[-1][2] = _clean_description(description, rows[-1][1])
        elif description is not None and line and not _looks_like_header(line.lower().split()):
            # A long description wraps onto the next lines until the next operation.
            description.append(line)
            rows[-1][2] = _clean_description(description, rows[-1][1])
    return [TEXT_COLUMNS, *rows] if rows else []


def _clean_description(parts: list[str], fallback: str) -> str:
    text = _CARD_TAIL.sub("", " ".join(parts)).strip()
    return text or fallback


def _looks_like_header(cells: Sequence[str]) -> bool:
    joined = " ".join(cells).lower()
    return sum(hint in joined for hint in _HEADER_HINTS) >= 2 and not re.search(_DATE, joined)
