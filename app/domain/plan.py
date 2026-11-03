"""Plan vs fact: how much the user planned to spend in each category and how much was spent."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class PlanFactRow:
    name: str
    planned: Decimal | None
    spent: Decimal

    @property
    def left(self) -> Decimal | None:
        """What can still be spent; negative means overspent. None if there is no plan."""
        return None if self.planned is None else self.planned - self.spent

    @property
    def overspent(self) -> Decimal:
        left = self.left
        return -left if left is not None and left < 0 else ZERO

    @property
    def used_percent(self) -> int:
        """How much of the plan is spent: 21 500 of 30 000 → 72. Can be above 100."""
        if not self.planned:
            return 0
        return int((self.spent * 100 / self.planned).quantize(Decimal("1"), ROUND_HALF_UP))


@dataclass(frozen=True)
class PlanFact:
    rows: list[PlanFactRow]
    planned: Decimal
    spent: Decimal

    @property
    def left(self) -> Decimal:
        return self.planned - self.spent

    @property
    def has_plan(self) -> bool:
        return self.planned > 0


def plan_vs_fact(plan: Mapping[str, Decimal], spent: Mapping[str, Decimal]) -> PlanFact:
    """Compare the month plan with spending, both given as «category name → rubles».

    Example: plan «Продукты» 30 000, spent 32 500 → left −2 500, overspent 2 500.
    Planned categories come first (largest plan first), then spending without a plan.
    The total spent includes spending without a plan: the family budget is one wallet.
    """
    planned_rows = [
        PlanFactRow(name=name, planned=amount, spent=spent.get(name, ZERO))
        for name, amount in sorted(plan.items(), key=lambda item: -item[1])
    ]
    unplanned_rows = [
        PlanFactRow(name=name, planned=None, spent=amount)
        for name, amount in sorted(spent.items(), key=lambda item: -item[1])
        if name not in plan
    ]
    return PlanFact(
        rows=planned_rows + unplanned_rows,
        planned=sum(plan.values(), ZERO),
        spent=sum(spent.values(), ZERO),
    )
