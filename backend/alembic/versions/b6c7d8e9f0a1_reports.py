"""deliverables: reports

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-07-08 22:10:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("share_token", sa.String(length=64), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_org_id"), "reports", ["org_id"], unique=False)
    op.create_index(op.f("ix_reports_project_id"), "reports", ["project_id"], unique=False)
    op.create_index(op.f("ix_reports_share_token"), "reports", ["share_token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_share_token"), table_name="reports")
    op.drop_index(op.f("ix_reports_project_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_org_id"), table_name="reports")
    op.drop_table("reports")
