"""Automatic categorization of transactions into the user's own categories.

All categorizers share one interface, so they can be combined in a cascade and compared
with each other in research/ on the same data.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

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
