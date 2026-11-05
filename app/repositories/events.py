from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Event


def add(
    session: Session, event_type: str, user_id: int | None, payload: dict[str, Any] | None = None
) -> None:
    session.add(Event(type=event_type, user_id=user_id, payload=payload or {}))


def count_since(
    session: Session, event_type: str, since: datetime, payload_key: str, payload_value: str
) -> int:
    query = select(func.count()).where(
        Event.type == event_type,
        Event.created_at >= since,
        Event.payload[payload_key].astext == payload_value,
    )
    return session.scalar(query) or 0


def delete_with_payload(session: Session, payload_key: str, payload_value: str) -> None:
    """Delete events that point to someone by a payload value, e.g. failed logins by email hash."""
    session.execute(delete(Event).where(Event.payload[payload_key].astext == payload_value))
