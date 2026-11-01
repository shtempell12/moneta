from datetime import date

import pytest

from app.domain.months import month_param, month_title, next_month, parse_month

TODAY = date(2026, 11, 15)


def test_parse_month_from_url_value() -> None:
    assert parse_month("2026-10", TODAY) == date(2026, 10, 1)


@pytest.mark.parametrize("value", [None, "", "октябрь", "2026-13", "2026"])
def test_parse_month_falls_back_to_current_month(value: str | None) -> None:
    assert parse_month(value, TODAY) == date(2026, 11, 1)


def test_next_month_crosses_the_year() -> None:
    assert next_month(date(2026, 12, 1)) == date(2027, 1, 1)
    assert next_month(date(2026, 10, 1)) == date(2026, 11, 1)


def test_month_title_and_param() -> None:
    assert month_title(date(2026, 10, 1)) == "Октябрь 2026"
    assert month_param(date(2026, 3, 1)) == "2026-03"
