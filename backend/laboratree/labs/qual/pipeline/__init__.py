"""Transcription pipeline: blob → (extract audio) → engine → Mongo transcript → asset status.

Runs as a FastAPI background task today (a Celery task can wrap the same function later — the
pipeline is a plain async function with an injectable engine, so the execution host is a detail).
Failures never crash silently: the asset lands in FAILED with the reason on the row.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict

from ....core.db.postgres import sessionmaker
from ....core.media import extract_audio
from ....core.storage import get_blob_store
from ....core.transcribe import TranscriptionEngine
from ....media.models import MediaAsset, MediaStatus
from ..transcripts import save_transcript

log = logging.getLogger(__name__)


async def run_transcription(asset_id: uuid.UUID, engine: TranscriptionEngine) -> None:
    """Transcribe one MediaAsset end-to-end, updating its status as it goes."""
    async with sessionmaker()() as session:
        asset = await session.get(MediaAsset, asset_id)
        if asset is None:
            log.warning("transcription skipped: asset %s not found", asset_id)
            return
        asset.status = MediaStatus.PROCESSING
        await session.commit()

        try:
            data = get_blob_store().get(asset.storage_key)
            audio, audio_name = extract_audio(data, asset.filename or "audio.mp3")
            result = engine.transcribe(audio, audio_name)
            segments = [asdict(s) for s in result.segments]
            await save_transcript(
                asset.id, asset.org_id,
                segments=segments, text=result.text, language=result.language,
            )
            asset.status = MediaStatus.TRANSCRIBED
            asset.language = result.language or ""
            if segments:
                asset.duration_seconds = float(segments[-1].get("end") or 0.0) or None
            asset.error = ""
            log.info("asset %s transcribed: %d segments, lang=%s",
                     asset.id, len(segments), result.language or "?")
        except Exception as exc:  # any failure -> honest FAILED state, reason stored
            log.warning("transcription failed for asset %s: %s", asset_id, exc)
            asset.status = MediaStatus.FAILED
            asset.error = str(exc)[:2000]
        await session.commit()


__all__ = ["run_transcription"]
