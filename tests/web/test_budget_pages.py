import base64
import re

from fastapi.testclient import TestClient

from tests.web.conftest import csrf_token, register

STATEMENT = "\n".join(
    [
        "Дата операции;Сумма платежа;Категория;Описание",
        "03.10.2026 10:00:00;-1 500,00;Супермаркеты;ПЯТЕРОЧКА 1",
        "10.10.2026 10:00:00;-1 500,00;Супермаркеты;ПЯТЕРОЧКА 2",
        "12.10.2026 10:00:00;-2 990,00;Маркетплейсы;WILDBERRIES",
        "15.10.2026 10:00:00;+85 000,00;Пополнения;ЗАРПЛАТА",
    ]
).encode("cp1251")


def preview(client: TestClient, token: str) -> str:
    return client.post(
        "/import/preview",
        data={"csrf_token": token},
        files={"file": ("october.csv", STATEMENT, "text/csv")},
    ).text


def confirm_import(client: TestClient, token: str) -> str:
    return client.post(
        "/import",
        data={
            "csrf_token": token,
            "file_name": "october.csv",
            "file_b64": base64.b64encode(STATEMENT).decode(),
            "date": "Дата операции",
            "amount": "Сумма платежа",
            "description": "Описание",
            "bank_category": "Категория",
        },
    ).text


def transaction_id(page: str, description: str) -> str:
    row = next(chunk for chunk in page.split("<tr") if description in chunk)
    match = re.search(r"/transactions/(\d+)/category", row)
    assert match, f"no category selector for {description}"
    return match.group(1)


def category_option_id(page: str, name: str) -> str:
    match = re.search(rf'<option value="(\d+)"\s*>{name}</option>', page)
    assert match, f"no option {name}"
    return match.group(1)


def test_pages_require_login(client: TestClient) -> None:
    for path in ("/", "/transactions", "/import", "/categories"):
        response = client.get(path, follow_redirects=False)
        assert response.headers["location"] == "/login", path


def test_preview_guesses_columns_and_shows_first_rows(client: TestClient) -> None:
    page = preview(client, csrf_token(register(client)))

    assert '<option value="Сумма платежа" selected>' in page
    assert "WILDBERRIES" in page


def test_unsupported_file_shows_error(client: TestClient) -> None:
    token = csrf_token(register(client))

    response = client.post(
        "/import/preview",
        data={"csrf_token": token},
        files={"file": ("statement.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 400
    assert "CSV и Excel" in response.text


def test_import_without_csrf_token_is_forbidden(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/import/preview",
        data={"csrf_token": "forged"},
        files={"file": ("october.csv", STATEMENT, "text/csv")},
    )

    assert response.status_code == 403


def test_import_shows_what_was_categorized(client: TestClient) -> None:
    result = confirm_import(client, csrf_token(register(client)))

    assert "Новых операций" in result
    assert 'href="/transactions?month=2026-10"' in result


def test_dashboard_shows_categories_and_auto_share(client: TestClient) -> None:
    confirm_import(client, csrf_token(register(client)))

    dashboard = client.get("/?month=2026-10").text

    assert "Продукты" in dashboard
    # Two «Пятёрочка» purchases were categorized by the bank category, Wildberries was not.
    assert "67%" in dashboard


def test_fixing_category_in_the_table(client: TestClient) -> None:
    token = csrf_token(register(client))
    confirm_import(client, token)
    page = client.get("/transactions?month=2026-10").text

    table = client.post(
        f"/transactions/{transaction_id(page, 'WILDBERRIES')}/category",
        data={
            "category_id": category_option_id(page, "Одежда"),
            "month": "2026-10",
            "csrf_token": token,
        },
    ).text

    assert "Запомнили" in table
    assert "вручную" in table


def test_adding_own_category(client: TestClient) -> None:
    token = csrf_token(register(client))

    page = client.post("/categories", data={"name": "Развивашки", "csrf_token": token}).text

    assert "Развивашки" in page
