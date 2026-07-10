"""Flow orchestration API — run a whole pipeline template, each phase as a sub-agent."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..agents import flow as flow_engine
from ..agents import supervisor
from ..agents.flow import scenarios  # noqa: F401 — importing registers every scenario's executors
from ..core.deps import Principal, SessionDep, require_role
from ..projects.models import Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["flows"])

# canonical stage order per flow (the frontend may send its own, possibly edited, order)
_POLICY_STAGES = [
    "intake", "stakeholders", "background", "questions", "hypotheses",
    "design", "personas", "questionnaire", "field",
    "clean", "eda", "crosstab", "model",
    "prioritize", "intervention", "pilot",
    "impact", "recommend", "monitor",
]

DEFAULT_STAGES: dict[str, list[str]] = {
    # the three use-case flows; stages without executors are DeepAgent phases
    "research": [
        "intake", "literature", "hypotheses", "design", "personas", "questionnaire",
        "field", "clean", "eda", "crosstab", "model", "recommend", "monitor",
    ],
    "policy-research": _POLICY_STAGES,
    "market-research": [
        "intake", "market-sizing", "competitor-scan", "trend-scan",
        "design", "questionnaire", "field", "clean", "eda",
        "segmentation", "pricing-analysis", "prioritize", "recommend", "monitor",
    ],
    "ngo-policy": _POLICY_STAGES,  # legacy alias of policy-research (old canvases keep working)
}

# default DeepAgent objectives per flow's uncovered stages (overridable per request)
DEFAULT_OBJECTIVES: dict[str, dict[str, str]] = {
    "research": {
        "literature": "Survey the scholarly literature for this project's topic: find the most "
                      "relevant papers (research_search/arxiv_search), synthesize what is known, "
                      "and cite every claim to a specific source.",
    },
    "market-research": dict(scenarios.market_research.DEEP_STAGES),
}

MAX_STAGES = 40


class FlowRunIn(BaseModel):
    stages: list[str] | None = Field(default=None, max_length=MAX_STAGES)


class SuperviseIn(BaseModel):
    stages: list[str] | None = Field(default=None, max_length=MAX_STAGES)
    # stage_id -> objective text; used when the DeepAgent must fulfil an uncovered stage
    objectives: dict[str, str] = Field(default_factory=dict)


class ResumeIn(BaseModel):
    approved: bool
    note: str = Field(default="", max_length=500)


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


@router.post("/projects/{project_id}/flows/{flow_key}/supervise")
async def supervise_flow(
    project_id: uuid.UUID,
    flow_key: str,
    body: SuperviseIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Supervised (durable) run: lab agents per stage, DeepAgent for gaps, gates pause the graph."""
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    if flow_key not in DEFAULT_STAGES:
        raise HTTPException(status_code=422, detail=f"unknown flow: {flow_key}")
    objectives = {**DEFAULT_OBJECTIVES.get(flow_key, {}), **body.objectives}
    return await supervisor.supervise(
        session, org_id=principal.org_id, project_id=project_id, flow_key=flow_key,
        stage_ids=body.stages or DEFAULT_STAGES[flow_key], objectives=objectives,
    )


@router.get("/flows/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    state = await supervisor.thread_state(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail="unknown supervised run")
    return state


@router.post("/flows/threads/{thread_id}/resume")
async def resume_thread(
    thread_id: str,
    body: ResumeIn,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Deliver the human's gate decision and continue the supervised run."""
    state = await supervisor.thread_state(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail="unknown supervised run")
    if state["status"] != "paused":
        raise HTTPException(status_code=409, detail="this run is not waiting on a gate")
    return await supervisor.resume(thread_id, approved=body.approved, note=body.note)
