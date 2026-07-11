"""Agent experience database — long-term strategy memory for the cognitive architecture.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_experiences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("goal_kind", sa.String(40), nullable=False, server_default="", index=True),
        sa.Column("goal_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("plan", JSONB(), nullable=False, server_default="[]"),
        sa.Column("outcome", sa.String(20), nullable=False, server_default="succeeded"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lessons", JSONB(), nullable=False, server_default="[]"),
        sa.Column("refined", sa.Boolean(), nullable=False, server_default="false"),
    )
    # lexical recall leg (mirrors the paper_chunks FTS pattern)
    op.execute(
        "CREATE INDEX ix_agent_experiences_fts ON agent_experiences "
        "USING gin (to_tsvector('english', goal_text || ' ' || lessons::text))"
    )


def downgrade() -> None:
    op.drop_table("agent_experiences")
