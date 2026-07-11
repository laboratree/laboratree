"""Persona ORM models: PersonaCohort + Persona (stable traits + accumulating memory)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.orm import Base, OrgScopedMixin, PkMixin, TimestampMixin


class PersonaCohort(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    """A named, reusable set of persona twins built to target margins."""

    __tablename__ = "persona_cohorts"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), default="Cohort")
    margins: Mapped[dict] = mapped_column(JSONB, default=dict)   # {dim: {cat: share}}
    graph: Mapped[list] = mapped_column(JSONB, default=list)     # social edges [{a,b,weight}]
    n: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    waves: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # surveys run so far
    # objective conditioning (honesty labels): neutral by default; conditioned cohorts record
    # the survey objective AND the exact per-trait bias injected (trait_delta) — and are
    # REFUSED for RCT/impact work at the API.
    objective: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    conditioning: Mapped[str] = mapped_column(String(20), default="neutral", nullable=False)
    trait_delta: Mapped[dict] = mapped_column(JSONB, default=dict)

    personas: Mapped[list[Persona]] = relationship(
        back_populates="cohort", cascade="all, delete-orphan"
    )


class Persona(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    """One synthetic respondent: attributes, stable OCEAN traits, and episodic memory."""

    __tablename__ = "personas"

    cohort_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_cohorts.id", ondelete="CASCADE"), index=True
    )
    handle: Mapped[str] = mapped_column(String(40), default="")  # p1, p2, … (stable within cohort)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)  # {gender, city, …}
    traits: Mapped[dict] = mapped_column(JSONB, default=dict)      # OCEAN floats
    bio: Mapped[str] = mapped_column(String(600), default="")
    # episodic memory: [{wave, survey_id, answers, ts}] — grows one entry per survey wave
    memory: Mapped[list] = mapped_column(JSONB, default=list)

    cohort: Mapped[PersonaCohort] = relationship(back_populates="personas")


__all__ = ["PersonaCohort", "Persona"]
