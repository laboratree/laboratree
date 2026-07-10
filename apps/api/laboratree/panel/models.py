"""Panel CRM ORM models: Respondent (PII), append-only ConsentRecord, Invitation (opaque link)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.orm import Base, OrgScopedMixin, PkMixin, TimestampMixin


class InvitationStatus(enum.StrEnum):
    SENT = "sent"
    STARTED = "started"
    COMPLETED = "completed"


class Respondent(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    """A panel member. The ONLY table holding respondent PII (email/name)."""

    __tablename__ = "respondents"

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)   # {gender, city, ...}
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="import")  # import|signup|manual

    consents: Mapped[list[ConsentRecord]] = relationship(
        back_populates="respondent", cascade="all, delete-orphan", lazy="selectin"
    )


class ConsentRecord(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    """Append-only consent trail: never updated or deleted while the respondent exists."""

    __tablename__ = "consent_records"

    respondent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("respondents.id", ondelete="CASCADE"), index=True
    )
    scope: Mapped[str] = mapped_column(String(120), default="surveys")
    text_hash: Mapped[str] = mapped_column(String(64), default="")  # sha256 of the consent text
    channel: Mapped[str] = mapped_column(String(60), default="import")

    respondent: Mapped[Respondent] = relationship(back_populates="consents")


class Invitation(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    """respondent × survey with a unique token — the only bridge between PII and responses."""

    __tablename__ = "invitations"

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveys.id", ondelete="CASCADE"), index=True
    )
    respondent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("respondents.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, name="invitation_status", native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        default=InvitationStatus.SENT,
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reminder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


__all__ = ["Respondent", "ConsentRecord", "Invitation", "InvitationStatus"]
