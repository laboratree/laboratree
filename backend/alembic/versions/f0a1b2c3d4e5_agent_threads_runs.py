"""Agent runs (job-style, live steps, frontier), chat threads, and the blob catalog.

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None


def _base_cols():
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        *_base_cols(),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("lab", sa.String(60), nullable=False, server_default=""),
        sa.Column("task", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("steps", JSONB(), nullable=False, server_default="[]"),
        sa.Column("findings", JSONB(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("run_id", UUID(as_uuid=True),
                  sa.ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trace_key", sa.String(500), nullable=False, server_default=""),
        sa.Column("llm_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("frontier", JSONB(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "agent_threads",
        *_base_cols(),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("lab", sa.String(60), nullable=False, server_default=""),
        sa.Column("messages", JSONB(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "blob_notes",
        *_base_cols(),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("key", sa.String(500), nullable=False, unique=True, index=True),
        sa.Column("kind", sa.String(40), nullable=False, server_default="blob"),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(300), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("blob_notes")
    op.drop_table("agent_threads")
    op.drop_table("agent_runs")
