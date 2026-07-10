"""qual studio: media_assets

Revision ID: f4c5d6e7a8b9
Revises: e3b4c5d6f7a8
Create Date: 2026-07-08 18:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4c5d6e7a8b9"
down_revision: str | None = "e3b4c5d6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="uploaded"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_assets_org_id"), "media_assets", ["org_id"], unique=False)
    op.create_index(
        op.f("ix_media_assets_project_id"), "media_assets", ["project_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_media_assets_project_id"), table_name="media_assets")
    op.drop_index(op.f("ix_media_assets_org_id"), table_name="media_assets")
    op.drop_table("media_assets")
