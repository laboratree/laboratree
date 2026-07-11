"""Lab-agent API — conversational chat per Lab + job-style agent runs polled live."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ..agents.lab_agent import LAB_AGENTS, chat_turn, execute_agent_run, list_threads
from ..core.db.postgres import sessionmaker
from ..core.deps import Principal, SessionDep, require_role
from ..core.ratelimit import rate_limited
from ..projects.models import AgentRun, LLMCall, Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["lab-agents"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None


async def _require_project(session, principal, project_id) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


async def _run_agent_job(agent_run_id: uuid.UUID) -> None:
    """Background body — its own session (the request's session is closed by then)."""
    async with sessionmaker()() as session:
        await execute_agent_run(session, agent_run_id)


@router.post("/projects/{project_id}/labs/{lab}/chat",
             dependencies=[rate_limited("lab_agent", limit=20)])
async def lab_chat(
    project_id: uuid.UUID,
    lab: str,
    body: ChatIn,
    background: BackgroundTasks,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    await _require_project(session, principal, project_id)
    if lab not in LAB_AGENTS:
        raise HTTPException(status_code=422, detail=f"unknown lab agent: {lab}")
    reply, queued_run_id = await chat_turn(
        session, org_id=principal.org_id, project_id=project_id,
        lab=lab, thread_id=body.thread_id, message=body.message,
    )
    if queued_run_id is not None:
        background.add_task(_run_agent_job, queued_run_id)
    return {"thread_id": reply.thread_id, "reply": reply.reply,
            "agent_run_id": reply.agent_run_id, "flow_ops": reply.flow_ops}


@router.get("/projects/{project_id}/agent-runs/{agent_run_id}")
async def get_agent_run(
    project_id: uuid.UUID,
    agent_run_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Live state for polling: steps as they land, findings, cost rollup."""
    agent_run = await session.get(AgentRun, agent_run_id)
    if (agent_run is None or agent_run.org_id != principal.org_id
            or agent_run.project_id != project_id):
        raise HTTPException(status_code=404, detail="unknown agent run")
    tokens, cost = (await session.execute(
        select(func.coalesce(func.sum(LLMCall.total_tokens), 0),
               func.coalesce(func.sum(LLMCall.cost_usd), 0.0))
        .where(LLMCall.operation == f"agent-run:{agent_run.id}")
    )).one()
    return {
        "id": str(agent_run.id), "lab": agent_run.lab, "task": agent_run.task,
        "status": agent_run.status.value, "steps": agent_run.steps,
        "findings": agent_run.findings, "summary": agent_run.summary,
        "run_id": str(agent_run.run_id) if agent_run.run_id else None,
        "trace_key": agent_run.trace_key,
        "llm_calls": agent_run.llm_calls_used,
        "tokens": int(tokens or 0), "cost_usd": float(cost or 0.0),
    }


@router.get("/projects/{project_id}/labs/{lab}/threads")
async def lab_threads(
    project_id: uuid.UUID,
    lab: str,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> list[dict[str, Any]]:
    await _require_project(session, principal, project_id)
    threads = await list_threads(session, principal.org_id, project_id, lab)
    return [{"id": str(t.id), "messages": t.messages, "updated_at": str(t.updated_at)}
            for t in threads]
