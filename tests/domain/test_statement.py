import io
from datetime import date, datetime
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.domain.statement import (
    ColumnMapping,
    StatementFormatError,
    guess_columns,
    parse_rows,
    read_table,
)

# Synthetic statement in the layout of a typical Russian bank CSV export.
TBANK_LIKE_CSV = "\n".join(
    [
        "Дата операции;Дата платежа;Номер карты;Статус;Сумма операции;Валюта операции;"
        "Сумма платежа;Валюта платежа;Категория;Описание",
        "31.10.2026 19:04:11;31.10.2026;*1234;OK;-1 234,56;RUB;-1 234,56;RUB;"
        "Супермаркеты;ПЯТЕРОЧКА 1234",
        "30.10.2026 08:15:00;30.10.2026;*1234;OK;-350,00;RUB;-350,00;RUB;Рестораны;Кофейня Зерно",
        "29.10.2026 12:00:00;29.10.2026;*1234;OK;+85 000,00;RUB;+85 000,00;RUB;"
        "Пополнения;Зарплата ООО Ромашка",
    ]
)

TBANK_MAPPING = ColumnMapping(
    date="Дата операции",
    amount="Сумма платежа",
    description="Описание",
    bank_category="Категория",
)


def make_xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_reads_windows_1251_csv_with_semicolons() -> None:
    table = read_table(TBANK_LIKE_CSV.encode("cp1251"), "operations.csv")

    parsed = parse_rows(table, TBANK_MAPPING)

    assert parsed.errors == []
    assert parsed.rows[0].date == date(2026, 10, 31)
    assert parsed.rows[0].amount == Decimal("-1234.56")
    assert parsed.rows[0].description == "ПЯТЕРОЧКА 1234"
    assert parsed.rows[0].bank_category == "Супермаркеты"
    assert parsed.rows[2].amount == Decimal("85000.00")


def test_reads_utf8_csv_with_commas() -> None:
    content = 'Дата,Сумма,Описание\n01.10.2026,"-99,90",Метро\n'.encode()

    table = read_table(content, "statement.csv")
    parsed = parse_rows(table, ColumnMapping(date="Дата", amount="Сумма", description="Описание"))

    assert parsed.rows[0].amount == Decimal("-99.90")
    assert parsed.rows[0].bank_category is None


def test_reads_excel_with_preamble_above_the_table() -> None:
    content = make_xlsx(
        [
            ["Выписка по счёту 40817810..."],
            ["Период: 01.10.2026 — 31.10.2026"],
            [],
            ["Дата операции", "Сумма", "Описание операции", "Категория"],
            [datetime(2026, 10, 5, 13, 30), -1234.56, "ВКУСВИЛЛ", "Супермаркеты"],
        ]
    )

    table = read_table(content, "выписка.xlsx")
    mapping = ColumnMapping(
        date="Дата операции",
        amount="Сумма",
        description="Описание операции",
        bank_category="Категория",
    )
    parsed = parse_rows(table, mapping)

    assert parsed.rows[0].date == date(2026, 10, 5)
    assert parsed.rows[0].amount == Decimal("-1234.56")


def test_guesses_columns_of_a_typical_bank_export() -> None:
    table = read_table(TBANK_LIKE_CSV.encode(), "operations.csv")

    guess = guess_columns(list(table.columns))

    assert guess == {
        "date": "Дата операции",
        "amount": "Сумма платежа",
        "description": "Описание",
        "bank_category": "Категория",
    }


def test_bad_rows_are_reported_with_line_numbers_and_good_rows_kept() -> None:
    content = (
        "Дата;Сумма;Описание\n01.10.2026;-100;Метро\nвчера;-200;Такси\n02.10.2026;много;Кафе\n"
    )

    table = read_table(content.encode(), "statement.csv")
    parsed = parse_rows(table, ColumnMapping(date="Дата", amount="Сумма", description="Описание"))

    assert len(parsed.rows) == 1
    assert [error.line for error in parsed.errors] == [3, 4]
    assert "дату" in parsed.errors[0].message


def test_empty_lines_are_skipped() -> None:
    content = "Дата;Сумма;Описание\n01.10.2026;-100;Метро\n;;\n"

    table = read_table(content.encode(), "statement.csv")
    parsed = parse_rows(table, ColumnMapping(date="Дата", amount="Сумма", description="Описание"))

    assert len(parsed.rows) == 1
    assert parsed.errors == []


def test_unsupported_format_is_rejected_with_a_clear_message() -> None:
    with pytest.raises(StatementFormatError, match="CSV, Excel"):
        read_table(b"PK", "statement.docx")


def test_broken_pdf_is_rejected_with_a_clear_message() -> None:
    with pytest.raises(StatementFormatError, match="Не удалось открыть PDF"):
        read_table(b"%PDF-1.4", "statement.pdf")


def test_file_without_operations_table_is_rejected() -> None:
    with pytest.raises(StatementFormatError, match="Не нашли"):
        read_table("просто текст\nбез таблицы\n".encode(), "notes.csv")
