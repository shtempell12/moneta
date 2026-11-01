from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.parsing import merchant_key, parse_amount, parse_date


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-1 234,56", Decimal("-1234.56")),
        ("-1 234,56 ₽", Decimal("-1234.56")),
        ("−1 234,56", Decimal("-1234.56")),
        ("+500", Decimal("500.00")),
        ("1234.5", Decimal("1234.50")),
        ("-350,00 руб.", Decimal("-350.00")),
        ("  -99,9 RUB ", Decimal("-99.90")),
        (-1234.56, Decimal("-1234.56")),
        (0.1 + 0.2, Decimal("0.30")),
        (700, Decimal("700.00")),
    ],
)
def test_parse_amount(raw: object, expected: Decimal) -> None:
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "12,34,56"])
def test_parse_amount_rejects_garbage(raw: str) -> None:
    with pytest.raises(ValueError, match="сумму"):
        parse_amount(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("31.10.2026", date(2026, 10, 31)),
        ("31.10.2026 14:22:05", date(2026, 10, 31)),
        ("2026-10-31", date(2026, 10, 31)),
        ("01.02.26", date(2026, 2, 1)),
        (datetime(2026, 10, 31, 14, 22), date(2026, 10, 31)),
        (date(2026, 10, 31), date(2026, 10, 31)),
    ],
)
def test_parse_date(raw: object, expected: date) -> None:
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "вчера", "32.10.2026"])
def test_parse_date_rejects_garbage(raw: str) -> None:
    with pytest.raises(ValueError, match="дату"):
        parse_date(raw)


def test_merchant_key_ignores_store_numbers_case_and_punctuation() -> None:
    assert merchant_key("ПЯТЕРОЧКА 1234 Москва") == merchant_key("Пятерочка #5678, МОСКВА")
    assert merchant_key("ПЯТЕРОЧКА 1234 Москва") == "пятерочка москва"


def test_merchant_key_treats_yo_as_e() -> None:
    assert merchant_key("Ёлки-Палки") == merchant_key("елки палки")
