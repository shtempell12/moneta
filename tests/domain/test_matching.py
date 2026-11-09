from datetime import date
from decimal import Decimal

from app.domain.matching import BankRow, Match, TableRow, match_rows


def table_row(day: int, amount: str, category: str, note: str = "") -> TableRow:
    return TableRow(date=date(2026, 10, day), amount=Decimal(amount), category=category, note=note)


def bank_row(key: int, day: int, amount: str, description: str) -> BankRow:
    return BankRow(
        key=key, date=date(2026, 10, day), amount=Decimal(amount), description=description
    )


def test_purchase_posted_next_day_is_matched() -> None:
    table = [table_row(5, "1500", "повар и продукты", "Пятерочка")]
    bank = [bank_row(1, 6, "-1500", "ПЯТЕРОЧКА 1234")]

    assert match_rows(table, bank) == [Match(table_index=0, bank_key=1, days_apart=1)]


def test_rows_outside_the_window_are_not_matched() -> None:
    table = [table_row(1, "1500", "повар и продукты")]
    bank = [bank_row(1, 9, "-1500", "ПЯТЕРОЧКА")]

    assert match_rows(table, bank, window_days=3) == []


def test_exact_matching_is_the_zero_window() -> None:
    table = [table_row(5, "1500", "повар и продукты")]
    bank = [bank_row(1, 6, "-1500", "ПЯТЕРОЧКА")]

    assert match_rows(table, bank, window_days=0) == []


def test_same_amount_twice_pairs_by_the_closest_date() -> None:
    # Two pool payments of 3 500 a week apart.
    table = [table_row(3, "3500", "спорт"), table_row(10, "3500", "спорт")]
    bank = [bank_row(1, 11, "-3500", "БАССЕЙН"), bank_row(2, 4, "-3500", "БАССЕЙН")]

    assert [(m.table_index, m.bank_key) for m in match_rows(table, bank)] == [(0, 2), (1, 1)]


def test_same_day_and_amount_are_told_apart_by_the_name() -> None:
    table = [
        table_row(5, "500", "развивашки", "Студия Лучик"),
        table_row(5, "500", "красота", "Ногти"),
    ]
    bank = [bank_row(1, 5, "-500", "САЛОН НОГОТОК"), bank_row(2, 5, "-500", "СТУДИЯ ЛУЧИК")]

    assert [(m.table_index, m.bank_key) for m in match_rows(table, bank)] == [(0, 2), (1, 1)]


def test_cash_rows_without_a_bank_row_stay_unmatched() -> None:
    table = [table_row(5, "700", "повар и продукты", "Рынок"), table_row(6, "63", "транспорт")]
    bank = [bank_row(1, 6, "-63", "МЕТРО")]

    assert match_rows(table, bank) == [Match(table_index=1, bank_key=1, days_apart=0)]


def test_each_bank_row_is_used_once() -> None:
    table = [table_row(5, "63", "транспорт"), table_row(5, "63", "транспорт")]
    bank = [bank_row(1, 5, "-63", "МЕТРО")]

    assert len(match_rows(table, bank)) == 1
