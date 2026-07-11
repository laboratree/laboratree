"""Deliverables Studio API — compose Evidence-bound reports, render, and share (read-only).

Block saves are validated against the project's real Evidence: a stat/table/chart/quote block that
cites an unknown evidence id is rejected (U1). Public share pages render read-only HTML by token.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import cache_key, cached_json
from ..core.config import settings
from ..core.db.postgres import get_session
from ..core.deps import Principal, PrincipalDep, SessionDep, require_role
from ..core.ratelimit import check_rate_limit
from ..deliverables.models import Report
from ..labs.deliverables import render_html, validate_blocks
from ..projects.models import Evidence, Project, Run
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["deliverables"])
public_router = APIRouter(prefix="/public", tags=["public-report"])

SHARE_TOKEN_BYTES = 24


class ReportOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    blocks: list[dict[str, Any]]
    share_token: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportPatchIn(BaseModel):
    title: str | None = None
    blocks: list[dict[str, Any]] | None = None


class EvidenceItem(BaseModel):
    id: uuid.UUID
    label: str
    kind: str
    value: Any
    run_id: uuid.UUID | None


async def _require_project(session: SessionDep, principal: Principal, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


async def _require_report(session: SessionDep, principal: Principal, report_id: uuid.UUID) -> Report:
    report = await session.get(Report, report_id)
    if report is None or report.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="report not found")
    return report


async def _project_evidence(
    session: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> list[Evidence]:
    run_ids = (
        await session.execute(
            select(Run.id).where(Run.project_id == project_id, Run.org_id == org_id)
        )
    ).scalars().all()
    if not run_ids:
        return []
    return list(
        (
            await session.execute(
                select(Evidence).where(Evidence.run_id.in_(run_ids)).order_by(Evidence.created_at)
            )
        ).scalars().all()
    )


def _evidence_map(rows: list[Evidence]) -> dict[str, dict[str, Any]]:
    return {
        str(e.id): {"label": e.label, "kind": e.kind,
                    "value": (e.value or {}).get("v"), "run_id": str(e.run_id) if e.run_id else None}
        for e in rows
    }


# ----------------------------- CRUD -----------------------------

@router.post("/projects/{project_id}/reports", response_model=ReportOut, status_code=201)
async def create_report(
    project_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Report:
    await _require_project(session, principal, project_id)
    report = Report(org_id=principal.org_id, project_id=project_id,
                    title="Untitled report", blocks=[])
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.get("/projects/{project_id}/reports", response_model=list[ReportOut])
async def list_reports(
    project_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[Report]:
    await _require_project(session, principal, project_id)
    rows = (
        await session.execute(
            select(Report).where(Report.org_id == principal.org_id,
                                 Report.project_id == project_id).order_by(Report.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(report_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> Report:
    return await _require_report(session, principal, report_id)


@router.get("/projects/{project_id}/evidence", response_model=list[EvidenceItem])
async def evidence_picker(
    project_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[dict[str, Any]]:
    """All Evidence across the project's runs — the source for numeric/quote/table/chart blocks.

    Cached briefly (org-scoped key): the picker is re-fetched on every editor load while its
    contents only change when a run finishes.
    """
    await _require_project(session, principal, project_id)

    async def _compute() -> list[dict[str, Any]]:
        rows = await _project_evidence(session, project_id, principal.org_id)
        return [
            {"id": str(e.id), "label": e.label, "kind": e.kind,
             "value": (e.value or {}).get("v"),
             "run_id": str(e.run_id) if e.run_id else None}
            for e in rows
        ]

    key = cache_key("evidence-picker", project_id, principal.org_id)
    return await cached_json(key, settings.evidence_cache_ttl_s, _compute)


@router.patch("/reports/{report_id}", response_model=ReportOut)
async def patch_report(
    report_id: uuid.UUID,
    body: ReportPatchIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Report:
    report = await _require_report(session, principal, report_id)
    if body.title is not None:
        report.title = body.title
    if body.blocks is not None:
        rows = await _project_evidence(session, report.project_id, principal.org_id)
        valid_ids = {str(e.id) for e in rows}
        errors = validate_blocks(body.blocks, valid_ids)
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})
        report.blocks = body.blocks
    await session.commit()
    await session.refresh(report)
    return report


# ----------------------------- render + share -----------------------------

async def _render(session: AsyncSession, report: Report, org_id: uuid.UUID) -> str:
    rows = await _project_evidence(session, report.project_id, org_id)
    return render_html(report.title, report.blocks or [], _evidence_map(rows))


@router.get("/reports/{report_id}/render", response_class=HTMLResponse)
async def render_report(
    report_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> str:
    report = await _require_report(session, principal, report_id)
    return await _render(session, report, principal.org_id)


@router.post("/reports/{report_id}/share")
async def share_report(
    report_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, str]:
    report = await _require_report(session, principal, report_id)
    if report.share_token is None:
        report.share_token = secrets.token_urlsafe(SHARE_TOKEN_BYTES)
    await session.commit()
    return {"token": report.share_token, "path": f"/r/{report.share_token}"}


@router.post("/reports/{report_id}/unshare")
async def unshare_report(
    report_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, str]:
    report = await _require_report(session, principal, report_id)
    report.share_token = None
    await session.commit()
    return {"status": "revoked"}


@public_router.get("/reports/{token}", response_class=HTMLResponse)
async def public_report(
    token: str,
    request_session: Annotated[AsyncSession, Depends(get_session)],
) -> str:
    """Public read-only render of a shared report (token = authorization, rate-limited)."""
    allowed, retry = await check_rate_limit(f"rl:pub:report:{token[:8]}", 120, 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"retry in {retry}s")
    report = (
        await request_session.execute(select(Report).where(Report.share_token == token))
    ).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="this report link is not valid")
    return await _render(request_session, report, report.org_id)


__all__ = ["router", "public_router"]
