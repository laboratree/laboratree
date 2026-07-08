"""Field Lab ORM models: Survey, SurveyResponse, Quota (org-scoped, Postgres source of truth)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.orm import Base, OrgScopedMixin, PkMixin, TimestampMixin


class SurveyStatus(enum.StrEnum):
    DRAFT = "draft"
    LIVE = "live"
    PAUSED = "paused"
    CLOSED = "closed"


class ResponseStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    SCREENED_OUT = "screened_out"
    QUOTA_FULL = "quota_full"
    FLAGGED = "flagged"


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=lambda e: [m.value for m in e],
    )


class Survey(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "surveys"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[SurveyStatus] = mapped_column(
        _enum(SurveyStatus, "survey_status"), default=SurveyStatus.DRAFT, nullable=False
    )
    structure: Mapped[dict] = mapped_column(JSONB, default=dict)   # sections/questions/logic
    # U6 pre-registration: {hypotheses, planned_analyses[], frozen_at?, structure_hash?}
    prereg: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    public_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )

    # selectin so quotas serialize safely in async responses without a lazy IO load
    quotas: Mapped[list[Quota]] = relationship(
        back_populates="survey", cascade="all, delete-orphan", lazy="selectin"
    )
    responses: Mapped[list[SurveyResponse]] = relationship(
        back_populates="survey", cascade="all, delete-orphan"
    )


class Quota(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "survey_quotas"

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveys.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), default="")
    conditions: Mapped[list] = mapped_column(JSONB, default=list)  # [{qid, value}]
    target: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    survey: Mapped[Survey] = relationship(back_populates="quotas")


class SurveyResponse(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "survey_responses"

    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("surveys.id", ondelete="CASCADE"), index=True
    )
    instrument_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resume_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[ResponseStatus] = mapped_column(
        _enum(ResponseStatus, "response_status"),
        default=ResponseStatus.IN_PROGRESS,
        nullable=False,
    )
    answers: Mapped[dict] = mapped_column(JSONB, default=dict)      # {qid: value}
    fingerprint: Mapped[dict] = mapped_column(JSONB, default=dict)  # {ip_hash, ua_hash}
    # opaque link to a panel Invitation (never PII); nullable = anonymous/open-link response
    invitation_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    flags: Mapped[list] = mapped_column(JSONB, default=list)        # quality flag names
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    survey: Mapped[Survey] = relationship(back_populates="responses")


__all__ = [
    "SurveyStatus",
    "ResponseStatus",
    "Survey",
    "Quota",
    "SurveyResponse",
]
