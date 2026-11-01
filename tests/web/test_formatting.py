from decimal import Decimal

from app.web.templating import format_rub


def test_rub_uses_russian_separators() -> None:
    assert format_rub(Decimal("-1234.5")) == "−1 234,50 ₽"
    assert format_rub(Decimal("85000")) == "85 000,00 ₽"


def test_rub_shows_plus_for_income_when_asked() -> None:
    assert format_rub(Decimal("100"), signed=True) == "+100,00 ₽"
    assert format_rub(Decimal("0"), signed=True) == "0,00 ₽"
