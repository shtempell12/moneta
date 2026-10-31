from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import User, UserSession


def get_active(session: Session, token_hash: str, now: datetime) -> UserSession | None:
    return session.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash, UserSession.expires_at > now
        )
    )


def get_user(session: Session, user_session: UserSession) -> User:
    return session.get_one(User, user_session.user_id)


def delete_by_token_hash(session: Session, token_hash: str) -> int | None:
    """Delete the session and return its user id, or None if there was no such session."""
    return session.scalar(
        delete(UserSession)
        .where(UserSession.token_hash == token_hash)
        .returning(UserSession.user_id)
    )
