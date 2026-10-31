from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Event, User
from app.services import auth
from app.services.auth import AuthError

EMAIL = "anna@mail.ru"
PASSWORD = "надёжный-пароль"


def register_anna(session: Session) -> str:
    return auth.register(session, EMAIL, PASSWORD, pd_consent=True)


def event_types(session: Session) -> list[str]:
    return list(session.scalars(select(Event.type).order_by(Event.id)))


def test_registration_creates_user_with_default_categories(session: Session) -> None:
    register_anna(session)

    user = session.scalars(select(User)).one()
    categories = session.scalars(select(Category.name).where(Category.user_id == user.id)).all()
    assert user.email == EMAIL
    assert user.password_hash != PASSWORD
    assert user.pd_consent_at is not None
    assert "Продукты" in categories
    assert event_types(session) == ["user_registered"]


def test_registration_logs_the_user_in(session: Session) -> None:
    token = register_anna(session)

    found = auth.find_session(session, token)

    assert found is not None
    user, _ = found
    assert user.email == EMAIL


def test_registration_requires_consent(session: Session) -> None:
    with pytest.raises(AuthError, match="согласие"):
        auth.register(session, EMAIL, PASSWORD, pd_consent=False)


def test_registration_rejects_short_password(session: Session) -> None:
    with pytest.raises(AuthError, match="не короче 8"):
        auth.register(session, EMAIL, "1234", pd_consent=True)


def test_email_cannot_be_registered_twice_even_in_other_case(session: Session) -> None:
    register_anna(session)

    with pytest.raises(AuthError, match="уже зарегистрирован"):
        auth.register(session, "  ANNA@mail.ru", PASSWORD, pd_consent=True)


def test_login_with_correct_password(session: Session) -> None:
    register_anna(session)

    token = auth.login(session, "Anna@Mail.ru", PASSWORD)

    assert auth.find_session(session, token) is not None
    assert event_types(session)[-1] == "login_succeeded"


def test_wrong_password_and_unknown_email_give_the_same_message(session: Session) -> None:
    register_anna(session)

    with pytest.raises(AuthError) as wrong_password:
        auth.login(session, EMAIL, "не-тот-пароль")
    with pytest.raises(AuthError) as unknown_email:
        auth.login(session, "olga@mail.ru", PASSWORD)

    assert str(wrong_password.value) == str(unknown_email.value) == "Неверный email или пароль"


def test_failed_login_does_not_store_the_email(session: Session) -> None:
    with pytest.raises(AuthError):
        auth.login(session, "olga@mail.ru", PASSWORD)

    event = session.scalars(select(Event)).one()
    assert "olga@mail.ru" not in str(event.payload)


def test_login_is_blocked_after_five_failures_even_with_correct_password(
    session: Session,
) -> None:
    register_anna(session)
    for _ in range(auth.MAX_FAILED_LOGINS):
        with pytest.raises(AuthError, match="Неверный"):
            auth.login(session, EMAIL, "не-тот-пароль")

    with pytest.raises(AuthError, match="Слишком много попыток"):
        auth.login(session, EMAIL, PASSWORD)


def test_logout_ends_the_session(session: Session) -> None:
    token = register_anna(session)

    auth.logout(session, token)

    assert auth.find_session(session, token) is None
    assert event_types(session)[-1] == "logout"


def test_session_expires_after_thirty_days(session: Session) -> None:
    token = register_anna(session)
    later = datetime.now(UTC) + auth.SESSION_LIFETIME + timedelta(minutes=1)

    assert auth.find_session(session, token, now=later) is None


def test_unknown_token_has_no_session(session: Session) -> None:
    assert auth.find_session(session, "made-up-token") is None
