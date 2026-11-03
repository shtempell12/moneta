import base64
import binascii
from datetime import UTC, date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import RedirectResponse

from app.domain.months import month_param, parse_month
from app.domain.statement import (
    ColumnMapping,
    StatementFormatError,
    guess_columns,
    parse_rows,
    read_table,
)
from app.repositories import categories
from app.repositories import transactions as transactions_repo
from app.services import categories as categories_service
from app.services import imports, plan, transactions
from app.services.categories import CategoryError
from app.services.transactions import NotFoundError
from app.web.session import DbSession, RequiredUser, check_csrf
from app.web.templating import templates

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
PREVIEW_ROWS = 5
# The confirm form carries the file back as base64, which is larger than Starlette's
# default 1 MB limit for a form field.
MAX_FORM_FIELD_BYTES = 8 * 1024 * 1024
MOSCOW = ZoneInfo("Europe/Moscow")


def today() -> date:
    return datetime.now(UTC).astimezone(MOSCOW).date()


def _current_month() -> date:
    return today().replace(day=1)


def selected_month(db: DbSession, user_id: int, value: str | None) -> tuple[date, list[date]]:
    """The month from the URL, or the latest month with data, plus all months for the switcher."""
    months = transactions_repo.months_with_data(db, user_id)
    default = months[0] if months else _current_month()
    month = parse_month(value, default) if value else default
    if month not in months:
        months = sorted([*months, month], reverse=True)
    return month, months


@router.get("/")
def dashboard(
    request: Request, db: DbSession, current: RequiredUser, month: str | None = None
) -> Response:
    selected, months = selected_month(db, current.user.id, month)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "current": current,
            "month": selected,
            "months": months,
            "summary": transactions.month_summary(db, current.user.id, selected),
            "plan": plan.month_plan_fact(db, current.user.id, selected),
        },
    )


@router.get("/transactions")
def transactions_page(
    request: Request, db: DbSession, current: RequiredUser, month: str | None = None
) -> Response:
    selected, months = selected_month(db, current.user.id, month)
    return templates.TemplateResponse(
        request,
        "transactions.html",
        {
            "current": current,
            "month": selected,
            "months": months,
            "rows": transactions.month_transactions(db, current.user.id, selected),
            "categories": categories.list_for_user(db, current.user.id),
        },
    )


@router.post("/transactions/{transaction_id}/category")
def change_category(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    transaction_id: int,
    category_id: Annotated[int, Form()],
    month: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
) -> Response:
    """HTMX endpoint: returns the re-rendered table, since other rows of the merchant change too."""
    check_csrf(current, csrf_token)
    try:
        also_changed = transactions.change_category(
            db, current.user.id, transaction_id, category_id
        )
    except NotFoundError:
        raise HTTPException(status_code=404) from None
    selected = parse_month(month, _current_month())
    return templates.TemplateResponse(
        request,
        "_transactions_table.html",
        {
            "current": current,
            "month": selected,
            "rows": transactions.month_transactions(db, current.user.id, selected),
            "categories": categories.list_for_user(db, current.user.id),
            "changed_id": transaction_id,
            "also_changed": also_changed,
        },
    )


@router.get("/categories")
def categories_page(request: Request, db: DbSession, current: RequiredUser) -> Response:
    return _categories_response(request, db, current)


@router.post("/categories")
def add_category(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    name: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
) -> Response:
    check_csrf(current, csrf_token)
    try:
        categories_service.add_category(db, current.user.id, name)
    except CategoryError as error:
        return _categories_response(request, db, current, error=str(error), status_code=400)
    return RedirectResponse("/categories", status_code=303)


@router.post("/categories/{category_id}/rename")
def rename_category(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    category_id: int,
    name: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
) -> Response:
    check_csrf(current, csrf_token)
    try:
        categories_service.rename_category(db, current.user.id, category_id, name)
    except CategoryError as error:
        return _categories_response(request, db, current, error=str(error), status_code=400)
    return RedirectResponse("/categories", status_code=303)


@router.post("/categories/{category_id}/delete")
def delete_category(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    category_id: int,
    csrf_token: Annotated[str, Form()],
) -> Response:
    check_csrf(current, csrf_token)
    try:
        categories_service.delete_category(db, current.user.id, category_id)
    except CategoryError as error:
        return _categories_response(request, db, current, error=str(error), status_code=400)
    return RedirectResponse("/categories", status_code=303)


def _categories_response(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    error: str | None = None,
    status_code: int = 200,
) -> Response:
    return templates.TemplateResponse(
        request,
        "categories.html",
        {
            "current": current,
            "categories": categories.list_for_user(db, current.user.id),
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/import")
def import_page(request: Request, current: RequiredUser) -> Response:
    return templates.TemplateResponse(request, "import_upload.html", {"current": current})


@router.post("/import/preview")
async def import_preview(
    request: Request,
    current: RequiredUser,
    file: UploadFile,
    csrf_token: Annotated[str, Form()],
) -> Response:
    """Step 1: show the first rows and our guess of which column is which."""
    check_csrf(current, csrf_token)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    file_name = file.filename or "statement"
    try:
        if len(content) > MAX_UPLOAD_BYTES:
            raise StatementFormatError("Файл больше 5 МБ — выгрузите период покороче")
        table = read_table(content, file_name)
    except StatementFormatError as error:
        return templates.TemplateResponse(
            request,
            "import_upload.html",
            {"current": current, "error": str(error)},
            status_code=400,
        )

    columns = list(table.columns)
    return templates.TemplateResponse(
        request,
        "import_mapping.html",
        {
            "current": current,
            "file_name": file_name,
            # Kept in the page instead of on the server: the file is not stored until confirmed.
            "file_b64": base64.b64encode(content).decode(),
            "columns": columns,
            "guess": guess_columns(columns),
            "preview": table.head(PREVIEW_ROWS).to_dict("records"),
        },
    )


@router.post("/import")
async def import_confirm(request: Request, db: DbSession, current: RequiredUser) -> Response:
    """Step 2: parse with the chosen columns and save transactions."""
    form = await request.form(max_part_size=MAX_FORM_FIELD_BYTES)
    check_csrf(current, str(form.get("csrf_token", "")))
    file_name = str(form.get("file_name", "statement"))
    try:
        content = base64.b64decode(str(form.get("file_b64", "")), validate=True)
        mapping = ColumnMapping(
            date=str(form["date"]),
            amount=str(form["amount"]),
            description=str(form["description"]),
            bank_category=str(form.get("bank_category") or "") or None,
        )
        table = read_table(content, file_name)
        if not {mapping.date, mapping.amount, mapping.description} <= set(table.columns):
            raise StatementFormatError("Выберите колонки с датой, суммой и описанием")
        parsed = parse_rows(table, mapping)
    except (KeyError, binascii.Error):
        return RedirectResponse("/import", status_code=303)
    except StatementFormatError as error:
        return templates.TemplateResponse(
            request,
            "import_upload.html",
            {"current": current, "error": str(error)},
            status_code=400,
        )

    result = imports.import_statement(db, current.user.id, file_name, parsed)
    return templates.TemplateResponse(
        request,
        "import_result.html",
        {
            "current": current,
            "result": result,
            "month_param": month_param(result.latest_month) if result.latest_month else "",
        },
    )
