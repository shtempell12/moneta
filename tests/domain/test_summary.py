from decimal import Decimal

from app.domain.enums import CategorySource
from app.domain.summary import UNCATEGORIZED, SummaryEntry, summarize_month

BANK, HISTORY, MANUAL = CategorySource.BANK, CategorySource.HISTORY, CategorySource.MANUAL


def entry(category: str | None, amount: str, source: CategorySource | None) -> SummaryEntry:
    return SummaryEntry(category_name=category, amount=Decimal(amount), source=source)


def test_spending_is_split_by_category_largest_first() -> None:
    summary = summarize_month(
        [
            entry("Кафе и рестораны", "-1000", BANK),
            entry("Продукты", "-2000", BANK),
            entry("Продукты", "-1000", HISTORY),
        ]
    )

    assert summary.spent == Decimal("4000")
    assert [(c.name, c.spent, c.percent) for c in summary.by_category] == [
        ("Продукты", Decimal("3000"), 75),
        ("Кафе и рестораны", Decimal("1000"), 25),
    ]


def test_income_is_counted_separately_from_spending() -> None:
    summary = summarize_month(
        [entry("Зарплата", "85000.00", BANK), entry("Продукты", "-1234.56", BANK)]
    )

    assert summary.income == Decimal("85000.00")
    assert summary.spent == Decimal("1234.56")
    assert summary.expenses_count == 1


def test_transactions_without_category_are_shown_as_uncategorized() -> None:
    summary = summarize_month([entry(None, "-500", None)])

    assert summary.by_category[0].name == UNCATEGORIZED
    assert summary.uncategorized_count == 1


def test_auto_and_manual_shares_of_expenses() -> None:
    # 17 of 20 expenses categorized automatically, 2 fixed by hand, 1 left without category.
    entries = (
        [entry("Продукты", "-100", BANK)] * 10
        + [entry("Продукты", "-100", HISTORY)] * 7
        + [entry("Дети", "-100", MANUAL)] * 2
        + [entry(None, "-100", None)]
    )

    summary = summarize_month(entries)

    assert summary.auto_percent == 85
    assert summary.manual_percent == 10
    assert summary.uncategorized_count == 1


def test_empty_month_has_zero_shares_instead_of_division_error() -> None:
    summary = summarize_month([])

    assert summary.spent == Decimal("0")
    assert summary.auto_percent == 0
    assert summary.by_category == []
