from sqlalchemy.orm import Session

from app.db.models import Category
from app.repositories import categories, events

MAX_NAME_LENGTH = 100


class CategoryError(Exception):
    """Invalid category; the message is safe to show to the user."""


def add_category(session: Session, user_id: int, name: str) -> Category:
    """Add the user's own category, e.g. «Развивашки» or «Бьюти»."""
    name = " ".join(name.split())
    if not name:
        raise CategoryError("Введите название категории")
    if len(name) > MAX_NAME_LENGTH:
        raise CategoryError(f"Название не длиннее {MAX_NAME_LENGTH} символов")
    if categories.get_by_name(session, user_id, name):
        raise CategoryError("Такая категория уже есть")

    category = Category(user_id=user_id, name=name)
    session.add(category)
    session.flush()
    events.add(session, "category_created", user_id, {"category_id": category.id})
    session.commit()
    return category
