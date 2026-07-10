"""fieldwork: surveys, survey_quotas, survey_responses

Revision ID: c1f0a2b3d4e5
Revises: 1a6db7e774dd
Create Date: 2026-07-06 18:20:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1f0a2b3d4e5"
down_revision: str | None = "1a6db7e774dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "surveys",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("structure", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("public_token", sa.String(length=64), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_surveys_org_id"), "surveys", ["org_id"], unique=False)
    op.create_index(op.f("ix_surveys_project_id"), "surveys", ["project_id"], unique=False)
    op.create_index(op.f("ix_surveys_public_token"), "surveys", ["public_token"], unique=True)

    op.create_table(
        "survey_quotas",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("target", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_survey_quotas_org_id"), "survey_quotas", ["org_id"], unique=False)
    op.create_index(
        op.f("ix_survey_quotas_survey_id"), "survey_quotas", ["survey_id"], unique=False
    )

    op.create_table(
        "survey_responses",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("instrument_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("resume_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fingerprint", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_survey_responses_org_id"), "survey_responses", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_survey_responses_survey_id"), "survey_responses", ["survey_id"], unique=False
    )
    op.create_index(
        op.f("ix_survey_responses_resume_key"),
        "survey_responses",
        ["resume_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_survey_responses_resume_key"), table_name="survey_responses")
    op.drop_index(op.f("ix_survey_responses_survey_id"), table_name="survey_responses")
    op.drop_index(op.f("ix_survey_responses_org_id"), table_name="survey_responses")
    op.drop_table("survey_responses")
    op.drop_index(op.f("ix_survey_quotas_survey_id"), table_name="survey_quotas")
    op.drop_index(op.f("ix_survey_quotas_org_id"), table_name="survey_quotas")
    op.drop_table("survey_quotas")
    op.drop_index(op.f("ix_surveys_public_token"), table_name="surveys")
    op.drop_index(op.f("ix_surveys_project_id"), table_name="surveys")
    op.drop_index(op.f("ix_surveys_org_id"), table_name="surveys")
    op.drop_table("surveys")
