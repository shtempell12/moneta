"""The saving goals page."""

from typing import Annotated

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse

from app.domain.goals import GoalError
from app.services import goals
from app.web.budget import today
from app.web.session import DbSession, RequiredUser, check_csrf
from app.web.templating import templates

router = APIRouter()


@router.get("/goals")
def goals_page(request: Request, db: DbSession, current: RequiredUser) -> Response:
    return _goals_response(request, db, current)


@router.post("/goals")
def create_goal(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    name: Annotated[str, Form()],
    target: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
    deadline: Annotated[str, Form()] = "",
) -> Response:
    check_csrf(current, csrf_token)
    try:
        goals.create_goal(db, current.user.id, name, target, deadline, today())
    except GoalError as error:
        form = {"name": name, "target": target, "deadline": deadline}
        return _goals_response(request, db, current, error=str(error), form=form)
    return RedirectResponse("/goals", status_code=303)


@router.post("/goals/{goal_id}/save")
def change_saved(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    goal_id: int,
    amount: Annotated[str, Form()],
    action: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
) -> Response:
    """One form, two buttons: «Отложил» (action=in) and «Взял» (action=out)."""
    check_csrf(current, csrf_token)
    try:
        goals.change_saved(db, current.user.id, goal_id, amount, withdraw=action == "out")
    except GoalError as error:
        return _goals_response(request, db, current, error=str(error))
    return RedirectResponse("/goals", status_code=303)


@router.post("/goals/{goal_id}/delete")
def delete_goal(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    goal_id: int,
    csrf_token: Annotated[str, Form()],
) -> Response:
    check_csrf(current, csrf_token)
    try:
        goals.delete_goal(db, current.user.id, goal_id)
    except GoalError as error:
        return _goals_response(request, db, current, error=str(error))
    return RedirectResponse("/goals", status_code=303)


def _goals_response(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    error: str | None = None,
    form: dict[str, str] | None = None,
) -> Response:
    return templates.TemplateResponse(
        request,
        "goals.html",
        {
            "current": current,
            "goals": goals.goals_with_progress(db, current.user.id, today()),
            "error": error,
            "form": form or {"name": "", "target": "", "deadline": ""},
        },
        status_code=400 if error else 200,
    )
