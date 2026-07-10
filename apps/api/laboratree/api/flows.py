"""Flow orchestration API — run a whole pipeline template, each phase as a sub-agent."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..agents import flow as flow_engine
from ..agents.flow import scenarios  # noqa: F401 — importing registers every scenario's executors
from ..core.deps import Principal, SessionDep, require_role
from ..projects.models import Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["flows"])

# canonical stage order per flow (the frontend may send its own, possibly edited, order)
DEFAULT_STAGES: dict[str, list[str]] = {
    "ngo-policy": [
        "intake", "stakeholders", "background", "questions", "hypotheses",
        "design", "personas", "questionnaire", "field",
        "clean", "eda", "crosstab", "model",
        "prioritize", "intervention", "pilot",
        "impact", "recommend", "monitor",
    ],
}

MAX_STAGES = 40


class FlowRunIn(BaseModel):
    stages: list[str] | None = Field(default=None, max_length=MAX_STAGES)


@router.get("/flows")
async def list_flows() -> dict[str, Any]:
    return {
        "flows": [
            {"key": key, "stages": stages,
             "executors": flow_engine.registered_stages(key)}
            for key, stages in DEFAULT_STAGES.items()
        ]
    }


@router.post("/projects/{project_id}/flows/{flow_key}/run")
async def run_flow(
    project_id: uuid.UUID,
    flow_key: str,
    body: FlowRunIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Orchestrated run: dispatch every phase to its executor, open gates for human stages."""
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    if flow_key not in DEFAULT_STAGES:
        raise HTTPException(status_code=422, detail=f"unknown flow: {flow_key}")

    stage_ids = body.stages or DEFAULT_STAGES[flow_key]
    report = await flow_engine.run_flow(
        session, org_id=principal.org_id, project_id=project_id,
        flow_key=flow_key, stage_ids=stage_ids,
    )
    log.info("orchestrated flow %s on project %s: %s (%d stages, %d gates)",
             flow_key, project_id, report["status"], len(report["stages"]),
             report["gates_opened"])
    return report
