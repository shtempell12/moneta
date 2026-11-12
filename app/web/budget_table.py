"""Pages for uploading the user's own budget table (Excel / CSV)."""

import base64
import binascii
from typing import Annotated

from fastapi import APIRouter, Form, Request, Response, UploadFile
from fastapi.responses import RedirectResponse

from app.domain.budget_table import (
    TABLE_HEADER_HINTS,
    TableMapping,
    guess_table_columns,
    parse_table_rows,
)
from app.domain.statement import StatementFormatError, read_table
from app.services.budget_table import import_table
from app.web.budget import MAX_FORM_FIELD_BYTES, MAX_UPLOAD_BYTES, PREVIEW_ROWS
from app.web.session import DbSession, RequiredUser, check_csrf
from app.web.templating import templates

router = APIRouter()


@router.get("/budget-table")
def upload_page(request: Request, current: RequiredUser) -> Response:
    return templates.TemplateResponse(request, "budget_table_upload.html", {"current": current})


@router.post("/budget-table/preview")
async def preview(
    request: Request,
    current: RequiredUser,
    file: UploadFile,
    csrf_token: Annotated[str, Form()],
) -> Response:
    """Step 1: the first rows and our guess of which column is which."""
    check_csrf(current, csrf_token)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    file_name = file.filename or "budget.xlsx"
    try:
        if len(content) > MAX_UPLOAD_BYTES:
            raise StatementFormatError("Файл больше 5 МБ — сохраните таблицу за меньший период")
        table = read_table(content, file_name, TABLE_HEADER_HINTS)
    except StatementFormatError as error:
        return _upload_error(request, current, str(error))

    columns = list(table.columns)
    return templates.TemplateResponse(
        request,
        "budget_table_mapping.html",
        {
            "current": current,
            "file_name": file_name,
            "file_b64": base64.b64encode(content).decode(),
            "columns": columns,
            "guess": guess_table_columns(columns),
            "preview": table.head(PREVIEW_ROWS).to_dict("records"),
        },
    )


@router.post("/budget-table")
async def confirm(request: Request, db: DbSession, current: RequiredUser) -> Response:
    """Step 2: read the rows with the chosen columns and match them with the statements."""
    form = await request.form(max_part_size=MAX_FORM_FIELD_BYTES)
    check_csrf(current, str(form.get("csrf_token", "")))
    file_name = str(form.get("file_name", "budget.xlsx"))
    try:
        content = base64.b64decode(str(form.get("file_b64", "")), validate=True)
        mapping = TableMapping(
            date=str(form["date"]),
            amount=str(form["amount"]),
            category=str(form["category"]),
            note=str(form.get("note") or "") or None,
            spender=str(form.get("spender") or "") or None,
        )
        table = read_table(content, file_name, TABLE_HEADER_HINTS)
        if not {mapping.date, mapping.amount, mapping.category} <= set(table.columns):
            raise StatementFormatError("Выберите колонки с датой, суммой и категорией")
        parsed = parse_table_rows(table, mapping)
    except (KeyError, binascii.Error):
        return RedirectResponse("/budget-table", status_code=303)
    except StatementFormatError as error:
        return _upload_error(request, current, str(error))

    result = import_table(db, current.user.id, parsed)
    return templates.TemplateResponse(
        request, "budget_table_result.html", {"current": current, "result": result}
    )


def _upload_error(request: Request, current: RequiredUser, error: str) -> Response:
    return templates.TemplateResponse(
        request,
        "budget_table_upload.html",
        {"current": current, "error": error},
        status_code=400,
    )
