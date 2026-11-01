"""Generate a synthetic bank statement for demos: no real person's data.

The layout mimics a typical Russian bank CSV export (Windows-1251, «;», «-1 234,56»).
Usage: uv run python scripts/make_demo_statement.py [output.csv]
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


def main() -> None:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "data/demo_statement.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [HEADER]
    for moment, amount, category, mcc, description in operations(random.Random(2026)):
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


if __name__ == "__main__":
    main()
