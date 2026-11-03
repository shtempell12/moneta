import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.main import app

EMAIL = "anna@mail.ru"
PASSWORD = "надёжный-пароль"


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client: TestClient) -> str:
    """Register Anna and return the page she lands on."""
    form = {"email": EMAIL, "password": PASSWORD, "pd_consent": "yes"}
    return client.post("/register", data=form).text


def csrf_token(page: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', page)
    assert match, "page has no CSRF token"
    return match.group(1)
