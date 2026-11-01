from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category


def list_for_user(session: Session, user_id: int) -> Sequence[Category]:
    return session.scalars(
        select(Category).where(Category.user_id == user_id).order_by(Category.kind, Category.id)
    ).all()
