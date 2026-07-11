"""persona lab: persona_cohorts + personas

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-07-08 23:40:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "persona_cohorts",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("margins", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("n", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_persona_cohorts_org_id"), "persona_cohorts", ["org_id"], unique=False)
    op.create_index(op.f("ix_persona_cohorts_project_id"), "persona_cohorts",
                    ["project_id"], unique=False)

    op.create_table(
        "personas",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("cohort_id", sa.UUID(), nullable=False),
        sa.Column("handle", sa.String(length=40), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("traits", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bio", sa.String(length=600), nullable=True),
        sa.Column("memory", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_id"], ["persona_cohorts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_personas_org_id"), "personas", ["org_id"], unique=False)
    op.create_index(op.f("ix_personas_cohort_id"), "personas", ["cohort_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_personas_cohort_id"), table_name="personas")
    op.drop_index(op.f("ix_personas_org_id"), table_name="personas")
    op.drop_table("personas")
    op.drop_index(op.f("ix_persona_cohorts_project_id"), table_name="persona_cohorts")
    op.drop_index(op.f("ix_persona_cohorts_org_id"), table_name="persona_cohorts")
    op.drop_table("persona_cohorts")
