from datetime import date

_MONTH_NAMES = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)  # fmt: skip


def parse_month(value: str | None, default: date) -> date:
    """«2026-10» → 1 October 2026; anything unparsable falls back to the default month."""
    try:
        year, month = (int(part) for part in (value or "").split("-"))
        return date(year, month, 1)
    except ValueError:
        return default.replace(day=1)


def next_month(month: date) -> date:
    return date(month.year + month.month // 12, month.month % 12 + 1, 1)


def month_title(month: date) -> str:
    """1 October 2026 → «Октябрь 2026»."""
    return f"{_MONTH_NAMES[month.month - 1]} {month.year}"


def month_param(month: date) -> str:
    """1 October 2026 → «2026-10», the format used in page URLs."""
    return f"{month.year}-{month.month:02d}"
