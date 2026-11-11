from app.domain.pdf_statement import TEXT_COLUMNS, table_rows, text_rows

# Made-up operations in the layout of a text PDF statement (no real data).
TEXT_STATEMENT = """Выписка по счёту дебетовой карты
ДАТА ОПЕРАЦИИ (МСК) КАТЕГОРИЯ СУММА В ВАЛЮТЕ СЧЁТА ОСТАТОК СРЕДСТВ
Дата обработки и код авторизации Описание операции
03.10.2026 10:15 Супермаркеты 1 234,56 10 000,00
03.10.2026 123456 PYATEROCHKA 1234 MOSKVA. Операция по карте ****1111
05.10.2026 09:00 Перевод на карту +85 000,00 95 000,00
05.10.2026 654321 Зарплата. Операция по карте ****1111
06.10.2026 19:40 Рестораны и кафе 870,00 94 130,00
06.10.2026 111222 SHOKOLADNITSA KAFE
MOSKVA. Операция по карте
****1111"""


def test_text_statement_gives_one_row_per_operation_with_signed_amounts() -> None:
    rows = text_rows(TEXT_STATEMENT)

    assert rows[0] == TEXT_COLUMNS
    assert rows[1:] == [
        ["03.10.2026", "Супермаркеты", "PYATEROCHKA 1234 MOSKVA", "-1 234,56"],
        ["05.10.2026", "Перевод на карту", "Зарплата", "85 000,00"],
        ["06.10.2026", "Рестораны и кафе", "SHOKOLADNITSA KAFE MOSKVA", "-870,00"],
    ]


def test_text_without_operations_gives_nothing() -> None:
    assert text_rows("Справка о наличии счёта\nОстаток на 01.10.2026 10 000,00") == []


def test_tables_of_all_pages_are_joined_under_one_header() -> None:
    page_1 = [
        ["Дата операции", "Документ", "Назначение платежа", "Сумма операции", None],
        ["", "", "", "в валюте счёта", "в валюте операции"],
        ["03.10.2026 10:15:00", "123", "Оплата товаров\nи услуг", "- 450.00 ₽", "- 450.00 ₽"],
    ]
    page_2 = [["05.10.2026 09:00:00", "124", "Пополнение", "+ 5 000.00 ₽", "+ 5 000.00 ₽"]]

    rows = table_rows([page_1, page_2])

    assert rows[0] == [
        "Дата операции",
        "Документ",
        "Назначение платежа",
        "Сумма операции",
        "Колонка 5",
    ]
    assert [row[2] for row in rows[1:]] == ["Оплата товаров и услуг", "Пополнение"]
    assert rows[2][3] == "+ 5 000.00 ₽"


def test_table_without_header_gives_nothing() -> None:
    assert table_rows([[["01.10.2026", "100"]]]) == []
