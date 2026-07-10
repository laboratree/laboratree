"""Report ORM model — a composed, Evidence-bound client deliverable (Phase 15)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.orm import Base, OrgScopedMixin, PkMixin, TimestampMixin


class Report(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    """A block-based report. Numeric/quote/table/chart blocks MUST bind an Evidence id (U1)."""

    __tablename__ = "reports"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300), default="Untitled report")
    blocks: Mapped[list] = mapped_column(JSONB, default=list)  # ordered typed blocks
    share_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )


__all__ = ["Report"]
