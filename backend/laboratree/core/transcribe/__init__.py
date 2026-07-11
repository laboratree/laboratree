"""Pluggable transcription — a ``TranscriptionEngine`` behind settings (like OCR/BlobStore/Mailer).

Backends: ``openai`` (any OpenAI-compatible audio endpoint — OpenAI, Azure, or a self-hosted
faster-whisper server) and ``none`` (transcription disabled → assets fail with a clear reason).
Engines return timestamped segments; callers own persistence.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Protocol

from ..config import settings

log = logging.getLogger(__name__)


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    segments: list[Segment]
    text: str
    language: str = ""


class TranscriptionEngine(Protocol):
    def transcribe(self, audio: bytes, filename: str) -> TranscriptResult: ...


class TranscriptionUnavailable(RuntimeError):
    """Raised when no engine is configured — surfaced honestly, never faked."""


class OpenAICompatTranscription:
    """Whisper-class transcription via any OpenAI-compatible ``audio/transcriptions`` endpoint."""

    def transcribe(self, audio: bytes, filename: str) -> TranscriptResult:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
        buffer = io.BytesIO(audio)
        buffer.name = filename  # the SDK reads the extension for format detection
        response = client.audio.transcriptions.create(
            model=settings.transcribe_model,
            file=buffer,
            response_format="verbose_json",
        )
        raw_segments = getattr(response, "segments", None) or []
        segments = [
            Segment(
                start=float(getattr(s, "start", 0.0)),
                end=float(getattr(s, "end", 0.0)),
                text=str(getattr(s, "text", "")).strip(),
            )
            for s in raw_segments
        ]
        text = getattr(response, "text", "") or " ".join(s.text for s in segments)
        if not segments and text:  # some backends omit segments — keep the transcript usable
            segments = [Segment(start=0.0, end=0.0, text=text)]
        return TranscriptResult(
            segments=segments, text=text, language=str(getattr(response, "language", "") or "")
        )


def get_engine() -> TranscriptionEngine:
    provider = settings.transcribe_provider.lower()
    if provider == "openai":
        return OpenAICompatTranscription()
    raise TranscriptionUnavailable(
        "transcription is not configured — set TRANSCRIBE_PROVIDER=openai (and an API key) "
        "or plug in another engine"
    )


__all__ = [
    "Segment",
    "TranscriptResult",
    "TranscriptionEngine",
    "TranscriptionUnavailable",
    "OpenAICompatTranscription",
    "get_engine",
]
