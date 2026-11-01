from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.core.security import tokens_match
from app.services import auth
from app.services.auth import AuthError
from app.web.session import SESSION_COOKIE, DbSession, OptionalUser, set_session_cookie
from app.web.templating import templates

router = APIRouter()


def _redirect(url: str) -> RedirectResponse:
    # 303 makes the browser follow up with GET, so refreshing the page does not resend the form.
    return RedirectResponse(url, status_code=303)


@router.get("/register")
def register_page(request: Request, current: OptionalUser) -> Response:
    if current is not None:
        return _redirect("/")
    return templates.TemplateResponse(request, "register.html")


@router.post("/register")
def register(
    request: Request,
    db: DbSession,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    pd_consent: Annotated[bool, Form()] = False,
) -> Response:
    try:
        token = auth.register(db, email, password, pd_consent)
    except AuthError as error:
        return templates.TemplateResponse(
            request, "register.html", {"error": str(error), "email": email}, status_code=400
        )
    response = _redirect("/")
    set_session_cookie(response, token)
    return response


@router.get("/login")
def login_page(request: Request, current: OptionalUser) -> Response:
    if current is not None:
        return _redirect("/")
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
def login(
    request: Request,
    db: DbSession,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    try:
        token = auth.login(db, email, password)
    except AuthError as error:
        return templates.TemplateResponse(
            request, "login.html", {"error": str(error), "email": email}, status_code=400
        )
    response = _redirect("/")
    set_session_cookie(response, token)
    return response


@router.post("/logout")
def logout(
    request: Request, db: DbSession, current: OptionalUser, csrf_token: Annotated[str, Form()]
) -> Response:
    if current is None or not tokens_match(current.csrf_token, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF check failed")
    auth.logout(db, request.cookies[SESSION_COOKIE])
    response = _redirect("/login")
    response.delete_cookie(SESSION_COOKIE)
    return response
