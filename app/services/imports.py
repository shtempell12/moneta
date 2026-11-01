from collections import Counter
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Import, Transaction
from app.domain.categorization import TransactionFeatures
from app.domain.parsing import merchant_key
from app.domain.statement import ParsedStatement, RowError
from app.repositories import events, transactions
from app.services.categorization import build_categorizer


@dataclass(frozen=True)
class ImportResult:
    imported: int
    duplicates: int
    errors: list[RowError]
    by_source: dict[str, int]
    latest_month: date | None


def import_statement(
    session: Session, user_id: int, file_name: str, statement: ParsedStatement
) -> ImportResult:
    """Save statement rows as transactions with automatically chosen categories.

    Rows that were already imported (same date, amount and description) are skipped,
    so uploading the same file twice does not double the spending.
    """
    rows = statement.rows
    already_imported = (
        transactions.existing_keys(
            session, user_id, min(row.date for row in rows), max(row.date for row in rows)
        )
        if rows
        else set()
    )
    categorizer = build_categorizer(session, user_id)
    statement_import = Import(user_id=user_id, file_name=file_name[:255])
    session.add(statement_import)
    session.flush()

    sources: Counter[str] = Counter()
    duplicates = 0
    for row in rows:
        key = (row.date, row.amount, row.description[:500])
        if key in already_imported:
            duplicates += 1
            continue
        already_imported.add(key)
        merchant = merchant_key(row.description)[:255]
        prediction = categorizer.predict(TransactionFeatures(merchant, row.bank_category))
        session.add(
            Transaction(
                user_id=user_id,
                import_id=statement_import.id,
                date=row.date,
                amount=row.amount,
                description=row.description[:500],
                merchant_key=merchant,
                bank_category=row.bank_category[:100] if row.bank_category else None,
                category_id=prediction.category_id if prediction else None,
                category_source=prediction.source if prediction else None,
            )
        )
        sources[prediction.source.value if prediction else "none"] += 1

    imported = sum(sources.values())
    events.add(
        session,
        "statement_imported",
        user_id,
        {
            "import_id": statement_import.id,
            "imported": imported,
            "duplicates": duplicates,
            "errors": len(statement.errors),
            "by_source": dict(sources),
        },
    )
    session.commit()
    return ImportResult(
        imported=imported,
        duplicates=duplicates,
        errors=statement.errors,
        by_source=dict(sources),
        latest_month=max(row.date for row in rows).replace(day=1) if rows else None,
    )
