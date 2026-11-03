from datetime import date
from decimal import Decimal

import pytest

from app.domain.entries import EntryError, EntryForm, make_entry
from app.domain.enums import CategoryKind


def form(amount: str = "1 500", description: str = "Рынок", spender: str = "") -> EntryForm:
    return EntryForm(
        date="2026-10-05", amount=amount, description=description, category_id=1, spender=spender
    )


def test_expense_typed_without_sign_becomes_negative() -> None:
    entry = make_entry(form("1 500,50"), CategoryKind.EXPENSE, "Продукты")

    assert entry.date == date(2026, 10, 5)
    assert entry.amount == Decimal("-1500.50")
    assert entry.description == "Рынок"


def test_income_category_makes_amount_positive() -> None:
    entry = make_entry(form("85 000", "Аванс"), CategoryKind.INCOME, "Зарплата")

    assert entry.amount == Decimal("85000.00")


def test_typed_minus_does_not_flip_the_sign_twice() -> None:
    assert make_entry(form("-300"), CategoryKind.EXPENSE, "Кафе").amount == Decimal("-300.00")


def test_empty_description_takes_the_category_name() -> None:
    assert make_entry(form(description="  "), CategoryKind.EXPENSE, "Такси").description == "Такси"


def test_spender_is_trimmed_and_optional() -> None:
    assert make_entry(form(spender="  муж "), CategoryKind.EXPENSE, "Кафе").spender == "муж"
    assert make_entry(form(spender=""), CategoryKind.EXPENSE, "Кафе").spender is None


@pytest.mark.parametrize(
    ("amount", "message"),
    [("abc", "числом"), ("0", "больше нуля"), ("NaN", "больше нуля"), ("1e12", "большая")],
)
def test_bad_amounts_are_rejected_with_a_clear_message(amount: str, message: str) -> None:
    with pytest.raises(EntryError, match=message):
        make_entry(form(amount), CategoryKind.EXPENSE, "Продукты")


def test_missing_date_is_rejected() -> None:
    bad = EntryForm(date="", amount="100", description="", category_id=1)

    with pytest.raises(EntryError, match="дату"):
        make_entry(bad, CategoryKind.EXPENSE, "Продукты")
