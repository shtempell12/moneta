from fastapi.testclient import TestClient

from tests.web.conftest import csrf_token, register


def test_registration_leads_to_onboarding(client: TestClient) -> None:
    page = register(client)

    assert "Давайте познакомимся" in page


def test_answers_lead_to_import_and_show_the_guide(client: TestClient) -> None:
    token = csrf_token(register(client))

    page = client.post(
        "/onboarding",
        data={
            "csrf_token": token,
            "goal_name": "Отпуск",
            "goal_target": "120 000",
            "income": "100 000",
            "categories": ["Развивашки", "Питомец"],
            "current_tool": "excel",
        },
    ).text

    assert "Остался последний шаг" in page
    dashboard = client.get("/").text
    assert "50/30/20" in dashboard
    assert "6 месяцев" in dashboard  # 120 000 ₽ at 20 000 ₽ a month
    assert "Развивашки" in client.get("/categories").text


def test_wrong_income_keeps_the_answers(client: TestClient) -> None:
    token = csrf_token(register(client))

    response = client.post(
        "/onboarding", data={"csrf_token": token, "goal_name": "Отпуск", "income": "много"}
    )

    assert response.status_code == 400
    assert "числом" in response.text
    assert 'value="Отпуск"' in response.text


def test_onboarding_can_be_skipped(client: TestClient) -> None:
    token = csrf_token(register(client))

    page = client.post("/onboarding/skip", data={"csrf_token": token}).text

    assert "50/30/20" not in page
    assert "Давайте познакомимся" not in page
