from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


def get_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))
