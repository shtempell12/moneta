"""H-ML1 evaluation: train on a user's earlier months, check on the last one.

Only expenses are checked, and transfers are left out by the hypothesis boundary (they are
counted separately). A transaction a categorizer has no opinion about counts as a miss:
for the user it is the same as a wrong category — it has to be fixed by hand.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from research.approaches import APPROACHES, category_ids, features
from research.dataset import LabeledTransaction


@dataclass(frozen=True)
class Split:
    train: list[LabeledTransaction]
    test: list[LabeledTransaction]
    # Expenses of the test month left out by the hypothesis boundary (transfers).
    transfers: int = 0


@dataclass(frozen=True)
class UserResult:
    user: str
    approach: str
    total: int
    correct: int
    answered: int
    mixed_total: int
    mixed_correct: int
    transfers: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def split_last_month(rows: Sequence[LabeledTransaction], history_days: int | None = None) -> Split:
    """Last calendar month of the user's data is the test; earlier rows are the training.

    `history_days` keeps only that much history before the test month (14, 30, 60…),
    to see how accuracy depends on how long the user has used the service.
    """
    test_month = max(row.date for row in rows).replace(day=1)
    since = test_month - timedelta(days=history_days) if history_days else date.min
    expenses = [row for row in rows if row.date >= test_month and row.amount < 0]
    return Split(
        train=[row for row in rows if since <= row.date < test_month],
        test=[row for row in expenses if not row.is_transfer],
        transfers=sum(row.is_transfer for row in expenses),
    )


def mixed_merchants(train: Sequence[LabeledTransaction]) -> set[str]:
    """Merchants the user filed under 2+ categories, like a pharmacy: health and beauty."""
    categories: dict[str, set[str]] = defaultdict(set)
    for row in train:
        categories[row.merchant].add(row.category)
    return {merchant for merchant, names in categories.items() if len(names) > 1}


def evaluate(
    rows: Sequence[LabeledTransaction], history_days: int | None = None
) -> list[UserResult]:
    """Every approach on every user; one result row per (user, approach)."""
    by_user: dict[str, list[LabeledTransaction]] = defaultdict(list)
    for row in rows:
        by_user[row.user].append(row)

    results = []
    for user, user_rows in sorted(by_user.items()):
        split = split_last_month(user_rows, history_days)
        ids = category_ids(user_rows)
        mixed = mixed_merchants(split.train)
        for name, build in APPROACHES.items():
            categorizer = build(split.train, ids)
            predictions = [categorizer.predict(features(row)) for row in split.test]
            hits = [
                prediction is not None and prediction.category_id == ids[row.category]
                for row, prediction in zip(split.test, predictions, strict=True)
            ]
            results.append(
                UserResult(
                    user=user,
                    approach=name,
                    total=len(split.test),
                    correct=sum(hits),
                    answered=sum(prediction is not None for prediction in predictions),
                    mixed_total=sum(row.merchant in mixed for row in split.test),
                    mixed_correct=sum(
                        hit
                        for row, hit in zip(split.test, hits, strict=True)
                        if row.merchant in mixed
                    ),
                    transfers=split.transfers,
                )
            )
    return results


@dataclass(frozen=True)
class Summary:
    approach: str
    accuracy: float
    users_at_70: float
    mixed_accuracy: float | None


def summarize(results: Sequence[UserResult]) -> list[Summary]:
    """Per approach: accuracy over all checked transactions, share of users with ≥ 70%
    (the hypothesis asks for 80% of users), accuracy on mixed merchants."""
    summaries = []
    for name in APPROACHES:
        rows = [result for result in results if result.approach == name]
        total = sum(row.total for row in rows)
        mixed_total = sum(row.mixed_total for row in rows)
        summaries.append(
            Summary(
                approach=name,
                accuracy=sum(row.correct for row in rows) / total if total else 0.0,
                users_at_70=sum(row.accuracy >= 0.7 for row in rows) / len(rows) if rows else 0.0,
                mixed_accuracy=(
                    sum(row.mixed_correct for row in rows) / mixed_total if mixed_total else None
                ),
            )
        )
    return summaries
