"""add merchant key to transactions

Revision ID: 96ca9edc72f4
Revises: b0d1c69f0205
Create Date: 2026-11-01 10:30:43.121222

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "96ca9edc72f4"
down_revision: str | Sequence[str] | None = "b0d1c69f0205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "transactions",
        sa.Column("merchant_key", sa.String(length=255), server_default="", nullable=False),
    )
    op.create_index(
        op.f("ix_transactions_user_id_merchant_key"),
        "transactions",
        ["user_id", "merchant_key"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_transactions_user_id_merchant_key"), table_name="transactions")
    op.drop_column("transactions", "merchant_key")
