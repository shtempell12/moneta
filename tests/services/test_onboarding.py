from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Event, Goal, User
from app.domain.onboarding import make_answers
from app.services import onboarding

TODAY = date(2026, 11, 11)


def test_answers_create_goal_categories_and_income(session: Session, user_id: int) -> None:
    user = session.get_one(User, user_id)
    answers = make_answers(
        goal_name="Отпуск",
        goal_target="120 000",
        goal_deadline="",
        income="95 000",
        categories=["Развивашки", "Дети"],
        custom_category="",
        current_tool="excel",
        today=TODAY,
    )

    onboarding.complete(session, user, answers, TODAY)

    assert session.scalars(select(Goal.name)).all() == ["Отпуск"]
    assert user.monthly_income == Decimal("95000.00") and user.onboarded_at is not None
    names = session.scalars(select(Category.name)).all()
    assert names.count("Развивашки") == 1 and names.count("Дети") == 1
    event = session.scalars(select(Event).where(Event.type == "onboarding_completed")).one()
    assert event.payload == {
        "goal": True,
        "income": True,
        "categories_added": 1,
        "current_tool": "excel",
    }


def test_skipping_marks_onboarding_done(session: Session, user_id: int) -> None:
    user = session.get_one(User, user_id)

    onboarding.skip(session, user)

    assert user.onboarded_at is not None
    assert session.scalars(select(Goal)).all() == []
