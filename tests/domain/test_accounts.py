import pytest

from app.domain.accounts import (
    DEFAULT_CATEGORIES,
    email_problem,
    normalize_email,
    password_problem,
)
from app.domain.enums import CategoryKind


def test_email_is_normalized_to_lowercase_without_spaces() -> None:
    assert normalize_email("  Anna.Petrova@Mail.RU ") == "anna.petrova@mail.ru"


@pytest.mark.parametrize("email", ["anna@mail.ru", "anna.petrova+budget@yandex.ru"])
def test_valid_emails_pass(email: str) -> None:
    assert email_problem(email) is None


@pytest.mark.parametrize("email", ["", "anna", "anna@", "@mail.ru", "anna@mail"])
def test_invalid_emails_are_reported(email: str) -> None:
    assert email_problem(email) is not None


def test_short_password_is_rejected() -> None:
    assert password_problem("1234567") == "Пароль должен быть не короче 8 символов"


def test_password_of_eight_characters_is_accepted() -> None:
    assert password_problem("12345678") is None


def test_default_categories_cover_expenses_and_income() -> None:
    assert "Продукты" in DEFAULT_CATEGORIES[CategoryKind.EXPENSE]
    assert "Зарплата" in DEFAULT_CATEGORIES[CategoryKind.INCOME]
