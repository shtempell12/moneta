from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Event
from app.domain.goals import GoalError
from app.services import goals

TODAY = date(2026, 11, 5)


def test_goal_is_created_and_filled_step_by_step(session: Session, user_id: int) -> None:
    goal = goals.create_goal(session, user_id, "Отпуск", "120 000", "01.06.2027", TODAY)

    goals.change_saved(session, user_id, goal.id, "20 000")
    goals.change_saved(session, user_id, goal.id, "5 000", withdraw=True)

    [(saved_goal, progress)] = goals.goals_with_progress(session, user_id, TODAY)
    assert saved_goal.saved_amount == Decimal("15000.00")
    assert progress.monthly == Decimal("15000")
    event_types = session.scalars(select(Event.type).order_by(Event.id)).all()
    assert event_types[-3:] == ["goal_created", "goal_saved", "goal_saved"]


def test_cannot_take_more_than_saved(session: Session, user_id: int) -> None:
    goal = goals.create_goal(session, user_id, "Подушка", "50000", "", TODAY)
    goals.change_saved(session, user_id, goal.id, "1000")

    with pytest.raises(GoalError, match="больше, чем отложено"):
        goals.change_saved(session, user_id, goal.id, "1500", withdraw=True)


def test_deleted_goal_disappears(session: Session, user_id: int) -> None:
    goal = goals.create_goal(session, user_id, "Подушка", "50000", "", TODAY)

    goals.delete_goal(session, user_id, goal.id)

    assert goals.goals_with_progress(session, user_id, TODAY) == []
    with pytest.raises(GoalError, match="не найдена"):
        goals.change_saved(session, user_id, goal.id, "100")
