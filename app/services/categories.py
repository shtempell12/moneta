from sqlalchemy.orm import Session

from app.db.models import Category
from app.repositories import categories, events, transactions

MAX_NAME_LENGTH = 100


class CategoryError(Exception):
    """Invalid category; the message is safe to show to the user."""


def add_category(session: Session, user_id: int, name: str) -> Category:
    """Add the user's own category, e.g. «Развивашки» or «Бьюти»."""
    name = _clean_name(session, user_id, name)
    category = Category(user_id=user_id, name=name)
    session.add(category)
    session.flush()
    events.add(session, "category_created", user_id, {"category_id": category.id})
    session.commit()
    return category


def rename_category(session: Session, user_id: int, category_id: int, name: str) -> None:
    """Rename a category; its transactions and remembered merchants stay with it."""
    category = _get(session, user_id, category_id)
    name = _clean_name(session, user_id, name, keep=category)
    category.name = name
    events.add(session, "category_renamed", user_id, {"category_id": category.id})
    session.commit()


def delete_category(session: Session, user_id: int, category_id: int) -> None:
    """Delete a category. Its transactions become uncategorized, its merchant rules go away."""
    category = _get(session, user_id, category_id)
    transactions.clear_category(session, user_id, category.id)
    session.delete(category)
    events.add(session, "category_deleted", user_id, {"category_id": category_id})
    session.commit()


def _get(session: Session, user_id: int, category_id: int) -> Category:
    category = categories.get_for_user(session, user_id, category_id)
    if category is None:
        raise CategoryError("Категория не найдена")
    return category


def _clean_name(session: Session, user_id: int, name: str, keep: Category | None = None) -> str:
    """Collapse spaces and check the name; `keep` is the category being renamed."""
    name = " ".join(name.split())
    if not name:
        raise CategoryError("Введите название категории")
    if len(name) > MAX_NAME_LENGTH:
        raise CategoryError(f"Название не длиннее {MAX_NAME_LENGTH} символов")
    existing = categories.get_by_name(session, user_id, name)
    if existing is not None and existing is not keep:
        raise CategoryError("Такая категория уже есть")
    return name
