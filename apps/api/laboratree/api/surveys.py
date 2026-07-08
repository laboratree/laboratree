"""Field Lab admin API — design, publish, monitor, and export a survey (auth + org-scoped).

The respondent-facing runtime lives in ``api/public_survey.py`` (no auth). Survey structure and
skip-logic are validated by the pure ``labs.fieldwork.runtime`` evaluator before anything is
published.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..core.deps import Principal, PrincipalDep, SessionDep, require_role
from ..core.llm.context import use_llm_context
from ..core.repro import dataframe_hash
from ..core.storage import get_blob_store
from ..fieldwork.models import Quota, ResponseStatus, Survey, SurveyResponse, SurveyStatus
from ..labs.fieldwork.director import analyze_field
from ..labs.fieldwork.runtime import (
    ordered_qids,
    validate_structure,
    visible_path,
)
from ..labs.synth import llm as synth_llm
from ..labs.synth.personas import build_personas
from ..labs.synth.twin import aggregate_dry_run, simulate_persona
from ..projects.models import Dataset, Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["surveys"])

PUBLIC_TOKEN_BYTES = 24


# ----------------------------- schemas -----------------------------

class QuotaOut(BaseModel):
    id: uuid.UUID
    name: str
    conditions: list[dict[str, Any]]
    target: int
    current: int

    model_config = {"from_attributes": True}


class SurveyOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    status: str
    structure: dict[str, Any]
    prereg: dict[str, Any] = {}
    version: int
    public_token: str | None
    quotas: list[QuotaOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class PreregIn(BaseModel):
    hypotheses: str = ""
    planned_analyses: list[str] = []


class SurveyCreateIn(BaseModel):
    title: str = ""
    structure: dict[str, Any] = {}


class SurveyPatchIn(BaseModel):
    title: str | None = None
    structure: dict[str, Any] | None = None


class QuotaIn(BaseModel):
    name: str = ""
    conditions: list[dict[str, Any]] = []
    target: int = 0


class TwinDryRunIn(BaseModel):
    n: int = 25
    margins: dict[str, dict[str, float]] = {}


# ----------------------------- helpers -----------------------------

async def _require_project(
    session: SessionDep, principal: Principal, project_id: uuid.UUID
) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


async def _require_survey(
    session: SessionDep, principal: Principal, survey_id: uuid.UUID
) -> Survey:
    survey = await session.get(Survey, survey_id)
    if survey is None or survey.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="survey not found")
    return survey


def _validate_or_422(structure: dict[str, Any]) -> None:
    errors = validate_structure(structure or {})
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})


def _structure_hash(structure: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(structure, sort_keys=True).encode()).hexdigest()


# ----------------------------- CRUD -----------------------------

@router.post("/projects/{project_id}/surveys", response_model=SurveyOut, status_code=201)
async def create_survey(
    project_id: uuid.UUID,
    body: SurveyCreateIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Survey:
    await _require_project(session, principal, project_id)
    if body.structure:
        _validate_or_422(body.structure)
    survey = Survey(
        org_id=principal.org_id,
        project_id=project_id,
        title=body.title,
        structure=body.structure or {"sections": [], "logic": []},
        status=SurveyStatus.DRAFT,
    )
    session.add(survey)
    await session.commit()
    await session.refresh(survey)
    log.info("survey %s created in project %s", survey.id, project_id)
    return survey


@router.get("/projects/{project_id}/surveys", response_model=list[SurveyOut])
async def list_surveys(
    project_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[Survey]:
    await _require_project(session, principal, project_id)
    rows = (
        await session.execute(
            select(Survey)
            .where(Survey.org_id == principal.org_id, Survey.project_id == project_id)
            .order_by(Survey.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/surveys/{survey_id}", response_model=SurveyOut)
async def get_survey(
    survey_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> Survey:
    survey = await _require_survey(session, principal, survey_id)
    await session.refresh(survey, attribute_names=["quotas"])
    return survey


@router.patch("/surveys/{survey_id}", response_model=SurveyOut)
async def patch_survey(
    survey_id: uuid.UUID,
    body: SurveyPatchIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Survey:
    survey = await _require_survey(session, principal, survey_id)
    if survey.status != SurveyStatus.DRAFT:
        raise HTTPException(status_code=409, detail="only draft surveys can be edited")
    if body.title is not None:
        survey.title = body.title
    if body.structure is not None:
        _validate_or_422(body.structure)
        survey.structure = body.structure
    await session.commit()
    await session.refresh(survey, attribute_names=["quotas"])
    return survey


@router.put("/surveys/{survey_id}/quotas", response_model=list[QuotaOut])
async def set_quotas(
    survey_id: uuid.UUID,
    body: list[QuotaIn],
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> list[Quota]:
    survey = await _require_survey(session, principal, survey_id)
    if survey.status != SurveyStatus.DRAFT:
        raise HTTPException(status_code=409, detail="quotas can only be set on a draft survey")
    existing = (
        await session.execute(select(Quota).where(Quota.survey_id == survey.id))
    ).scalars().all()
    for quota in existing:
        await session.delete(quota)
    created = [
        Quota(
            org_id=principal.org_id,
            survey_id=survey.id,
            name=q.name,
            conditions=q.conditions,
            target=q.target,
        )
        for q in body
    ]
    session.add_all(created)
    await session.commit()
    for quota in created:
        await session.refresh(quota)
    return created


# ----------------------------- pre-registration (U6) -----------------------------

@router.put("/surveys/{survey_id}/prereg", response_model=SurveyOut)
async def set_prereg(
    survey_id: uuid.UUID,
    body: PreregIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Survey:
    """Set the hypotheses + planned analyses. Refused once the prereg is frozen (at publish)."""
    survey = await _require_survey(session, principal, survey_id)
    if (survey.prereg or {}).get("frozen_at"):
        raise HTTPException(status_code=409, detail="pre-registration is locked and cannot change")
    survey.prereg = {
        "hypotheses": body.hypotheses,
        "planned_analyses": body.planned_analyses,
        "frozen_at": None,
        "structure_hash": None,
    }
    await session.commit()
    await session.refresh(survey, attribute_names=["quotas"])
    return survey


# ----------------------------- lifecycle -----------------------------

@router.post("/surveys/{survey_id}/publish")
async def publish_survey(
    survey_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, str]:
    survey = await _require_survey(session, principal, survey_id)
    _validate_or_422(survey.structure or {})
    if survey.public_token is None:
        survey.public_token = secrets.token_urlsafe(PUBLIC_TOKEN_BYTES)
    # U6: freeze the pre-registration on first publish (stamp time + a hash of the instrument)
    prereg = dict(survey.prereg or {})
    if not prereg.get("frozen_at"):
        prereg["frozen_at"] = datetime.now(UTC).isoformat()
        prereg["structure_hash"] = _structure_hash(survey.structure or {})
        prereg.setdefault("hypotheses", "")
        prereg.setdefault("planned_analyses", [])
        survey.prereg = prereg
    survey.status = SurveyStatus.LIVE
    await session.commit()
    log.info("survey %s published (token %s…, prereg frozen=%s)",
             survey.id, survey.public_token[:6], bool(prereg.get("frozen_at")))
    return {"token": survey.public_token, "public_url": f"/s/{survey.public_token}"}


async def _set_status(
    session: SessionDep, principal: Principal, survey_id: uuid.UUID, status: SurveyStatus
) -> dict[str, str]:
    survey = await _require_survey(session, principal, survey_id)
    survey.status = status
    await session.commit()
    return {"status": status.value}


@router.post("/surveys/{survey_id}/pause")
async def pause_survey(
    survey_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, str]:
    return await _set_status(session, principal, survey_id, SurveyStatus.PAUSED)


@router.post("/surveys/{survey_id}/close")
async def close_survey(
    survey_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, str]:
    return await _set_status(session, principal, survey_id, SurveyStatus.CLOSED)


# ----------------------------- monitor + responses -----------------------------

async def _responses(session: SessionDep, survey_id: uuid.UUID) -> list[SurveyResponse]:
    return list(
        (
            await session.execute(
                select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
            )
        ).scalars().all()
    )


def _build_monitor(survey: Survey, responses: list[SurveyResponse]) -> dict[str, Any]:
    """Aggregate a live survey snapshot (counts, quota fill, per-question drop-off)."""
    counts = {s.value: 0 for s in ResponseStatus}
    for r in responses:
        counts[r.status.value] += 1

    dropoff = []
    for qid in ordered_qids(survey.structure or {}):
        reached = sum(1 for r in responses if qid in visible_path(survey.structure, r.answers or {}))
        answered = sum(1 for r in responses if (r.answers or {}).get(qid) not in (None, "", []))
        dropoff.append({"qid": qid, "reached": reached, "answered": answered})

    return {
        "completes": counts[ResponseStatus.COMPLETE.value],
        "in_progress": counts[ResponseStatus.IN_PROGRESS.value],
        "screened_out": counts[ResponseStatus.SCREENED_OUT.value],
        "quota_full": counts[ResponseStatus.QUOTA_FULL.value],
        "flagged": counts[ResponseStatus.FLAGGED.value],
        "quotas": [
            {"name": q.name, "target": q.target, "current": q.current} for q in survey.quotas
        ],
        "dropoff": dropoff,
    }


@router.get("/surveys/{survey_id}/monitor")
async def monitor_survey(
    survey_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    survey = await _require_survey(session, principal, survey_id)
    await session.refresh(survey, attribute_names=["quotas"])
    responses = await _responses(session, survey_id)
    return _build_monitor(survey, responses)


@router.get("/surveys/{survey_id}/director")
async def field_director(
    survey_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """Field Director v1 (U2): findings + proposed actions from the live snapshot (HITL)."""
    survey = await _require_survey(session, principal, survey_id)
    await session.refresh(survey, attribute_names=["quotas"])
    responses = await _responses(session, survey_id)
    monitor = _build_monitor(survey, responses)
    return {"findings": analyze_field(monitor)}


@router.post("/surveys/{survey_id}/twin-dry-run")
async def twin_dry_run(
    survey_id: uuid.UUID,
    body: TwinDryRunIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Synthetic Twin Dry-Run (U3): simulate personas taking the survey → design report.

    Synthetic only — informs instrument design (drop-off, confusing items, expected distributions),
    never used as evidence of real results. Persona count is hard-capped in ``build_personas``.
    """
    survey = await _require_survey(session, principal, survey_id)
    _validate_or_422(survey.structure or {})
    personas = build_personas(body.n, body.margins)

    def _run() -> list[dict[str, Any]]:
        return [simulate_persona(survey.structure, p, synth_llm.default_complete) for p in personas]

    with use_llm_context(
        "field", "twin_dry_run", project_id=survey.project_id, org_id=principal.org_id
    ):
        results = await asyncio.to_thread(_run)

    report = aggregate_dry_run(survey.structure, results)
    report["personas_run"] = len(personas)
    log.info("twin dry-run for survey %s: %d personas, completion %.2f",
             survey.id, len(personas), report["completion_rate"])
    return report


