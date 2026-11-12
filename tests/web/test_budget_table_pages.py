import base64

from fastapi.testclient import TestClient

from tests.web.conftest import csrf_token, register
from tests.web.test_budget_pages import confirm_import

# Made-up family budget table for the statement in test_budget_pages (no real data).
TABLE = "\n".join(
    [
        "Когда;Что;Бюджет;Сколько;Кто?",
        "03.10.2026;Пятерочка;Повар и продукты;1 500;Жена",
        "11.10.2026;ВБ;бытовые расходы;2 990;Муж",
        "20.10.2026;Рынок;Повар и продукты;700;",
    ]
).encode("utf-8")


def test_preview_recognizes_table_columns(client: TestClient) -> None:
    token = csrf_token(register(client))

    page = client.post(
        "/budget-table/preview",
        data={"csrf_token": token},
        files={"file": ("budget.csv", TABLE, "text/csv")},
    ).text

    assert '<option value="Бюджет" selected>' in page
    assert '<option value="Сколько" selected>' in page


def test_table_categorizes_statement_operations(client: TestClient) -> None:
    token = csrf_token(register(client))
    confirm_import(client, token)

    page = client.post(
        "/budget-table",
        data={
            "csrf_token": token,
            "file_name": "budget.csv",
            "file_b64": base64.b64encode(TABLE).decode(),
            "date": "Когда",
            "amount": "Сколько",
            "category": "Бюджет",
            "note": "Что",
            "spender": "Кто?",
        },
    ).text

    assert "Таблица загружена" in page
    transactions = client.get("/transactions?month=2026-10").text
    assert "бытовые расходы" in transactions
    assert "из таблицы" in transactions


def test_table_without_needed_columns_shows_error(client: TestClient) -> None:
    token = csrf_token(register(client))

    response = client.post(
        "/budget-table/preview",
        data={"csrf_token": token},
        files={"file": ("notes.csv", "Заметки\nкупить хлеб".encode(), "text/csv")},
    )

    assert response.status_code == 400
