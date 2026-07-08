"""surveys: pre-registration lock column (U6)

Revision ID: d2a1b3c4e5f6
Revises: c1f0a2b3d4e5
Create Date: 2026-07-08 13:10:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2a1b3c4e5f6"
down_revision: str | None = "c1f0a2b3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "surveys",
        sa.Column(
            "prereg",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("surveys", "prereg")