class ResponseOut(BaseModel):
    id: uuid.UUID
    status: str
    answers: dict[str, Any]
    flags: list[str]
    duration_seconds: float | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/surveys/{survey_id}/responses", response_model=list[ResponseOut])
async def list_responses(
    survey_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
    status: str | None = None,
) -> list[SurveyResponse]:
    await _require_survey(session, principal, survey_id)
    query = select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
    if status:
        query = query.where(SurveyResponse.status == ResponseStatus(status))
    rows = (await session.execute(query.order_by(SurveyResponse.created_at.desc()))).scalars().all()
    return list(rows)


@router.post("/surveys/{survey_id}/export-dataset")
async def export_dataset(
    survey_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Flatten complete responses (one row each, one column per question) into a versioned Dataset."""
    survey = await _require_survey(session, principal, survey_id)
    responses = [
        r
        for r in await _responses(session, survey_id)
        if r.status in (ResponseStatus.COMPLETE, ResponseStatus.FLAGGED)
    ]
    columns = ordered_qids(survey.structure or {})
    records = []
    for r in responses:
        row = {qid: (r.answers or {}).get(qid) for qid in columns}
        row["_response_id"] = str(r.id)
        row["_flags"] = ",".join(r.flags or [])
        records.append(row)
    df = pd.DataFrame(records, columns=[*columns, "_response_id", "_flags"])

    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    data = buf.getvalue()
    key = f"surveys/{survey.project_id}/{survey.id}/{uuid.uuid4()}.csv"
    get_blob_store().put(key, data)

    dataset = Dataset(
        org_id=principal.org_id,
        project_id=survey.project_id,
        name=f"{survey.title or 'survey'} responses",
        storage_key=key,
        content_hash=dataframe_hash(df) if len(df) else "",
        n_rows=int(len(df)),
        n_cols=int(df.shape[1]),
    )
    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)
    log.info("survey %s exported to dataset %s (%d rows)", survey.id, dataset.id, len(df))
    return {"dataset_id": str(dataset.id), "n_rows": int(len(df)), "n_cols": int(df.shape[1])}
