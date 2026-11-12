from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import Category
from app.domain.budget_table import ParsedTable
from app.domain.categorization import merchant_category
from app.domain.enums import CategoryKind, CategorySource
from app.domain.matching import BankRow, match_rows
from app.repositories import categories, events, merchant_rules, transactions


@dataclass(frozen=True)
class TableImportResult:
    rows: int
    matched: int
    categories_created: int
    errors: int

    @property
    def unmatched(self) -> int:
        return self.rows - self.matched


def import_table(session: Session, user_id: int, table: ParsedTable) -> TableImportResult:
    """Give statement transactions the categories from the user's own budget table.

    Matched transactions take the table's category and «who spent»; their merchants
    remember the category, so new statements are filed the family's way from day one.
    Table rows without a pair (cash, months without a statement) are only counted.
    """
    bank = {row.id: row for row in transactions.bank_rows_for_matching(session, user_id)}
    matches = match_rows(
        table.rows,
        [BankRow(t.id, t.date, t.amount, t.description) for t in bank.values()],
    )
    income_only: dict[str, bool] = defaultdict(lambda: True)
    for match in matches:
        name = table.rows[match.table_index].category.lower()
        income_only[name] = income_only[name] and bank[match.bank_key].amount > 0
    by_name, created = _ensure_categories(session, user_id, table, income_only)

    for match in matches:
        row, transaction = table.rows[match.table_index], bank[match.bank_key]
        transaction.category_id = by_name[row.category.lower()].id
        transaction.category_source = CategorySource.TABLE
        if row.spender and not transaction.spender:
            transaction.spender = row.spender[:50]
    session.flush()

    for merchant in {bank[match.bank_key].merchant_key for match in matches} - {""}:
        choices = transactions.manual_category_ids(session, user_id, merchant)
        remembered = merchant_category(choices, latest_choice=choices[-1])
        merchant_rules.upsert(session, user_id, merchant, remembered)
        session.flush()
        transactions.apply_category_to_merchant(session, user_id, merchant, remembered)

    result = TableImportResult(
        rows=len(table.rows),
        matched=len(matches),
        categories_created=created,
        errors=len(table.errors),
    )
    events.add(
        session,
        "budget_table_imported",
        user_id,
        {
            "rows": result.rows,
            "matched": result.matched,
            "categories_created": created,
            "errors": result.errors,
        },
    )
    session.commit()
    return result


def _ensure_categories(
    session: Session, user_id: int, table: ParsedTable, income_only: dict[str, bool]
) -> tuple[dict[str, Category], int]:
    """The user's categories by lowercase name, adding the table's missing ones.

    «Повар и продукты» and «повар и продукты» are one category: tables are typed by hand.
    """
    by_name = {c.name.lower(): c for c in categories.list_for_user(session, user_id)}
    created = 0
    for row in table.rows:
        name = row.category.lower()
        if name not in by_name:
            kind = CategoryKind.INCOME if income_only.get(name) else CategoryKind.EXPENSE
            by_name[name] = Category(user_id=user_id, name=row.category, kind=kind)
            session.add(by_name[name])
            created += 1
    session.flush()
    return by_name, created
