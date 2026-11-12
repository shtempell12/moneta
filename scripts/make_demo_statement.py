"""Generate a synthetic bank statement and a family budget table for demos: no real data.

The statement mimics a typical Russian bank CSV export (Windows-1251, «;», «-1 234,56»).
The budget table covers the first two months in the family's own categories, the way
people from the interviews keep it in Excel; purchases are written a day before the bank
posts them, and a few cash purchases are only in the table.
Usage: uv run python scripts/make_demo_statement.py [statement.csv]
"""

import random
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

HEADER = (
    "Дата операции;Дата платежа;Номер карты;Статус;Сумма операции;Валюта операции;"
    "Сумма платежа;Валюта платежа;Кэшбэк;Категория;MCC;Описание"
)

# (description, bank category, MCC, min amount, max amount, times per month).
# Some shops get a bank category that does not match how a family would file them,
# e.g. a kids' studio is «Образование», but the family calls it «Развивашки».
MERCHANTS = [
    ("ПЯТЕРОЧКА {n}", "Супермаркеты", "5411", 300, 2500, 8),
    ("ПЕРЕКРЕСТОК {n}", "Супермаркеты", "5411", 800, 4500, 4),
    ("ВКУСВИЛЛ", "Супермаркеты", "5411", 400, 3000, 4),
    ("Кофемания", "Рестораны", "5812", 450, 1800, 3),
    ("Вкусно и точка", "Фастфуд", "5814", 350, 900, 2),
    ("Яндекс Go", "Такси", "4121", 250, 1200, 5),
    ("Метро Москва", "Местный транспорт", "4111", 63, 63, 10),
    ("Аптека Ригла", "Аптеки", "5912", 300, 2500, 2),
    ("МТС", "Мобильная связь", "4814", 650, 650, 1),
    ("Мосэнергосбыт", "ЖКХ", "4900", 2100, 3200, 1),
    ("Детский мир", "Детские товары", "5641", 900, 6000, 1),
    ("Студия развития Лучик", "Образование", "8299", 4000, 4000, 1),
    ("Бассейн Дельфин", "Спорттовары", "7997", 3500, 3500, 1),
    ("Золотое яблоко", "Красота", "5977", 1200, 5000, 1),
    ("Салон Ноготок", "Красота", "7230", 2500, 2500, 1),
    ("WILDBERRIES", "Маркетплейсы", "5399", 500, 7000, 3),
    ("OZON", "Маркетплейсы", "5399", 500, 6000, 2),
    ("Кинопоиск", "Развлечения", "4899", 299, 299, 1),
    ("Лукойл АЗС {n}", "Топливо", "5541", 2500, 4000, 2),
]

INCOME = [("Зарплата ООО Ромашка", "Пополнения", 95000, 95000, 1)]
MONTHS = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]
TABLE_OUTPUT = Path("data/demo_budget_table.csv")
TABLE_MONTHS = MONTHS[:2]

# How the made-up family files each merchant in its own table (first word of the name).
FAMILY_CATEGORIES = {
    "ПЯТЕРОЧКА": "Повар и продукты",
    "ПЕРЕКРЕСТОК": "Повар и продукты",
    "ВКУСВИЛЛ": "Повар и продукты",
    "Кофемания": "Бюджет мужа",
    "Вкусно": "Кафе",
    "Яндекс": "Транспорт",
    "Метро": "Транспорт",
    "Лукойл": "Машина",
    "Аптека": "Здоровье",
    "МТС": "Связь и интернет",
    "Мосэнергосбыт": "Коммунальные расходы",
    "Детский": "Дети",
    "Студия": "Развивашки",
    "Бассейн": "Спорт",
    "Золотое": "Красота",
    "Салон": "Красота",
    "WILDBERRIES": "Бытовые расходы",
    "OZON": "Бытовые расходы",
    "Кинопоиск": "Развлечения",
    "Зарплата": "Зарплата",
}


def money(amount: Decimal) -> str:
    sign = "-" if amount < 0 else "+"
    whole, _, kopecks = f"{abs(amount):.2f}".partition(".")
    return f"{sign}{int(whole):,}".replace(",", " ") + f",{kopecks}"


def random_moment(rng: random.Random, month: date) -> datetime:
    days = (date(month.year + month.month // 12, month.month % 12 + 1, 1) - month).days
    day = month + timedelta(days=rng.randrange(days))
    return datetime.combine(day, time(rng.randrange(8, 23), rng.randrange(60), rng.randrange(60)))


def operations(rng: random.Random) -> list[tuple[datetime, Decimal, str, str, str]]:
    result = []
    for month in MONTHS:
        for description, category, mcc, low, high, times in MERCHANTS:
            for _ in range(times):
                amount = -Decimal(rng.randint(low, high)) - Decimal(rng.randint(0, 99)) / 100
                if low == high:
                    amount = -Decimal(low)
                name = description.format(n=rng.choice(["1234", "5521", "0087"]))
                result.append((random_moment(rng, month), amount, category, mcc, name))
        for description, category, low, _high, _times in INCOME:
            moment = datetime.combine(month + timedelta(days=4), time(10, 0))
            result.append((moment, Decimal(low), category, "", description))
    return sorted(result, reverse=True)


def budget_table(
    rng: random.Random, ops: list[tuple[datetime, Decimal, str, str, str]]
) -> list[str]:
    lines = ["Когда;Что;Бюджет;Сколько;Кто?"]
    rows = [
        (moment.date() - timedelta(days=rng.choice([0, 0, 1])), description, amount)
        for moment, amount, _, _, description in ops
        if moment.date().replace(day=1) in TABLE_MONTHS
    ]
    rows += [
        (month + timedelta(days=day), "Рынок, наличные", Decimal(-700))
        for month in TABLE_MONTHS
        for day in (6, 20)
    ]
    for day, description, amount in sorted(rows):
        category = FAMILY_CATEGORIES.get(description.split()[0], "Другое")
        who = rng.choice(["Жена", "Жена", "Муж", ""])
        whole, _, kopecks = f"{abs(amount):.2f}".partition(".")
        lines.append(f"{day:%d.%m.%Y};{description};{category};{whole},{kopecks};{who}")
    return lines


def main() -> None:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "data/demo_statement.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(2026)
    ops = operations(rng)
    lines = [HEADER]
    for moment, amount, category, mcc, description in ops:
        lines.append(
            ";".join(
                [
                    moment.strftime("%d.%m.%Y %H:%M:%S"),
                    moment.strftime("%d.%m.%Y"),
                    "*4417",
                    "OK",
                    money(amount),
                    "RUB",
                    money(amount),
                    "RUB",
                    "",
                    category,
                    mcc,
                    description,
                ]
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="cp1251")
    print(f"Saved {len(lines) - 1} operations to {output}")
    table = budget_table(rng, ops)
    TABLE_OUTPUT.write_text("\n".join(table) + "\n", encoding="utf-8")
    print(f"Saved {len(table) - 1} budget table rows to {TABLE_OUTPUT}")


if __name__ == "__main__":
    main()
