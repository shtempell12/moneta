from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Goal


def list_for_user(session: Session, user_id: int) -> Sequence[Goal]:
    return session.scalars(select(Goal).where(Goal.user_id == user_id).order_by(Goal.id)).all()


def get_for_user(session: Session, user_id: int, goal_id: int) -> Goal | None:
    return session.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))
