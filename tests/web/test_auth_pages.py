import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app
from app.web.session import SESSION_COOKIE

EMAIL = "anna@mail.ru"
PASSWORD = "надёжный-пароль"


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client: TestClient, consent: bool = True) -> str:
    form = {"email": EMAIL, "password": PASSWORD}
    if consent:
        form["pd_consent"] = "yes"
    return client.post("/register", data=form).text


def csrf_token(page: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', page)
    assert match, "page has no CSRF token"
    return match.group(1)


def test_home_redirects_guests_to_login(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_registration_shows_home_with_default_categories(client: TestClient) -> None:
    page = register(client)

    assert EMAIL in page
    assert "Продукты" in page


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

    assert "Ваши категории" in page


def test_logout_without_csrf_token_is_forbidden(client: TestClient) -> None:
    register(client)

    response = client.post("/logout", data={"csrf_token": "forged"})

    assert response.status_code == 403
    assert "Ваши категории" in client.get("/").text


def test_logout_with_csrf_token_ends_session(client: TestClient) -> None:
    page = register(client)

    client.post("/logout", data={"csrf_token": csrf_token(page)})

    response = client.get("/", follow_redirects=False)
    assert response.headers["location"] == "/login"


def test_logged_in_user_is_sent_from_login_page_to_home(client: TestClient) -> None:
    register(client)

    response = client.get("/login", follow_redirects=False)

    assert response.headers["location"] == "/"
