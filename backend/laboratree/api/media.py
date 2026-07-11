"""Qual Studio media API — upload/record audio-video, track transcription, read/correct transcripts.

Uploads kick off the transcription pipeline as a background task (the engine is resolved at
request time so tests inject a fake via ``labs.qual.engine_factory``-style monkeypatching of
``core.transcribe.get_engine``). Status is polled on the asset row.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from ..core import transcribe as transcribe_core
from ..core.deps import Principal, PrincipalDep, SessionDep, require_role
from ..core.media import media_kind
from ..core.storage import get_blob_store
from ..core.transcribe import TranscriptionUnavailable
from ..labs.qual.pipeline import run_transcription
from ..labs.qual.transcripts import get_transcript, update_segment_text
from ..media.models import MediaAsset, MediaStatus
from ..projects.models import Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["media"])

MAX_MEDIA_BYTES = 200 * 1024 * 1024  # 200 MB cap per upload

CONTENT_TYPES = {
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg",
    ".webm": "audio/webm", ".flac": "audio/flac", ".aac": "audio/aac",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".mkv": "video/x-matroska",
}


class MediaOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    kind: str
    status: str
    duration_seconds: float | None
    language: str
    error: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SegmentEditIn(BaseModel):
    index: int
    text: str


async def _require_project(
    session: SessionDep, principal: Principal, project_id: uuid.UUID
) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


async def _require_asset(
    session: SessionDep, principal: Principal, asset_id: uuid.UUID
) -> MediaAsset:
    asset = await session.get(MediaAsset, asset_id)
    if asset is None or asset.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="media asset not found")
    return asset


@router.post("/projects/{project_id}/media", response_model=MediaOut, status_code=201)
async def upload_media(
    project_id: uuid.UUID,
    background: BackgroundTasks,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
    file: Annotated[UploadFile, File(...)],
    source: str = "upload",
) -> MediaAsset:
    await _require_project(session, principal, project_id)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    if len(data) > MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds the 200 MB limit")
    filename = file.filename or "recording.webm"
    kind = media_kind(filename)
    if kind == "other":
        raise HTTPException(status_code=422, detail=f"unsupported media type: {filename}")

    key = f"media/{project_id}/{uuid.uuid4()}/{filename}"
    get_blob_store().put(key, data)
    asset = MediaAsset(
        org_id=principal.org_id,
        project_id=project_id,
        filename=filename,
        kind=kind,
        storage_key=key,
        status=MediaStatus.UPLOADED,
        source=source if source in ("upload", "recording", "survey") else "upload",
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)

    try:
        engine = transcribe_core.get_engine()
        background.add_task(run_transcription, asset.id, engine)
    except TranscriptionUnavailable as exc:
        asset.status = MediaStatus.FAILED
        asset.error = str(exc)
        await session.commit()
        await session.refresh(asset)
    log.info("media asset %s uploaded (%s, %d bytes)", asset.id, kind, len(data))
    return asset


@router.get("/projects/{project_id}/media", response_model=list[MediaOut])
async def list_media(
    project_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[MediaAsset]:
    await _require_project(session, principal, project_id)
    rows = (
        await session.execute(
            select(MediaAsset)
            .where(MediaAsset.org_id == principal.org_id, MediaAsset.project_id == project_id)
            .order_by(MediaAsset.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/media/{asset_id}")
async def get_media(
    asset_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    asset = await _require_asset(session, principal, asset_id)
    transcript = await get_transcript(asset.id, principal.org_id)
    return {
        "asset": MediaOut.model_validate(asset).model_dump(mode="json"),
        "transcript": transcript,
    }


@router.get("/media/{asset_id}/file")
async def download_media(
    asset_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> Response:
    asset = await _require_asset(session, principal, asset_id)
    data = get_blob_store().get(asset.storage_key)
    ext = "." + asset.filename.rsplit(".", 1)[-1].lower() if "." in asset.filename else ""
    return Response(
        content=data,
        media_type=CONTENT_TYPES.get(ext, "application/octet-stream"),
        headers={"Content-Disposition": f'inline; filename="{asset.filename}"'},
    )


@router.patch("/media/{asset_id}/transcript")
async def correct_segment(
    asset_id: uuid.UUID,
    body: SegmentEditIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, str]:
    await _require_asset(session, principal, asset_id)
    ok = await update_segment_text(asset_id, principal.org_id, body.index, body.text)
    if not ok:
        raise HTTPException(status_code=404, detail="transcript segment not found")
    return {"status": "corrected"}


@router.post("/media/{asset_id}/retry", response_model=MediaOut)
async def retry_transcription(
    asset_id: uuid.UUID,
    background: BackgroundTasks,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> MediaAsset:
    asset = await _require_asset(session, principal, asset_id)
    if asset.status not in (MediaStatus.FAILED, MediaStatus.TRANSCRIBED):
        raise HTTPException(status_code=409, detail="asset is still processing")
    try:
        engine = transcribe_core.get_engine()
    except TranscriptionUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    asset.status = MediaStatus.UPLOADED
    asset.error = ""
    await session.commit()
    await session.refresh(asset)
    background.add_task(run_transcription, asset.id, engine)
    return asset
