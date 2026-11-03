from decimal import Decimal
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.domain.enums import CategorySource
from app.domain.months import month_param, month_title

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

SOURCE_LABELS = {
    CategorySource.BANK: "по банку",
    CategorySource.HISTORY: "по истории",
    CategorySource.MANUAL: "вручную",
}


def format_rub(amount: Decimal, signed: bool = False) -> str:
    """Decimal("-1234.5") → «−1 234,50 ₽» (narrow no-break spaces, as in Russian typography)."""
    sign = "−" if amount < 0 else ("+" if signed and amount > 0 else "")
    whole, _, kopecks = f"{abs(amount):.2f}".partition(".")
    groups = f"{int(whole):,}".replace(",", " ")
    return f"{sign}{groups},{kopecks} ₽"


def format_plan_amount(amount: Decimal) -> str:
    """Decimal("30000.00") → «30 000» for an input field; kopecks only when there are any."""
    whole, _, kopecks = f"{amount:.2f}".partition(".")
    groups = f"{int(whole):,}".replace(",", " ")
    return groups if kopecks == "00" else f"{groups},{kopecks}"


def plural(count: int, one: str, few: str, many: str) -> str:
    """Russian plural form: 1 операция, 2 операции, 5 операций, 21 операция, 11 операций."""
    if count % 10 == 1 and count % 100 != 11:
        return one
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


templates.env.filters["rub"] = format_rub
templates.env.filters["plural"] = plural
templates.env.filters["plan_amount"] = format_plan_amount
templates.env.filters["month_title"] = month_title
templates.env.filters["month_param"] = month_param
templates.env.globals["source_labels"] = SOURCE_LABELS
