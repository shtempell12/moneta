"""add goals

Revision ID: 2a80524611d3
Revises: fe0ac176d974
Create Date: 2026-11-05 13:13:05.484056

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a80524611d3"
down_revision: str | Sequence[str] | None = "fe0ac176d974"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("target_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("saved_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("saved_amount >= 0", name=op.f("ck_goals_saved_not_negative")),
        sa.CheckConstraint("target_amount > 0", name=op.f("ck_goals_target_positive")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_goals_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goals")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("goals")
