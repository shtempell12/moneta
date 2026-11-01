from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import tokens_match
from app.db.models import User
from app.db.session import get_session
from app.services import auth

SESSION_COOKIE = "moneta_session"

DbSession = Annotated[Session, Depends(get_session)]


@dataclass(frozen=True)
class CurrentUser:
    user: User
    csrf_token: str


def get_current_user(request: Request, db: DbSession) -> CurrentUser | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    found = auth.find_session(db, token)
    if found is None:
        return None
    user, user_session = found
    return CurrentUser(user=user, csrf_token=user_session.csrf_token)


OptionalUser = Annotated[CurrentUser | None, Depends(get_current_user)]


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(auth.SESSION_LIFETIME.total_seconds()),
        # httponly: page scripts cannot read the cookie; samesite=lax: other sites cannot
        # submit our forms with it; secure: sent only over HTTPS (local dev runs on plain HTTP).
        httponly=True,
        samesite="lax",
        secure=get_settings().app_env != "dev",
    )


def require_user(current: OptionalUser) -> CurrentUser:
    """Dependency for pages that need a logged-in user: guests are sent to the login page."""
    if current is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return current


RequiredUser = Annotated[CurrentUser, Depends(require_user)]


def check_csrf(current: CurrentUser, received_token: str) -> None:
    if not tokens_match(current.csrf_token, received_token):
        raise HTTPException(status_code=403, detail="CSRF check failed")
