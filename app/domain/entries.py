"""Transactions the user adds by hand: cash and anything the bank statement does not show."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.enums import CategoryKind
from app.domain.parsing import parse_amount, parse_date

MAX_DESCRIPTION_LENGTH = 500
MAX_SPENDER_LENGTH = 50
# NUMERIC(12, 2) in the database holds up to 10 digits before the point.
MAX_AMOUNT = Decimal("9999999999.99")


class EntryError(ValueError):
    """Invalid form field; the message is safe to show to the user."""


@dataclass(frozen=True)
class EntryForm:
    """The form fields exactly as the user typed them."""

    date: str
    amount: str
    description: str
    category_id: int
    spender: str = ""


@dataclass(frozen=True)
class ManualEntry:
    date: date
    # Signed, like bank transactions: negative is an expense, positive is income.
    amount: Decimal
    description: str
    spender: str | None


def make_entry(form: EntryForm, category_kind: CategoryKind, category_name: str) -> ManualEntry:
    """Check a hand-added transaction and bring it to the shape of a bank one.

    The amount is typed without a sign and the category gives it: 1 500 in «Продукты»
    becomes −1 500, 85 000 in «Зарплата» becomes +85 000. An empty description is
    replaced with the category name, so the transaction list has no blank rows.
    """
    try:
        day = parse_date(form.date)
    except ValueError:
        raise EntryError("Укажите дату") from None
    try:
        amount = abs(parse_amount(form.amount))
    except ValueError:
        raise EntryError("Сумма должна быть числом, например 1 500 или 349,90") from None
    if not amount.is_finite() or amount == 0:
        raise EntryError("Сумма должна быть больше нуля")
    if amount > MAX_AMOUNT:
        raise EntryError("Слишком большая сумма")

    description = " ".join(form.description.split()) or category_name
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise EntryError(f"Описание не длиннее {MAX_DESCRIPTION_LENGTH} символов")

    return ManualEntry(
        date=day,
        amount=amount if category_kind == CategoryKind.INCOME else -amount,
        description=description,
        spender=clean_spender(form.spender),
    )


def clean_spender(spender: str) -> str | None:
    """«  муж » → «муж»; an empty field means the label is not set."""
    spender = " ".join(spender.split())
    if len(spender) > MAX_SPENDER_LENGTH:
        raise EntryError(f"Поле «Кто потратил» не длиннее {MAX_SPENDER_LENGTH} символов")
    return spender or None
