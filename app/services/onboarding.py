from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.db.models import Category, Goal, User
from app.domain.onboarding import Answers
from app.repositories import categories, events


def complete(session: Session, user: User, answers: Answers, today: date) -> None:
    """Apply the first-run answers: a goal, the income, the user's own categories."""
    if answers.goal is not None:
        session.add(
            Goal(
                user_id=user.id,
                name=answers.goal.name,
                target_amount=answers.goal.target,
                deadline=answers.goal.deadline,
            )
        )
    added = 0
    for name in answers.categories:
        if categories.get_by_name(session, user.id, name) is None:
            session.add(Category(user_id=user.id, name=name))
            added += 1
    if answers.income is not None:
        user.monthly_income = answers.income
    user.onboarded_at = datetime.now(UTC)
    # What people answer (not the amounts) is product research data for the team.
    events.add(
        session,
        "onboarding_completed",
        user.id,
        {
            "goal": answers.goal is not None,
            "income": answers.income is not None,
            "categories_added": added,
            "current_tool": answers.current_tool,
        },
    )
    session.commit()


def skip(session: Session, user: User) -> None:
    user.onboarded_at = datetime.now(UTC)
    events.add(session, "onboarding_skipped", user.id)
    session.commit()
