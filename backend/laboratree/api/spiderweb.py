"""SpiderWeb API — delegate web-extraction missions, poll them live, resume stopped ones."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select

from ..core.db.postgres import sessionmaker
from ..core.deps import Principal, SessionDep, require_role
from ..core.ratelimit import rate_limited
from ..labs.spiderweb import MissionSpec, canonical, run_mission
from ..projects.models import AgentRun, AgentRunStatus, Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["spiderweb"])


async def _mission_job(agent_run_id: uuid.UUID) -> None:
    async with sessionmaker()() as session:
        await run_mission(session, agent_run_id)


@router.post("/projects/{project_id}/spiderweb/missions",
             dependencies=[rate_limited("spider", limit=5)])
async def create_mission(
    project_id: uuid.UUID,
    spec: MissionSpec,
    background: BackgroundTasks,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    agent_run = AgentRun(
        org_id=principal.org_id, project_id=project_id, lab="spiderweb",
        task=spec.objective, status=AgentRunStatus.QUEUED,
        frontier={"spec": spec.model_dump(),
                  "queue": [[canonical(u), 0] for u in spec.seed_urls]},
    )
    session.add(agent_run)
    await session.commit()
    background.add_task(_mission_job, agent_run.id)
    return {"agent_run_id": str(agent_run.id)}


@router.get("/projects/{project_id}/spiderweb/missions")
async def list_missions(
    project_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> list[dict[str, Any]]:
    rows = (await session.execute(
        select(AgentRun).where(AgentRun.org_id == principal.org_id,
                               AgentRun.project_id == project_id,
                               AgentRun.lab == "spiderweb")
        .order_by(AgentRun.created_at.desc()).limit(25)
    )).scalars().all()
    return [{
        "id": str(r.id), "objective": r.task, "status": r.status.value,
        "pages": len((r.frontier or {}).get("visited", [])),
        "items": len((r.frontier or {}).get("records", [])),
        "summary": r.summary,
    } for r in rows]


@router.post("/projects/{project_id}/spiderweb/missions/{agent_run_id}/resume")
async def resume_mission(
    project_id: uuid.UUID,
    agent_run_id: uuid.UUID,
    background: BackgroundTasks,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Continue a stopped/failed mission from its persisted frontier."""
    agent_run = await session.get(AgentRun, agent_run_id)
    if (agent_run is None or agent_run.org_id != principal.org_id
            or agent_run.project_id != project_id or agent_run.lab != "spiderweb"):
        raise HTTPException(status_code=404, detail="unknown mission")
    if agent_run.status == AgentRunStatus.SUCCEEDED:
        raise HTTPException(status_code=409, detail="mission already completed")
    agent_run.status = AgentRunStatus.QUEUED
    await session.commit()
    background.add_task(_mission_job, agent_run.id)
    return {"agent_run_id": str(agent_run.id), "status": "resumed"}
