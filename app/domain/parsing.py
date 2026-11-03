import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Bank exports use regular, non-breaking and narrow spaces as thousands separators,
# and sometimes the typographic minus sign instead of "-".
_SPACES = re.compile(r"[\s  ]")
_CURRENCY = re.compile(r"(₽|руб\.?|rub|р\.)", re.IGNORECASE)
_DATE_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y")


def parse_amount(value: object) -> Decimal:
    """Parse a money amount as written in Russian bank statements.

    «-1 234,56 ₽» → Decimal("-1234.56"); «+500» → Decimal("500.00").
    Raises ValueError if the value is not a number.
    """
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    if isinstance(value, int):
        return Decimal(value).quantize(Decimal("0.01"))
    if isinstance(value, float):
        # Excel cells come as float; going through str avoids binary float artefacts.
        return Decimal(str(value)).quantize(Decimal("0.01"))

    text = _CURRENCY.sub("", str(value))
    text = _SPACES.sub("", text).replace("−", "-").replace(",", ".")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Не удалось разобрать сумму: {value!r}") from None


def parse_date(value: object) -> date:
    """Parse an operation date: «31.10.2026», «31.10.2026 14:22:05», «2026-10-31» or a datetime.

    Raises ValueError if the value is not a date.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    date_part = text.split()[0] if text else text
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(date_part, date_format).date()
        except ValueError:
            continue
    raise ValueError(f"Не удалось разобрать дату: {value!r}")


def merchant_key(description: str) -> str:
    """Normalize an operation description so that the same shop always gets the same key.

    «ПЯТЕРОЧКА 1234 Москва» and «Пятерочка 5678 МОСКВА» → «пятерочка москва»:
    store numbers, card masks and punctuation differ between operations of one shop.
    """
    text = description.lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я ]+", " ", text)
    return " ".join(text.split())
