"""Synthetic labeled transactions of four made-up families, to run the evaluation end to end
before real data is collected. Not evidence for the hypothesis — only a check of the code.

Built to contain what makes the task hard on real data: personal categories that do not
exist at the bank («Развивашки», «Бюджет мужа»), mixed merchants (a pharmacy: health or
beauty) and new branches of known chains that appear only in the last month.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from research.dataset import LabeledTransaction

MONTHS = [date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]

# name, branches (a new one opens in the last month), bank category, amount range, per month
MERCHANTS = [
    ("ПЯТЕРОЧКА", ["ХИМКИ", "МОСКВА", "МЫТИЩИ"], "Супермаркеты", (300, 2500), 8),
    ("ПЕРЕКРЕСТОК", ["ТВЕРСКАЯ", "ЛЕНИНСКИЙ"], "Супермаркеты", (800, 4500), 4),
    ("Кофемания", [""], "Рестораны", (450, 1800), 3),
    ("Яндекс Go", [""], "Такси", (250, 1200), 5),
    ("Аптека Ригла", ["", "КРАСНОГОРСК"], "Аптеки", (300, 2500), 3),
    ("Студия развития Лучик", [""], "Образование", (4000, 4000), 1),
    ("WILDBERRIES", [""], "Маркетплейсы", (500, 7000), 4),
    ("Лукойл АЗС", ["12", "47"], "Топливо", (2500, 4000), 2),
    ("Золотое яблоко", [""], "Красота", (1200, 5000), 1),
    ("Детский мир", [""], "Детские товары", (900, 6000), 1),
]

# Each family files merchants its own way: category → weight.
FAMILIES: dict[str, dict[str, dict[str, int]]] = {
    "family-1": {
        "ПЯТЕРОЧКА": {"Продукты": 1},
        "ПЕРЕКРЕСТОК": {"Продукты": 1},
        "Кофемания": {"Кафе и рестораны": 1},
        "Яндекс Go": {"Транспорт": 1},
        "Аптека Ригла": {"Здоровье": 3, "Красота": 2},
        "Студия развития Лучик": {"Развивашки": 1},
        "WILDBERRIES": {"Одежда": 2, "Дети": 1, "Дом и ЖКХ": 1},
        "Лукойл АЗС": {"Транспорт": 1},
        "Золотое яблоко": {"Красота": 1},
        "Детский мир": {"Дети": 1},
    },
    "family-2": {
        "ПЯТЕРОЧКА": {"Еда": 1},
        "ПЕРЕКРЕСТОК": {"Еда": 1},
        "Кофемания": {"Бюджет мужа": 1},
        "Яндекс Go": {"Такси": 1},
        "Аптека Ригла": {"Аптека": 1},
        "Студия развития Лучик": {"Дети": 1},
        "WILDBERRIES": {"Маркетплейсы": 1},
        "Лукойл АЗС": {"Бюджет мужа": 1},
        "Золотое яблоко": {"Бьюти": 1},
        "Детский мир": {"Дети": 1},
    },
    "family-3": {
        "ПЯТЕРОЧКА": {"Продукты": 1},
        "ПЕРЕКРЕСТОК": {"Продукты": 3, "Праздники": 1},
        "Кофемания": {"Кафе и рестораны": 1},
        "Яндекс Go": {"Транспорт": 2, "Работа": 1},
        "Аптека Ригла": {"Здоровье": 1},
        "Студия развития Лучик": {"Кружки": 1},
        "WILDBERRIES": {"Одежда": 1, "Подарки": 1},
        "Лукойл АЗС": {"Машина": 1},
        "Золотое яблоко": {"Подарки": 1, "Красота": 1},
        "Детский мир": {"Подарки": 1},
    },
    "family-4": {
        "ПЯТЕРОЧКА": {"Продукты": 1},
        "ПЕРЕКРЕСТОК": {"Продукты": 1},
        "Кофемания": {"Кафе и рестораны": 1},
        "Яндекс Go": {"Транспорт": 1},
        "Аптека Ригла": {"Здоровье": 1},
        "Студия развития Лучик": {"Образование": 1},
        "WILDBERRIES": {"Одежда": 1},
        "Лукойл АЗС": {"Транспорт": 1},
        "Золотое яблоко": {"Красота": 1},
        "Детский мир": {"Дети": 1},
    },
}


def generate(seed: int = 7) -> list[LabeledTransaction]:
    """Four months of expenses for every family; the same seed gives the same data."""
    rng = random.Random(seed)
    rows = []
    for family, choices in FAMILIES.items():
        for month_index, month in enumerate(MONTHS):
            is_last = month_index == len(MONTHS) - 1
            for name, branches, bank_category, (low, high), per_month in MERCHANTS:
                # The last branch of a chain opens only in the last month.
                open_branches = branches if is_last or len(branches) == 1 else branches[:-1]
                for _ in range(per_month):
                    category = rng.choices(
                        list(choices[name]), weights=list(choices[name].values())
                    )[0]
                    branch = rng.choice(open_branches)
                    rows.append(
                        LabeledTransaction(
                            user=family,
                            date=month + timedelta(days=rng.randrange(28)),
                            amount=-Decimal(rng.randint(low, high)),
                            description=f"{name} {branch}".strip(),
                            bank_category=bank_category,
                            category=category,
                        )
                    )
    return sorted(rows, key=lambda row: (row.user, row.date))
