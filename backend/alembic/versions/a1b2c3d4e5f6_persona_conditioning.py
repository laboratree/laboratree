"""Objective conditioning on persona cohorts (honesty labels + recorded trait deltas).

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("persona_cohorts", sa.Column("objective", sa.String(1000), nullable=True))
    op.add_column("persona_cohorts",
                  sa.Column("conditioning", sa.String(20), nullable=False,
                            server_default="neutral"))
    op.add_column("persona_cohorts",
                  sa.Column("trait_delta", JSONB(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("persona_cohorts", "trait_delta")
    op.drop_column("persona_cohorts", "conditioning")
    op.drop_column("persona_cohorts", "objective")
