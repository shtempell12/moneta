from decimal import Decimal

import pytest

from app.web.templating import format_plan_amount, format_rub, plural


def test_rub_uses_russian_separators() -> None:
    assert format_rub(Decimal("-1234.5")) == "−1 234,50 ₽"
    assert format_rub(Decimal("85000")) == "85 000,00 ₽"


def test_rub_shows_plus_for_income_when_asked() -> None:
    assert format_rub(Decimal("100"), signed=True) == "+100,00 ₽"
    assert format_rub(Decimal("0"), signed=True) == "0,00 ₽"


@pytest.mark.parametrize(
    ("count", "word"),
    [(1, "операция"), (2, "операции"), (5, "операций"), (11, "операций"), (21, "операция"),
     (22, "операции"), (112, "операций")],
)  # fmt: skip
def test_plural(count: int, word: str) -> None:
    assert plural(count, "операция", "операции", "операций") == word


def test_plan_amount_for_input_field() -> None:
    assert format_plan_amount(Decimal("30000.00")) == "30 000"
    assert format_plan_amount(Decimal("1500.50")) == "1 500,50"
