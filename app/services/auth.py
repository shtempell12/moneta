from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_token, new_token, verify_password
from app.db.models import Category, User, UserSession
from app.domain.accounts import DEFAULT_CATEGORIES, email_problem, normalize_email, password_problem
from app.repositories import events, user_sessions, users

SESSION_LIFETIME = timedelta(days=30)
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW = timedelta(minutes=15)


class AuthError(Exception):
    """Authentication failure with a message that is safe to show to the user."""


def register(
    session: Session, email: str, password: str, pd_consent: bool, now: datetime | None = None
) -> str:
    """Create a user with the default categories and log them in. Returns the session token."""
    now = now or datetime.now(UTC)
    email = normalize_email(email)
    if not pd_consent:
        raise AuthError("Нужно согласие на обработку персональных данных")
    problem = email_problem(email) or password_problem(password)
    if problem:
        raise AuthError(problem)
    if users.get_by_email(session, email):
        raise AuthError("Пользователь с таким email уже зарегистрирован")

    user = User(email=email, password_hash=hash_password(password), pd_consent_at=now)
    session.add(user)
    session.flush()
    session.add_all(
        Category(user_id=user.id, name=name, kind=kind)
        for kind, names in DEFAULT_CATEGORIES.items()
        for name in names
    )
    events.add(session, "user_registered", user.id)
    token = _start_session(session, user, now)
    session.commit()
    return token


def login(session: Session, email: str, password: str, now: datetime | None = None) -> str:
    """Check the password and start a session. Returns the session token."""
    now = now or datetime.now(UTC)
    email = normalize_email(email)
    # Store a hash, not the email itself: failed attempts may belong to no user (152-FZ).
    email_key = hash_token(email)
    recent_failures = events.count_since(
        session, "login_failed", now - FAILED_LOGIN_WINDOW, "email_hash", email_key
    )
    if recent_failures >= MAX_FAILED_LOGINS:
        raise AuthError("Слишком много попыток входа. Попробуйте через 15 минут")

    user = users.get_by_email(session, email)
    if user is None or not verify_password(user.password_hash, password):
        events.add(session, "login_failed", user.id if user else None, {"email_hash": email_key})
        session.commit()
        # One message for both cases, so the form does not reveal which emails are registered.
        raise AuthError("Неверный email или пароль")

    events.add(session, "login_succeeded", user.id)
    token = _start_session(session, user, now)
    session.commit()
    return token


def delete_account(
    session: Session, user: User, password: str, now: datetime | None = None
) -> None:
    """Delete the user and all their data (152-FZ). The password is asked again,
    so a forgotten open browser is not enough to wipe someone's budget."""
    now = now or datetime.now(UTC)
    email_key = hash_token(user.email)
    recent_failures = events.count_since(
        session, "login_failed", now - FAILED_LOGIN_WINDOW, "email_hash", email_key
    )
    if recent_failures >= MAX_FAILED_LOGINS:
        raise AuthError("Слишком много попыток. Попробуйте через 15 минут")
    if not verify_password(user.password_hash, password):
        events.add(session, "login_failed", user.id, {"email_hash": email_key})
        session.commit()
        raise AuthError("Неверный пароль")

    # Everything else (sessions, categories, transactions, plans, goals, own events)
    # goes with the user through ON DELETE CASCADE.
    events.delete_with_payload(session, "email_hash", email_key)
    session.delete(user)
    # Kept without a user or any detail: only the count of deletions, for retention metrics.
    events.add(session, "account_deleted", None)
    session.commit()


def logout(session: Session, token: str) -> None:
    user_id = user_sessions.delete_by_token_hash(session, hash_token(token))
    if user_id is not None:
        events.add(session, "logout", user_id)
    session.commit()


def find_session(
    session: Session, token: str, now: datetime | None = None
) -> tuple[User, UserSession] | None:
    """Return the logged-in user and their session for a cookie token, if it is still valid."""
    user_session = user_sessions.get_active(session, hash_token(token), now or datetime.now(UTC))
    if user_session is None:
        return None
    return user_sessions.get_user(session, user_session), user_session


def _start_session(session: Session, user: User, now: datetime) -> str:
    token = new_token()
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            csrf_token=new_token(),
            expires_at=now + SESSION_LIFETIME,
        )
    )
    return token
