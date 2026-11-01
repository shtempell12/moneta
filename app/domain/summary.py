"""Month summary for the dashboard: spending by category and the auto-categorized share."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import CategorySource

UNCATEGORIZED = "Без категории"


@dataclass(frozen=True)
class SummaryEntry:
    category_name: str | None
    amount: Decimal
    source: CategorySource | None


@dataclass(frozen=True)
class CategoryTotal:
    name: str
    spent: Decimal
    percent: int


@dataclass(frozen=True)
class MonthSummary:
    spent: Decimal
    income: Decimal
    by_category: list[CategoryTotal]
    expenses_count: int
    auto_count: int
    manual_count: int
    uncategorized_count: int

    @property
    def auto_percent(self) -> int:
        """Share of expenses categorized without the user's help — the hypothesis metric."""
        return _percent(self.auto_count, self.expenses_count)

    @property
    def manual_percent(self) -> int:
        return _percent(self.manual_count, self.expenses_count)


def summarize_month(entries: Iterable[SummaryEntry]) -> MonthSummary:
    """Summarize a month of transactions; expenses are negative amounts, income positive.

    Example: −3 000 ₽ «Продукты» and −1 000 ₽ «Кафе» → «Продукты» 75%, «Кафе» 25%.
    """
    spent_by_category: dict[str, Decimal] = defaultdict(Decimal)
    income = Decimal("0.00")
    expenses_count = auto_count = manual_count = uncategorized_count = 0

    for entry in entries:
        if entry.amount >= 0:
            income += entry.amount
            continue
        expenses_count += 1
        spent_by_category[entry.category_name or UNCATEGORIZED] += -entry.amount
        if entry.source is None:
            uncategorized_count += 1
        elif entry.source == CategorySource.MANUAL:
            manual_count += 1
        else:
            auto_count += 1

    spent = sum(spent_by_category.values(), Decimal("0.00"))
    by_category = [
        CategoryTotal(name=name, spent=amount, percent=_percent(amount, spent))
        for name, amount in sorted(spent_by_category.items(), key=lambda item: -item[1])
    ]
    return MonthSummary(
        spent=spent,
        income=income,
        by_category=by_category,
        expenses_count=expenses_count,
        auto_count=auto_count,
        manual_count=manual_count,
        uncategorized_count=uncategorized_count,
    )


def _percent(part: Decimal | int, whole: Decimal | int) -> int:
    if not whole:
        return 0
    return int((Decimal(part) * 100 / Decimal(whole)).quantize(Decimal("1"), ROUND_HALF_UP))
