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


templates.env.filters["rub"] = format_rub
templates.env.filters["month_title"] = month_title
templates.env.filters["month_param"] = month_param
templates.env.globals["source_labels"] = SOURCE_LABELS
