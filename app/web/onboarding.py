"""First-run questions right after registration."""

from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse

from app.domain.onboarding import CURRENT_TOOLS, SUGGESTED_CATEGORIES, OnboardingError, make_answers
from app.services import onboarding
from app.web.budget import today
from app.web.session import DbSession, RequiredUser, check_csrf
from app.web.templating import templates

router = APIRouter()


@router.get("/onboarding")
def onboarding_page(request: Request, current: RequiredUser) -> Response:
    return _page(request, current)


@router.post("/onboarding")
def complete(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    csrf_token: Annotated[str, Form()],
    goal_name: Annotated[str, Form()] = "",
    goal_target: Annotated[str, Form()] = "",
    goal_deadline: Annotated[str, Form()] = "",
    income: Annotated[str, Form()] = "",
    categories: Annotated[list[str] | None, Form()] = None,
    custom_category: Annotated[str, Form()] = "",
    current_tool: Annotated[str, Form()] = "",
) -> Response:
    check_csrf(current, csrf_token)
    form = {
        "goal_name": goal_name,
        "goal_target": goal_target,
        "goal_deadline": goal_deadline,
        "income": income,
        "categories": categories or [],
        "custom_category": custom_category,
        "current_tool": current_tool,
    }
    try:
        answers = make_answers(
            goal_name=goal_name,
            goal_target=goal_target,
            goal_deadline=goal_deadline,
            income=income,
            categories=categories or [],
            custom_category=custom_category,
            current_tool=current_tool,
            today=today(),
        )
    except OnboardingError as error:
        return _page(request, current, form=form, error=str(error))
    onboarding.complete(db, current.user, answers, today())
    return RedirectResponse("/import?welcome=1", status_code=303)


@router.post("/onboarding/skip")
def skip(db: DbSession, current: RequiredUser, csrf_token: Annotated[str, Form()]) -> Response:
    check_csrf(current, csrf_token)
    onboarding.skip(db, current.user)
    return RedirectResponse("/", status_code=303)


def _page(
    request: Request,
    current: RequiredUser,
    form: Mapping[str, object] | None = None,
    error: str | None = None,
) -> Response:
    return templates.TemplateResponse(
        request,
        "onboarding.html",
        {
            "current": current,
            "form": form or {"categories": []},
            "suggested": SUGGESTED_CATEGORIES,
            "tools": CURRENT_TOOLS,
            "error": error,
        },
        status_code=400 if error else 200,
    )
