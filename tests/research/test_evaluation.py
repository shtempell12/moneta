from datetime import date
from decimal import Decimal
from pathlib import Path

from research.dataset import LabeledTransaction, read_dataset, write_dataset
from research.evaluation import evaluate, mixed_merchants, split_last_month, summarize
from research.synthetic import generate


def tx(day: date, description: str, category: str, bank: str | None = None) -> LabeledTransaction:
    return LabeledTransaction(
        user="family-1",
        date=day,
        amount=Decimal("-500"),
        description=description,
        bank_category=bank,
        category=category,
    )


ROWS = [
    tx(date(2026, 8, 3), "Аптека Ригла", "Здоровье", "Аптеки"),
    tx(date(2026, 9, 5), "Аптека Ригла", "Красота", "Аптеки"),
    tx(date(2026, 9, 20), "Студия Лучик", "Развивашки", "Образование"),
    tx(date(2026, 10, 2), "Студия Лучик", "Развивашки", "Образование"),
    tx(date(2026, 10, 9), "Аптека Ригла", "Здоровье", "Аптеки"),
]


def test_last_month_is_the_test_and_earlier_months_are_training() -> None:
    split = split_last_month(ROWS)

    assert [row.date.month for row in split.train] == [8, 9, 9]
    assert [row.date.month for row in split.test] == [10, 10]


def test_history_can_be_limited_to_the_days_before_the_test_month() -> None:
    split = split_last_month(ROWS, history_days=30)

    assert [row.date for row in split.train] == [date(2026, 9, 5), date(2026, 9, 20)]


def test_income_is_not_checked() -> None:
    salary = LabeledTransaction(
        "family-1", date(2026, 10, 10), Decimal("85000"), "Зарплата", None, "Зарплата"
    )

    assert salary not in split_last_month([*ROWS, salary]).test


def test_pharmacy_filed_under_two_categories_is_a_mixed_merchant() -> None:
    assert mixed_merchants(split_last_month(ROWS).train) == {"аптека ригла"}


def test_personal_category_beats_the_bank_baseline() -> None:
    results = {result.approach: result for result in evaluate(ROWS)}

    # Bank: «Образование» is not «Развивашки», «Аптеки» → «Здоровье» is right.
    assert (results["bank"].correct, results["bank"].total) == (1, 2)
    # History knows «Лучик» is «Развивашки»; the pharmacy's latest choice was «Красота».
    assert results["last_choice"].correct == 1
    assert results["most_frequent"].mixed_total == 1


def test_summary_has_one_row_per_approach() -> None:
    summaries = summarize(evaluate(ROWS))

    assert [summary.approach for summary in summaries] == [
        "bank",
        "last_choice",
        "most_frequent",
        "classifier",
        "cascade",
    ]


def test_dataset_survives_a_round_trip_through_csv(tmp_path: Path) -> None:
    path = tmp_path / "labeled.csv"

    write_dataset(ROWS, path)

    assert read_dataset(path) == ROWS


def test_synthetic_data_is_the_same_for_the_same_seed() -> None:
    assert generate(seed=1) == generate(seed=1)
    assert {row.user for row in generate()} == {"family-1", "family-2", "family-3", "family-4"}


def test_transfers_are_left_out_of_the_check_but_counted() -> None:
    transfer = tx(date(2026, 10, 12), "Перевод Ивану И.", "Подарки", "Перевод с карты")

    split = split_last_month([*ROWS, transfer])

    assert transfer not in split.test
    assert split.transfers == 1
    assert evaluate([*ROWS, transfer])[0].transfers == 1
