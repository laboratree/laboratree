"""panel CRM: respondents, consent_records, invitations + survey_responses.invitation_token

Revision ID: e3b4c5d6f7a8
Revises: d2a1b3c4e5f6
Create Date: 2026-07-08 16:40:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e3b4c5d6f7a8"
down_revision: str | None = "d2a1b3c4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "respondents",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("do_not_contact", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(length=60), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_respondents_org_id"), "respondents", ["org_id"], unique=False)
    op.create_index(op.f("ix_respondents_email"), "respondents", ["email"], unique=False)

    op.create_table(
        "consent_records",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("respondent_id", sa.UUID(), nullable=False),
        sa.Column("scope", sa.String(length=120), nullable=True),
        sa.Column("text_hash", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=60), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["respondent_id"], ["respondents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consent_records_org_id"), "consent_records", ["org_id"], unique=False)
    op.create_index(
        op.f("ix_consent_records_respondent_id"), "consent_records", ["respondent_id"], unique=False
    )

    op.create_table(
        "invitations",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("respondent_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="sent"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["survey_id"], ["surveys.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["respondent_id"], ["respondents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invitations_org_id"), "invitations", ["org_id"], unique=False)
    op.create_index(op.f("ix_invitations_survey_id"), "invitations", ["survey_id"], unique=False)
    op.create_index(
        op.f("ix_invitations_respondent_id"), "invitations", ["respondent_id"], unique=False
    )
    op.create_index(op.f("ix_invitations_token"), "invitations", ["token"], unique=True)

    op.add_column(
        "survey_responses",
        sa.Column("invitation_token", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_survey_responses_invitation_token"),
        "survey_responses",
        ["invitation_token"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_survey_responses_invitation_token"), table_name="survey_responses")
    op.drop_column("survey_responses", "invitation_token")
    op.drop_index(op.f("ix_invitations_token"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_respondent_id"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_survey_id"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_org_id"), table_name="invitations")
    op.drop_table("invitations")
    op.drop_index(op.f("ix_consent_records_respondent_id"), table_name="consent_records")
    op.drop_index(op.f("ix_consent_records_org_id"), table_name="consent_records")
    op.drop_table("consent_records")
    op.drop_index(op.f("ix_respondents_email"), table_name="respondents")
    op.drop_index(op.f("ix_respondents_org_id"), table_name="respondents")
    op.drop_table("respondents")
