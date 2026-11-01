from fastapi.testclient import TestClient

from app.web.session import SESSION_COOKIE
from tests.web.conftest import EMAIL, PASSWORD, csrf_token, register


def test_home_redirects_guests_to_login(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_registration_leads_to_dashboard(client: TestClient) -> None:
    page = register(client)

    assert EMAIL in page
    assert "Загрузить выписку" in page


def test_session_cookie_is_http_only(client: TestClient) -> None:
    response = client.post(
        "/register",
        data={"email": EMAIL, "password": PASSWORD, "pd_consent": "yes"},
        follow_redirects=False,
    )

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_registration_without_consent_shows_error(client: TestClient) -> None:
    response = client.post("/register", data={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 400
    assert "согласие" in response.text


def test_wrong_password_shows_error_and_keeps_email(client: TestClient) -> None:
    register(client)
    client.cookies.clear()

    response = client.post("/login", data={"email": EMAIL, "password": "не-тот-пароль"})

    assert response.status_code == 400
    assert "Неверный email или пароль" in response.text
    assert f'value="{EMAIL}"' in response.text


def test_login_after_registration(client: TestClient) -> None:
    register(client)
    client.cookies.clear()

    page = client.post("/login", data={"email": EMAIL, "password": PASSWORD}).text

    assert "Выйти" in page


def test_logout_without_csrf_token_is_forbidden(client: TestClient) -> None:
    register(client)

    response = client.post("/logout", data={"csrf_token": "forged"})

    assert response.status_code == 403
    assert "Выйти" in client.get("/").text


def test_logout_with_csrf_token_ends_session(client: TestClient) -> None:
    page = register(client)

    client.post("/logout", data={"csrf_token": csrf_token(page)})

    response = client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/login"


def test_logged_in_user_is_sent_from_login_page_to_home(client: TestClient) -> None:
    register(client)

    response = client.get("/login", follow_redirects=False)

    assert response.headers["location"] == "/"
