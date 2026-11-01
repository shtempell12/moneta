from sqlalchemy.orm import Session

from app.domain.categorization import (
    BankCategoryCategorizer,
    CascadeCategorizer,
    HistoryCategorizer,
)
from app.repositories import categories, merchant_rules


def build_categorizer(session: Session, user_id: int) -> CascadeCategorizer:
    """The user's own history first, the bank's category as a fallback."""
    return CascadeCategorizer(
        [
            HistoryCategorizer(merchant_rules.as_dict(session, user_id)),
            BankCategoryCategorizer(categories.ids_by_name(session, user_id)),
        ]
    )
