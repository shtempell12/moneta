from datetime import date
from decimal import Decimal

from app.domain.budget_table import (
    TABLE_HEADER_HINTS,
    TableMapping,
    guess_table_columns,
    parse_table_rows,
)
from app.domain.statement import read_table

# Made-up rows in the layout of a family budget table from an interview (no real data).
TABLE = "\n".join(
    [
        "Расходы семьи;;;;;",
        "Когда;Месяц;Что;Бюджет;Сколько;Кто?",
        "01.10.2026;10;Спорт 1;спорт;3 500;Жена",
        "02.10.2026;10;Пятерочка;Повар и продукты;1 234,50;",
        ";;;;;",
        "03.10.2026;10;Итого за день;;4 734,50;",
        "04.10.2026;10;ВБ;бытовые расходы;сто;Муж",
    ]
).encode("utf-8")


def test_columns_of_an_interview_table_are_recognized() -> None:
    columns = ["Когда", "Месяц", "Что", "Откуда расход", "Бюджет", "Сколько", "Валюта", "Кто?"]

    assert guess_table_columns(columns) == {
        "date": "Когда",
        "amount": "Сколько",
        "category": "Бюджет",
        "note": "Что",
        "spender": "Кто?",
    }


def test_rows_are_read_with_positive_amounts_and_bad_lines_reported() -> None:
    table = read_table(TABLE, "budget.csv", TABLE_HEADER_HINTS)
    mapping = TableMapping(
        date="Когда", amount="Сколько", category="Бюджет", note="Что", spender="Кто?"
    )

    parsed = parse_table_rows(table, mapping)

    assert [(r.date, r.amount, r.category, r.note, r.spender) for r in parsed.rows] == [
        (date(2026, 10, 1), Decimal("3500.00"), "спорт", "Спорт 1", "Жена"),
        (date(2026, 10, 2), Decimal("1234.50"), "Повар и продукты", "Пятерочка", None),
    ]
    assert [error.line for error in parsed.errors] == [7]


def test_table_without_optional_columns_still_reads() -> None:
    content = "Дата;Сумма;Категория\n05.10.2026;-700;Продукты".encode()
    table = read_table(content, "simple.csv", TABLE_HEADER_HINTS)

    parsed = parse_table_rows(
        table, TableMapping(date="Дата", amount="Сумма", category="Категория")
    )

    assert parsed.rows[0].amount == Decimal("700.00")
    assert parsed.rows[0].note == ""
