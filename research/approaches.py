"""The categorization approaches compared in H-ML1, each built from one user's training data."""

from collections import defaultdict
from collections.abc import Callable, Sequence

from app.domain.accounts import DEFAULT_CATEGORIES
from app.domain.categorization import (
    BankCategoryCategorizer,
    CascadeCategorizer,
    Categorizer,
    ClassifierCategorizer,
    HistoryCategorizer,
    TransactionFeatures,
    merchant_category,
)
from research.dataset import LabeledTransaction

# Category names become ids, as in the service; ids are local to one evaluation run.
CategoryIds = dict[str, int]
Builder = Callable[[Sequence[LabeledTransaction], CategoryIds], Categorizer]


def features(row: LabeledTransaction) -> TransactionFeatures:
    return TransactionFeatures(merchant_key=row.merchant, bank_category=row.bank_category)


def bank(train: Sequence[LabeledTransaction], ids: CategoryIds) -> Categorizer:
    """Baseline: the bank category translated to the user's category of the same name."""
    return BankCategoryCategorizer(ids)


def last_choice(train: Sequence[LabeledTransaction], ids: CategoryIds) -> Categorizer:
    """The merchant gets the category of its latest transaction («последний клик»)."""
    rules = {row.merchant: ids[row.category] for row in sorted(train, key=lambda r: r.date)}
    return HistoryCategorizer(rules)


def most_frequent(train: Sequence[LabeledTransaction], ids: CategoryIds) -> Categorizer:
    """The merchant gets the category chosen most often (what the service does now)."""
    return HistoryCategorizer(_most_frequent_rules(train, ids))


def classifier(train: Sequence[LabeledTransaction], ids: CategoryIds) -> Categorizer:
    return ClassifierCategorizer([(features(row), ids[row.category]) for row in train])


def cascade(train: Sequence[LabeledTransaction], ids: CategoryIds) -> Categorizer:
    """Known merchant → its most frequent category; otherwise the classifier; otherwise bank."""
    return CascadeCategorizer(
        [
            HistoryCategorizer(_most_frequent_rules(train, ids)),
            ClassifierCategorizer([(features(row), ids[row.category]) for row in train]),
            BankCategoryCategorizer(ids),
        ]
    )


APPROACHES: dict[str, Builder] = {
    "bank": bank,
    "last_choice": last_choice,
    "most_frequent": most_frequent,
    "classifier": classifier,
    "cascade": cascade,
}


def category_ids(rows: Sequence[LabeledTransaction]) -> CategoryIds:
    """Ids for the user's categories plus the default ones the bank baseline can map to."""
    names = {row.category for row in rows}
    names.update(name for group in DEFAULT_CATEGORIES.values() for name in group)
    return {name: number for number, name in enumerate(sorted(names), start=1)}


def _most_frequent_rules(train: Sequence[LabeledTransaction], ids: CategoryIds) -> dict[str, int]:
    choices: dict[str, list[int]] = defaultdict(list)
    for row in sorted(train, key=lambda r: r.date):
        choices[row.merchant].append(ids[row.category])
    return {merchant: merchant_category(ids_, ids_[-1]) for merchant, ids_ in choices.items()}
