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
from ..projects.models import AgentRun, Artifact, BlobNote, Project, Run
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


def _lab_for_key(key: str) -> str:
    """Infer the producing Lab from a blob key's prefix convention."""
    parts = key.split("/")
    if parts[0] == "spiderweb":
        return "spiderweb"
    if parts[0] == "media":
        return "qual"
    if parts[0] == "flows":
        stage = parts[2] if len(parts) > 3 else ""
        return stage.removeprefix("lab-") if stage.startswith("lab-") else "pipeline"
    return parts[0]


def _group_ref(entry: dict[str, Any]) -> tuple[str, str]:
    """Which task produced this artifact? Returns (group_id, prefix_type).

    The producing run/mission is encoded in the blob key prefix, so a chat run's whole output
    collapses into ONE task card instead of scattering as loose files.
    """
    key = entry["key"]
    parts = key.split("/")
    if entry["origin"] == "run":
        return f"run:{entry['run_id']}", "component"
    if parts[0] == "spiderweb" and len(parts) > 1:
        return f"agent:{parts[1]}", "spiderweb"
    if parts[0] == "flows" and len(parts) > 1:
        return f"run:{parts[1]}", "flows"
    if parts[0] == "media" and len(parts) > 2:
        return f"media:{parts[2]}", "media"
    return f"misc:{parts[0]}", "other"


@router.get("/projects/{project_id}/artifact-store")
async def artifact_store(
    project_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
    lab: str | None = None,
) -> dict[str, Any]:
    """Everything the project's labs and agents produced, GROUPED by the task that produced it.

    Each group is one run/mission/chat/flow — labelled by its objective — so the store reads as a
    list of tasks with their outputs, not a flat dump. A chatbot run is a ``chat`` task (not a
    standalone ``mission``); only SpiderWeb digs are missions.
    """
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")

    entries: list[dict[str, Any]] = []
    notes = (await session.execute(
        select(BlobNote).where(BlobNote.org_id == principal.org_id,
                               BlobNote.project_id == project_id)
        .order_by(BlobNote.created_at.desc()).limit(600)
    )).scalars().all()
    entries.extend({
        "origin": "blob", "key": n.key, "name": n.key.rsplit("/", 1)[-1],
        "kind": n.kind, "size": n.size, "description": n.description,
        "source": n.source, "created_at": str(n.created_at),
    } for n in notes)

    rows = (await session.execute(
        select(Artifact).join(Run, Artifact.run_id == Run.id)
        .where(Artifact.org_id == principal.org_id, Run.project_id == project_id)
        .order_by(Artifact.created_at.desc()).limit(600)
    )).scalars().all()
    entries.extend({
        "origin": "run", "artifact_id": str(a.id), "run_id": str(a.run_id), "key": a.storage_key,
        "name": a.name, "kind": a.kind, "size": a.size or 0, "description": a.name,
        "source": "", "created_at": str(a.created_at),
    } for a in rows)

    grouped = await _build_task_groups(session, principal.org_id, entries)
    if lab:
        grouped = [g for g in grouped if g["lab"] == lab]
    labs = sorted({g["lab"] for g in grouped if g["lab"]})
    return {"groups": grouped[:200], "labs": labs, "total_tasks": len(grouped)}


async def _build_task_groups(session, org_id: uuid.UUID,
                             entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket artifacts by producing task, then label each task from its Run/AgentRun."""
    buckets: dict[str, dict[str, Any]] = {}
    for e in entries:
        gid, prefix = _group_ref(e)
        bucket = buckets.setdefault(gid, {"prefix": prefix, "artifacts": [], "created_at": ""})
        bucket["artifacts"].append(e)
        bucket["created_at"] = max(bucket["created_at"], e["created_at"])

    # batch-resolve the labels/kinds from the owning rows
    agent_ids = [g.split(":", 1)[1] for g in buckets if g.startswith("agent:")]
    run_ids = [g.split(":", 1)[1] for g in buckets if g.startswith("run:")]
    agent_runs = await _fetch_by_ids(session, AgentRun, agent_ids)
    runs = await _fetch_by_ids(session, Run, run_ids)

    groups: list[dict[str, Any]] = []
    for gid, bucket in buckets.items():
        kind, ref_id = gid.split(":", 1)
        label, task_kind, lab = _label_group(kind, ref_id, bucket["prefix"],
                                              agent_runs, runs, bucket["artifacts"])
        bucket["artifacts"].sort(key=lambda a: a["created_at"], reverse=True)
        groups.append({
            "task_id": ref_id, "task_kind": task_kind, "lab": lab, "label": label,
            "created_at": bucket["created_at"], "count": len(bucket["artifacts"]),
            "artifacts": bucket["artifacts"],
        })
    groups.sort(key=lambda g: g["created_at"], reverse=True)
    return groups


async def _fetch_by_ids(session, model, ids: list[str]) -> dict[str, Any]:
    uuids = []
    for i in ids:
        try:
            uuids.append(uuid.UUID(i))
        except ValueError:
            continue
    if not uuids:
        return {}
    rows = (await session.execute(select(model).where(model.id.in_(uuids)))).scalars().all()
    return {str(r.id): r for r in rows}


def _label_group(kind, ref_id, prefix, agent_runs, runs, artifacts) -> tuple[str, str, str]:
    if kind == "agent":
        ar = agent_runs.get(ref_id)
        if ar is not None:
            is_mission = ar.lab == "spiderweb"
            return ((ar.task or "").strip()[:120] or "untitled",
                    "mission" if is_mission else "chat", ar.lab or "")
        return "SpiderWeb mission", "mission", "spiderweb"
    if kind == "run":
        run = runs.get(ref_id)
        if run is not None:
            if run.kind == "agent":
                task = (run.params or {}).get("task", "") if isinstance(run.params, dict) else ""
                return (str(task).strip()[:120] or f"{run.lab} agent", "chat", run.lab or "")
            if run.kind == "flow":
                return (f"Flow run · {str(run.id)[:8]}", "flow",
                        _lab_for_key(artifacts[0]["key"]))
            return (run.component_id or "component run", "run", run.lab or "")
        return (f"Flow run · {ref_id[:8]}", "flow", _lab_for_key(artifacts[0]["key"]))
    if kind == "media":
        return (artifacts[0]["name"], "media", "qual")
    return (ref_id, "other", _lab_for_key(artifacts[0]["key"]))


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
    media = _MEDIA_BY_EXT.get("." + filename.rsplit(".", 1)[-1].lower(), "text/plain")
    # PDFs render inline (the user wants to READ the paper); the rest download
    disposition = "inline" if media == "application/pdf" else "attachment"
    return Response(content=body, media_type=media, headers={
        "Content-Disposition": f'{disposition}; filename="{filename}"'})


_MEDIA_BY_EXT = {
    ".json": "application/json", ".pdf": "application/pdf", ".html": "text/html",
    ".csv": "text/csv", ".txt": "text/plain",
}
