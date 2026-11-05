from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Goal
from app.domain.goals import GoalError, GoalProgress, goal_progress, make_goal, parse_money
from app.repositories import events, goals


def goals_with_progress(
    session: Session, user_id: int, today: date
) -> list[tuple[Goal, GoalProgress]]:
    return [
        (goal, goal_progress(goal.target_amount, goal.saved_amount, goal.deadline, today))
        for goal in goals.list_for_user(session, user_id)
    ]


def create_goal(
    session: Session, user_id: int, name: str, target: str, deadline: str, today: date
) -> Goal:
    new = make_goal(name, target, deadline, today)
    goal = Goal(user_id=user_id, name=new.name, target_amount=new.target, deadline=new.deadline)
    session.add(goal)
    session.flush()
    events.add(session, "goal_created", user_id, {"goal_id": goal.id})
    session.commit()
    return goal


def change_saved(
    session: Session, user_id: int, goal_id: int, amount: str, withdraw: bool = False
) -> Goal:
    """«Отложил 10 000» adds to the goal, «Взял 3 000» takes from it."""
    goal = _get(session, user_id, goal_id)
    change = parse_money(amount)
    if withdraw:
        if change > goal.saved_amount:
            raise GoalError("Нельзя взять больше, чем отложено")
        change = -change
    goal.saved_amount += change
    events.add(session, "goal_saved", user_id, {"goal_id": goal.id, "amount": str(change)})
    session.commit()
    return goal


def delete_goal(session: Session, user_id: int, goal_id: int) -> None:
    goal = _get(session, user_id, goal_id)
    session.delete(goal)
    events.add(session, "goal_deleted", user_id, {"goal_id": goal_id})
    session.commit()


def _get(session: Session, user_id: int, goal_id: int) -> Goal:
    goal = goals.get_for_user(session, user_id, goal_id)
    if goal is None:
        raise GoalError("Цель не найдена")
    return goal
