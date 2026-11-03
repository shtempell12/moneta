"""Pages for adding, editing and deleting transactions by hand."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.db.models import Transaction
from app.domain.entries import EntryError, EntryForm
from app.domain.months import month_param
from app.repositories import categories
from app.repositories import transactions as transactions_repo
from app.services import transactions
from app.services.transactions import NotEditableError, NotFoundError
from app.web.budget import today
from app.web.session import DbSession, RequiredUser, check_csrf
from app.web.templating import templates

router = APIRouter()


def entry_form(
    date: Annotated[str, Form()] = "",
    amount: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    category_id: Annotated[int, Form()] = 0,
    spender: Annotated[str, Form()] = "",
) -> EntryForm:
    # Defaults: the edit form of a bank transaction sends only «Кто потратил».
    return EntryForm(date, amount, description, category_id, spender)


EntryFormData = Annotated[EntryForm, Depends(entry_form)]


@router.get("/transactions/new")
def new_transaction_page(request: Request, db: DbSession, current: RequiredUser) -> Response:
    values = EntryForm(date=today().isoformat(), amount="", description="", category_id=0)
    return _form_response(request, db, current, values=values)


@router.post("/transactions/new")
def add_transaction(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    form: EntryFormData,
    csrf_token: Annotated[str, Form()],
) -> Response:
    check_csrf(current, csrf_token)
    try:
        transaction = transactions.add_transaction(db, current.user.id, form)
    except NotFoundError:
        raise HTTPException(status_code=404) from None
    except EntryError as error:
        return _form_response(request, db, current, values=form, error=str(error))
    return _back_to_month(transaction)


@router.get("/transactions/{transaction_id}/edit")
def edit_transaction_page(
    request: Request, db: DbSession, current: RequiredUser, transaction_id: int
) -> Response:
    transaction = _get(db, current.user.id, transaction_id)
    values = EntryForm(
        date=transaction.date.isoformat(),
        amount=f"{abs(transaction.amount)}".replace(".", ","),
        description=transaction.description,
        category_id=transaction.category_id or 0,
        spender=transaction.spender or "",
    )
    return _form_response(request, db, current, values=values, transaction=transaction)


@router.post("/transactions/{transaction_id}/edit")
def edit_transaction(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    transaction_id: int,
    form: EntryFormData,
    csrf_token: Annotated[str, Form()],
) -> Response:
    """Hand-added transactions change completely; bank ones change only «Кто потратил»."""
    check_csrf(current, csrf_token)
    transaction = _get(db, current.user.id, transaction_id)
    try:
        if transaction.added_by_hand:
            transactions.edit_transaction(db, current.user.id, transaction_id, form)
        else:
            transactions.set_spender(db, current.user.id, transaction_id, form.spender)
    except NotFoundError:
        raise HTTPException(status_code=404) from None
    except EntryError as error:
        return _form_response(
            request, db, current, values=form, transaction=transaction, error=str(error)
        )
    return _back_to_month(transaction)


@router.post("/transactions/{transaction_id}/delete")
def delete_transaction(
    db: DbSession,
    current: RequiredUser,
    transaction_id: int,
    csrf_token: Annotated[str, Form()],
) -> Response:
    check_csrf(current, csrf_token)
    transaction = _get(db, current.user.id, transaction_id)
    month = transaction.date.replace(day=1)
    try:
        transactions.delete_transaction(db, current.user.id, transaction_id)
    except NotEditableError:
        raise HTTPException(status_code=400) from None
    return RedirectResponse(f"/transactions?month={month_param(month)}", status_code=303)


def _get(db: DbSession, user_id: int, transaction_id: int) -> Transaction:
    transaction = transactions_repo.get_for_user(db, user_id, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404)
    return transaction


def _back_to_month(transaction: Transaction) -> Response:
    month = month_param(transaction.date.replace(day=1))
    return RedirectResponse(f"/transactions?month={month}", status_code=303)


def _form_response(
    request: Request,
    db: DbSession,
    current: RequiredUser,
    values: EntryForm,
    transaction: Transaction | None = None,
    error: str | None = None,
) -> Response:
    return templates.TemplateResponse(
        request,
        "transaction_form.html",
        {
            "current": current,
            "transaction": transaction,
            "values": values,
            "categories": categories.list_for_user(db, current.user.id),
            "spenders": transactions_repo.spenders(db, current.user.id),
            "error": error,
        },
        status_code=400 if error else 200,
    )
