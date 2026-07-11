"""qual studio II: codebooks

Revision ID: a5b6c7d8e9f0
Revises: f4c5d6e7a8b9
Create Date: 2026-07-08 20:10:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a5b6c7d8e9f0"
down_revision: str | None = "f4c5d6e7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "codebooks",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("codes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposed"),
        sa.Column("source_asset_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_codebooks_org_id"), "codebooks", ["org_id"], unique=False)
    op.create_index(op.f("ix_codebooks_project_id"), "codebooks", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_codebooks_project_id"), table_name="codebooks")
    op.drop_index(op.f("ix_codebooks_org_id"), table_name="codebooks")
    op.drop_table("codebooks")
