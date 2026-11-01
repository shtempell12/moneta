from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import MerchantRule


def as_dict(session: Session, user_id: int) -> dict[str, int]:
    """All the user's rules as «merchant key → category id»."""
    rules = session.scalars(select(MerchantRule).where(MerchantRule.user_id == user_id))
    return {rule.merchant_key: rule.category_id for rule in rules}


def upsert(session: Session, user_id: int, merchant_key: str, category_id: int) -> None:
    statement = insert(MerchantRule).values(
        user_id=user_id, merchant_key=merchant_key, category_id=category_id
    )
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[MerchantRule.user_id, MerchantRule.merchant_key],
            set_={"category_id": category_id, "updated_at": func.now()},
        )
    )
