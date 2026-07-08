"""Codebook ORM model — the HITL-gated vocabulary for thematic coding.

A codebook is *proposed* (usually LLM-drafted from transcripts) and must be explicitly *approved*
by a human before any coding can run against it — the Phase 13 human gate.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.orm import Base, OrgScopedMixin, PkMixin, TimestampMixin


class CodebookStatus(enum.StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"


class Codebook(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "codebooks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), default="Codebook")
    codes: Mapped[list] = mapped_column(JSONB, default=list)  # [{name, definition}]
    status: Mapped[CodebookStatus] = mapped_column(
        Enum(CodebookStatus, name="codebook_status", native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        default=CodebookStatus.PROPOSED,
        nullable=False,
    )
    source_asset_ids: Mapped[list] = mapped_column(JSONB, default=list)  # provenance of the draft
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["Codebook", "CodebookStatus"]
