"""Media helpers — ffmpeg-gated probing/extraction (graceful when ffmpeg is absent).

Same gating philosophy as the ``ocr`` package: capability is detected, never assumed. Audio files
flow through untouched without ffmpeg; video needs ffmpeg to extract an audio track and fails with
a clear, actionable error when it is missing.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".mkv", ".avi"})
FFMPEG_TIMEOUT_S = 300


@lru_cache(maxsize=1)
def ffmpeg_available() -> bool:
    available = shutil.which("ffmpeg") is not None
    if not available:
        log.info("ffmpeg not found on PATH — video extraction disabled, audio passes through")
    return available


def media_kind(filename: str) -> str:
    """Classify by extension: 'audio' | 'video' | 'other'."""
    ext = Path(filename).suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "other"


def extract_audio(data: bytes, filename: str) -> tuple[bytes, str]:
    """Return ``(audio_bytes, audio_filename)`` ready for transcription.

    Audio inputs pass through unchanged. Video inputs are converted to mono 16k mp3 via ffmpeg;
    raises ``RuntimeError`` with a clear message when ffmpeg is unavailable or fails.
    """
    kind = media_kind(filename)
    if kind == "audio":
        return data, filename
    if kind != "video":
        raise RuntimeError(f"unsupported media type: {filename!r}")
    if not ffmpeg_available():
        raise RuntimeError(
            "video files need ffmpeg to extract the audio track — install ffmpeg or upload the "
            "audio file directly"
        )

    suffix = Path(filename).suffix
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"in{suffix}"
        dst = Path(tmp) / "out.mp3"
        src.write_bytes(data)
        cmd = ["ffmpeg", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(dst)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=FFMPEG_TIMEOUT_S)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode(errors="replace")[-400:]
            log.warning("ffmpeg extraction failed for %s: %s", filename, stderr)
            raise RuntimeError(f"audio extraction failed: {stderr}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("audio extraction timed out") from exc
        return dst.read_bytes(), Path(filename).stem + ".mp3"


__all__ = ["AUDIO_EXTENSIONS", "VIDEO_EXTENSIONS", "ffmpeg_available", "media_kind", "extract_audio"]
