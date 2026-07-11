"""Storage visibility — browse a flow's per-stage buckets and download owned blobs.

Access law: a blob is downloadable ONLY when its key resolves to something the caller's org
owns — a flow/agent Run's bucket prefix or a catalogued BlobNote. No raw key access.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from ..core.deps import Principal, SessionDep, require_role
from ..core.storage import get_blob_store
from ..projects.models import AgentRun, BlobNote, Run
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["storage"])

MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024


@router.get("/flows/runs/{flow_run_id}/storage")
async def flow_run_storage(
    flow_run_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Per-stage bucket listing for one flow run (org-checked via the Run row)."""
    run = await session.get(Run, flow_run_id)
    if run is None or run.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="unknown flow run")
    blobs = get_blob_store().list(f"flows/{flow_run_id}/")
    stages: dict[str, list[dict[str, Any]]] = {}
    for blob in blobs:
        parts = blob["key"].split("/")
        stage = parts[2] if len(parts) > 3 else "(root)"
        stages.setdefault(stage, []).append(blob)
    return {"flow_run_id": str(flow_run_id), "stages": stages,
            "total_files": len(blobs), "total_bytes": sum(b["size"] for b in blobs)}


async def _org_owns_key(session, org_id: uuid.UUID, key: str) -> bool:
    parts = key.split("/")
    try:
        if parts[0] == "flows" and len(parts) > 2:
            run = await session.get(Run, uuid.UUID(parts[1]))
            return run is not None and run.org_id == org_id
        if parts[0] in ("lab-agents", "spiderweb") and len(parts) > 2:
            agent_run = await session.get(AgentRun, uuid.UUID(parts[1]))
            return agent_run is not None and agent_run.org_id == org_id
    except (ValueError, IndexError):
        pass
    note = (await session.execute(
        select(BlobNote).where(BlobNote.org_id == org_id, BlobNote.key == key)
    )).scalar_one_or_none()
    return note is not None


@router.get("/blobs/download")
async def download_blob(
    key: str,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Response:
    if not await _org_owns_key(session, principal.org_id, key):
        raise HTTPException(status_code=403, detail="blob not accessible")
    try:
        body = get_blob_store().get(key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="blob not found") from exc
    if len(body) > MAX_DOWNLOAD_BYTES:
        raise HTTPException(status_code=413, detail="blob too large for download")
    filename = key.rsplit("/", 1)[-1]
    media = "application/json" if filename.endswith(".json") else "text/plain"
    return Response(content=body, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{filename}"'})
