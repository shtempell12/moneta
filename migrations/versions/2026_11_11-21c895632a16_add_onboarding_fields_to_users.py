"""add onboarding fields to users

Revision ID: 21c895632a16
Revises: 2a80524611d3
Create Date: 2026-11-11 19:46:51.118510

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21c895632a16"
down_revision: str | Sequence[str] | None = "2a80524611d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users", sa.Column("monthly_income", sa.Numeric(precision=12, scale=2), nullable=True)
    )
    # Accounts created before onboarding existed should not be asked the questions again.
    op.execute("UPDATE users SET onboarded_at = created_at")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "monthly_income")
    op.drop_column("users", "onboarded_at")
