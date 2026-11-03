"""The month plan page: how much the user wants to spend in each category."""

from datetime import date

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from app.domain.enums import CategoryKind
from app.domain.months import month_param, next_month, parse_month
from app.repositories import budget_lines, categories
from app.services import plan
from app.services.plan import PlanError
from app.web.budget import selected_month, today
from app.web.session import DbSession, RequiredUser, check_csrf
from app.web.templating import templates

router = APIRouter()

FIELD_PREFIX = "plan_"


@router.get("/plan")
def plan_page(
    request: Request, db: DbSession, current: RequiredUser, month: str | None = None
) -> Response:
    return _plan_response(request, db, current, month)


@router.post("/plan")
async def save_plan(request: Request, db: DbSession, current: RequiredUser) -> Response:
    form = await request.form()
    check_csrf(current, str(form.get("csrf_token", "")))
    month = parse_month(str(form.get("month", "")), today().replace(day=1))
    # One field per category: «plan_12» = «30 000».
    typed = {
        int(name.removeprefix(FIELD_PREFIX)): str(value)
        for name, value in form.items()
        if name.startswith(FIELD_PREFIX) and name.removeprefix(FIELD_PREFIX).isdigit()
    }
    try:
        plan.save_plan(db, current.user.id, month, typed)
    except PlanError as error:
        return _plan_response(request, db, current, month_param(month), error=str(error))
    return RedirectResponse(f"/?month={month_param(month)}", status_code=303)


@router.post("/plan/copy")
async def copy_plan(request: Request, db: DbSession, current: RequiredUser) -> Response:
    form = await request.form()
    check_csrf(current, str(form.get("csrf_token", "")))
    month = parse_month(str(form.get("month", "")), today().replace(day=1))
    try:
        plan.copy_previous_plan(db, current.user.id, month)
    except PlanError as error:
        return _plan_response(request, db, current, month_param(month), error=str(error))
    return RedirectResponse(f"/plan?month={month_param(month)}", status_code=303)


def _plan_response(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    month: str | None,
    error: str | None = None,
) -> Response:
    selected, months = selected_month(db, current.user.id, month)
    # The plan is usually made in advance, so next month is always offered too.
    upcoming = next_month(today().replace(day=1))
    if upcoming not in months:
        months = sorted([*months, upcoming], reverse=True)
    planned = plan.month_plan(db, current.user.id, selected)
    fact = plan.month_plan_fact(db, current.user.id, selected)
    return templates.TemplateResponse(
        request,
        "plan.html",
        {
            "current": current,
            "month": selected,
            "months": months,
            "categories": [
                category
                for category in categories.list_for_user(db, current.user.id)
                if category.kind == CategoryKind.EXPENSE
            ],
            "planned": planned,
            "spent": {row.name: row.spent for row in fact.rows},
            "can_copy": not planned and _has_earlier_plan(db, current.user.id, selected),
            "error": error,
        },
        status_code=400 if error else 200,
    )


def _has_earlier_plan(db: DbSession, user_id: int, month: date) -> bool:
    return budget_lines.latest_month_before(db, user_id, month) is not None
