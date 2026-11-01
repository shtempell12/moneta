from app.domain.categorization import (
    BankCategoryCategorizer,
    CascadeCategorizer,
    HistoryCategorizer,
    TransactionFeatures,
)
from app.domain.enums import CategorySource

GROCERIES, KIDS_CLUBS, CAFE = 1, 2, 3
USER_CATEGORIES = {"Продукты": GROCERIES, "Кафе и рестораны": CAFE}


def features(merchant: str, bank_category: str | None = None) -> TransactionFeatures:
    return TransactionFeatures(merchant_key=merchant, bank_category=bank_category)


def test_history_repeats_users_choice_for_the_same_merchant() -> None:
    categorizer = HistoryCategorizer({"детский мир": KIDS_CLUBS})

    prediction = categorizer.predict(features("детский мир", "Детские товары"))

    assert prediction is not None
    assert prediction.category_id == KIDS_CLUBS
    assert prediction.source == CategorySource.HISTORY


def test_history_has_no_opinion_about_new_merchants() -> None:
    assert HistoryCategorizer({}).predict(features("новый магазин")) is None


def test_bank_category_is_translated_to_users_category() -> None:
    prediction = BankCategoryCategorizer(USER_CATEGORIES).predict(
        features("пятерочка", " Супермаркеты ")
    )

    assert prediction is not None
    assert prediction.category_id == GROCERIES
    assert prediction.source == CategorySource.BANK


def test_bank_category_without_mapping_gives_nothing() -> None:
    categorizer = BankCategoryCategorizer(USER_CATEGORIES)

    assert categorizer.predict(features("wildberries", "Маркетплейсы")) is None
    assert categorizer.predict(features("перевод", None)) is None


def test_bank_category_mapped_to_a_category_the_user_deleted_gives_nothing() -> None:
    prediction = BankCategoryCategorizer({"Продукты": GROCERIES}).predict(
        features("кофейня", "Рестораны")
    )

    assert prediction is None


def test_cascade_prefers_users_history_over_bank_category() -> None:
    # The bank says "Супермаркеты", but this user files this shop under "Кафе".
    cascade = CascadeCategorizer(
        [HistoryCategorizer({"вкусвилл": CAFE}), BankCategoryCategorizer(USER_CATEGORIES)]
    )

    prediction = cascade.predict(features("вкусвилл", "Супермаркеты"))

    assert prediction is not None
    assert prediction.category_id == CAFE
    assert prediction.source == CategorySource.HISTORY


def test_cascade_falls_back_to_bank_category_and_then_to_nothing() -> None:
    cascade = CascadeCategorizer([HistoryCategorizer({}), BankCategoryCategorizer(USER_CATEGORIES)])

    assert cascade.predict(features("пятерочка", "Супермаркеты")) is not None
    assert cascade.predict(features("wildberries", "Маркетплейсы")) is None
