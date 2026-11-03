from decimal import Decimal

from app.domain.plan import plan_vs_fact


def rub(value: str) -> Decimal:
    return Decimal(value)


def test_left_and_share_of_plan_used() -> None:
    result = plan_vs_fact({"Продукты": rub("30000")}, {"Продукты": rub("21500")})

    row = result.rows[0]
    assert (row.planned, row.spent, row.left) == (rub("30000"), rub("21500"), rub("8500"))
    assert row.used_percent == 72
    assert row.overspent == 0


def test_overspending_is_shown_as_positive_amount() -> None:
    row = plan_vs_fact({"Продукты": rub("30000")}, {"Продукты": rub("32500")}).rows[0]

    assert row.left == rub("-2500")
    assert row.overspent == rub("2500")
    assert row.used_percent == 108


def test_planned_category_without_spending_has_nothing_spent() -> None:
    row = plan_vs_fact({"Подарки": rub("5000")}, {}).rows[0]

    assert (row.spent, row.left, row.used_percent) == (0, rub("5000"), 0)


def test_spending_without_plan_comes_after_planned_categories() -> None:
    result = plan_vs_fact(
        {"Кафе": rub("5000"), "Продукты": rub("30000")},
        {"Такси": rub("2000"), "Продукты": rub("10000"), "Одежда": rub("7000")},
    )

    assert [row.name for row in result.rows] == ["Продукты", "Кафе", "Одежда", "Такси"]
    unplanned = result.rows[2]
    assert (unplanned.planned, unplanned.left, unplanned.used_percent) == (None, None, 0)


def test_totals_count_all_spending_against_the_whole_plan() -> None:
    result = plan_vs_fact(
        {"Продукты": rub("30000"), "Кафе": rub("5000")},
        {"Продукты": rub("25000"), "Такси": rub("3000")},
    )

    assert (result.planned, result.spent, result.left) == (rub("35000"), rub("28000"), rub("7000"))
    assert result.has_plan


def test_month_without_plan() -> None:
    result = plan_vs_fact({}, {"Продукты": rub("100")})

    assert not result.has_plan
    assert result.left == rub("-100")
