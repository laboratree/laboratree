"""GIN full-text index on paper_chunks.text — the hybrid retrieval lexical leg.

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
"""

from __future__ import annotations

from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None

INDEX = "ix_paper_chunks_text_fts"


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {INDEX} ON paper_chunks "
        "USING gin (to_tsvector('english', text))"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX}")
