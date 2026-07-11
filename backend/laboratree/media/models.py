"""MediaAsset ORM model — one row per uploaded/recorded audio-video file (Qual Studio)."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.orm import Base, OrgScopedMixin, PkMixin, TimestampMixin


class MediaStatus(enum.StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    TRANSCRIBED = "transcribed"
    FAILED = "failed"


class MediaAsset(PkMixin, OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "media_assets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(300), default="")
    kind: Mapped[str] = mapped_column(String(20), default="audio")  # audio|video|other
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[MediaStatus] = mapped_column(
        Enum(MediaStatus, name="media_status", native_enum=False,
             values_callable=lambda e: [m.value for m in e]),
        default=MediaStatus.UPLOADED,
        nullable=False,
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str] = mapped_column(String(20), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(40), default="upload")  # upload|recording|survey


__all__ = ["MediaAsset", "MediaStatus"]
