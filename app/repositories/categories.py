from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category


def list_for_user(session: Session, user_id: int) -> Sequence[Category]:
    return session.scalars(
        select(Category).where(Category.user_id == user_id).order_by(Category.kind, Category.id)
    ).all()


def get_for_user(session: Session, user_id: int, category_id: int) -> Category | None:
    return session.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )


def get_by_name(session: Session, user_id: int, name: str) -> Category | None:
    return session.scalar(
        select(Category).where(Category.user_id == user_id, Category.name == name)
    )


def ids_by_name(session: Session, user_id: int) -> dict[str, int]:
    return {category.name: category.id for category in list_for_user(session, user_id)}
