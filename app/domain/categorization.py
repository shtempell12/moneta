"""Automatic categorization of transactions into the user's own categories.

All categorizers share one interface, so they can be combined in a cascade and compared
with each other in research/ on the same data.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline

from app.domain.enums import CategorySource

# Bank categories (lowercase) → names of the default Moneta categories.
# This is the "bank category brought to the user's categories" baseline from the hypothesis.
BANK_CATEGORY_TO_DEFAULT: dict[str, str] = {
    "супермаркеты": "Продукты",
    "продукты": "Продукты",
    "рестораны": "Кафе и рестораны",
    "фастфуд": "Кафе и рестораны",
    "кафе": "Кафе и рестораны",
    "транспорт": "Транспорт",
    "такси": "Транспорт",
    "топливо": "Транспорт",
    "азс": "Транспорт",
    "местный транспорт": "Транспорт",
    "жкх": "Дом и ЖКХ",
    "коммунальные услуги": "Дом и ЖКХ",
    "дом и ремонт": "Дом и ЖКХ",
    "мобильная связь": "Связь и интернет",
    "связь": "Связь и интернет",
    "интернет": "Связь и интернет",
    "аптеки": "Здоровье",
    "медицина": "Здоровье",
    "красота": "Красота",
    "детские товары": "Дети",
    "одежда и обувь": "Одежда",
    "одежда": "Одежда",
    "развлечения": "Развлечения",
    "кино": "Развлечения",
    "цветы": "Подарки",
}


@dataclass(frozen=True)
class TransactionFeatures:
    """What a categorizer may look at: the same fields a bank statement provides."""

    merchant_key: str
    bank_category: str | None


@dataclass(frozen=True)
class Prediction:
    category_id: int
    source: CategorySource
    confidence: float


class Categorizer(Protocol):
    def predict(self, transaction: TransactionFeatures) -> Prediction | None:
        """Return the predicted category, or None if this categorizer has no opinion."""
        ...


class HistoryCategorizer:
    """Repeats the user's own earlier choice for the same merchant."""

    def __init__(self, rules: Mapping[str, int]) -> None:
        self._rules = rules

    def predict(self, transaction: TransactionFeatures) -> Prediction | None:
        category_id = self._rules.get(transaction.merchant_key)
        if category_id is None:
            return None
        return Prediction(category_id, CategorySource.HISTORY, confidence=1.0)


class BankCategoryCategorizer:
    """Translates the bank's category into one of the user's categories (the baseline)."""

    def __init__(self, user_category_ids: Mapping[str, int]) -> None:
        self._user_category_ids = user_category_ids

    def predict(self, transaction: TransactionFeatures) -> Prediction | None:
        if not transaction.bank_category:
            return None
        default_name = BANK_CATEGORY_TO_DEFAULT.get(transaction.bank_category.strip().lower())
        category_id = self._user_category_ids.get(default_name) if default_name else None
        if category_id is None:
            return None
        # Bank categories are generic, so they are trusted less than the user's own history.
        return Prediction(category_id, CategorySource.BANK, confidence=0.5)


class ClassifierCategorizer:
    """Learns from the user's own categorized transactions which words point to which category.

    Unlike HistoryCategorizer it also handles merchants the user has never categorized:
    «пятерочка москва 12» is close to «пятерочка химки» by its letter sequences
    (character n-grams), so it lands in the same category.
    """

    def __init__(self, examples: Sequence[tuple[TransactionFeatures, int]]) -> None:
        self._model: Pipeline | None = None
        self._only_category: int | None = None
        categories = {category_id for _, category_id in examples}
        if len(categories) == 1:
            # A classifier needs at least two classes; with one there is nothing to choose.
            self._only_category = categories.pop()
        elif categories:
            self._model = make_pipeline(
                TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)),
                LogisticRegression(max_iter=1000),
            )
            self._model.fit(
                [_text(features) for features, _ in examples],
                [category_id for _, category_id in examples],
            )

    def predict(self, transaction: TransactionFeatures) -> Prediction | None:
        if self._only_category is not None:
            return Prediction(self._only_category, CategorySource.HISTORY, confidence=1.0)
        if self._model is None:
            return None
        probabilities = self._model.predict_proba([_text(transaction)])[0]
        best = int(probabilities.argmax())
        return Prediction(
            int(self._model.classes_[best]),
            CategorySource.HISTORY,
            confidence=float(probabilities[best]),
        )


def _text(transaction: TransactionFeatures) -> str:
    return f"{transaction.merchant_key} {transaction.bank_category or ''}".strip().lower()


class CascadeCategorizer:
    """Asks categorizers in order and returns the first answer."""

    def __init__(self, categorizers: Sequence[Categorizer]) -> None:
        self._categorizers = categorizers

    def predict(self, transaction: TransactionFeatures) -> Prediction | None:
        for categorizer in self._categorizers:
            prediction = categorizer.predict(transaction)
            if prediction is not None:
                return prediction
        return None


def merchant_category(manual_choices: Sequence[int], latest_choice: int) -> int:
    """The category for a merchant's other and future transactions.

    It is the category the user chose by hand most often for this merchant, so one unusual
    purchase does not move the whole merchant: a pharmacy fixed 4 times to «Здоровье» and
    once to «Красота» stays in «Здоровье». On a tie the latest choice wins, so a fresh
    correction is never ignored.
    """
    counts = Counter(manual_choices)
    top = max(counts.values(), default=0)
    if counts[latest_choice] >= top:
        return latest_choice
    return counts.most_common(1)[0][0]
